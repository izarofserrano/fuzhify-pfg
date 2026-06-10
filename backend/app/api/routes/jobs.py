"""
Endpoints del pipeline de análisis difuso.
Flujo de 2 pasos: detect-metric → run → polling + descarga.
"""
import asyncio
import io
import uuid as uuid_module
from pathlib import Path
from typing import Literal
from uuid import UUID

import pandas as pd
from fastapi import (
    APIRouter, BackgroundTasks, Depends, File, Form,
    HTTPException, Query, Response, UploadFile,
)
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.fuzzy import FuzzyConfig, detectar_metricas_candidatas, _leer_csv
from app.core.global_report import construir_informe_global
from app.core.pdf_export import generar_pdf_informe
from app.db import AsyncSessionLocal, get_db
from app.models.job import Job
from app.schemas.job import (
    DetectMetricResponse,
    JobStatus,
    MetricaCandidata,
    ParametrosPipeline,
    ReglasResponse,
    ReglaItem,
    RunJobRequest,
)
from app.services.pipeline_service import ejecutar_pipeline
from app.services.storage import guardar_entrada

router = APIRouter()


class InformeGlobalRequest(BaseModel):
    job_ids: list[UUID]


# ── Auxiliares ───────────────────────────────────────────────────────────────

def _job_to_dict(job) -> dict:
    """Convierte objeto Job a dict dentro de la sesión async."""
    return {
        "id": job.id,
        "estado": job.estado,
        "fase_actual": job.fase_actual,
        "nombre_dataset": job.nombre_dataset,
        "metrica_seleccionada": job.metrica_seleccionada,
        "error_mensaje": job.error_mensaje,
        "creado_en": job.creado_en,
        "actualizado_en": job.actualizado_en,
    }


async def _get_job_or_404(session: AsyncSession, job_id: UUID) -> Job:
    resultado = await session.execute(select(Job).where(Job.id == job_id))
    job = resultado.scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=404, detail="Job no encontrado")
    return job


# 1. Detectar métricas candidatas

@router.post("/detect-metric", response_model=DetectMetricResponse, status_code=201)
async def detect_metric(
    csv: UploadFile = File(..., description="CSV con la serie temporal"),
    parametros: str = Form("{}", description="JSON con ParametrosPipeline"),
    session: AsyncSession = Depends(get_db),
):
    """
    Paso 1: sube el CSV y detecta métricas candidatas.
    Crea un job en estado 'esperando_metrica'.
    """
    # Validar tamaño del archivo
    contenido = await csv.read()
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if len(contenido) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"El CSV supera el límite de {settings.max_upload_mb} MB",
        )

    # Parsear parámetros del formulario
    try:
        params = ParametrosPipeline.model_validate_json(parametros)
    except Exception:
        raise HTTPException(status_code=422, detail="'parametros' no es un JSON válido")

    nombre_dataset = csv.filename or "dataset"
    new_id = uuid_module.uuid4()

    # Guardar CSV en disco (crea el directorio del job)
    ruta_csv = guardar_entrada(new_id, contenido)

    # Leer CSV para detectar métricas
    try:
        df = _leer_csv(io.BytesIO(contenido))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    fuzzy_config = FuzzyConfig(
        pais_festivos=params.pais,
        subdiv_festivos=params.subdiv,
    )
    resultado = detectar_metricas_candidatas(df, fuzzy_config)

    # Crear job en BD
    job = Job(
        id=new_id,
        estado="esperando_metrica",
        nombre_dataset=nombre_dataset,
        parametros=params.model_dump(),
        ruta_csv_entrada=str(ruta_csv),
        var_tiempo=resultado.get("var_tiempo"),
        metricas_candidatas=resultado.get("candidatas", []),
        granularidad_s=(
            int(resultado["granularidad_s"])
            if resultado.get("granularidad_s") is not None
            else None
        ),
    )
    session.add(job)
    await session.commit()

    return DetectMetricResponse(
        job_id=job.id,
        nombre_dataset=nombre_dataset,
        var_tiempo=resultado.get("var_tiempo") or "",
        candidatas=[MetricaCandidata(**c) for c in resultado.get("candidatas", [])],
        granularidad_s=job.granularidad_s or 0,
    )


# 2. Confirmar métrica y lanzar pipeline

@router.post("/jobs/{job_id}/run", response_model=JobStatus, status_code=202)
async def run_job(
    job_id: UUID,
    body: RunJobRequest,
    background_tasks: BackgroundTasks,
):
    """Paso 2: confirma métrica y lanza pipeline."""
    async with AsyncSessionLocal() as session:
        job = await session.get(Job, job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Job no encontrado")

        if job.estado != "esperando_metrica":
            raise HTTPException(
                status_code=409,
                detail=f"Estado inválido para lanzar: {job.estado!r}",
            )

        candidatas = job.metricas_candidatas or []
        nombres_candidatas = [c["nombre"] for c in candidatas]
        if body.metrica_seleccionada not in nombres_candidatas:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Métrica {body.metrica_seleccionada!r} no válida. "
                    f"Candidatas: {nombres_candidatas}"
                ),
            )

        job.metrica_seleccionada = body.metrica_seleccionada
        job.parametros = body.parametros.model_dump()
        job.estado = "pendiente"
        await session.commit()
        await session.refresh(job)   # evita MissingGreenlet al acceder atributos post-commit
        job_dict = _job_to_dict(job)

    background_tasks.add_task(asyncio.run, ejecutar_pipeline(job_id))
    return JobStatus.model_validate(job_dict)


# 3. Consultar estado del job

@router.get("/jobs/{job_id}", response_model=JobStatus)
async def get_job(
    job_id: UUID,
    session: AsyncSession = Depends(get_db),
):
    """Devuelve el estado actual del job."""
    job = await _get_job_or_404(session, job_id)
    return JobStatus.model_validate(_job_to_dict(job))


# 4. Listar reglas del job 

@router.get("/jobs/{job_id}/reglas", response_model=ReglasResponse)
async def get_reglas(
    job_id: UUID,
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    consecuente: str | None = Query(None, description="Filtrar por consecuente"),
    session: AsyncSession = Depends(get_db),
):
    """Devuelve las reglas paginadas del job (solo si está completado)."""
    job = await _get_job_or_404(session, job_id)

    if job.estado != "completado":
        raise HTTPException(status_code=409, detail="El job no está completado")

    df = pd.read_csv(job.ruta_csv_reglas)

    if consecuente is not None:
        df = df[df["consecuente"] == consecuente]

    total = len(df)
    df_page = df.iloc[offset: offset + limit].copy()
    df_page["n_vars"] = df_page["n_vars"].fillna(0).astype(int)

    items = [ReglaItem(**row) for row in df_page.to_dict(orient="records")]
    return ReglasResponse(total=total, items=items)


# 5. Informe en markdown 

@router.get("/jobs/{job_id}/informe")
async def get_informe(
    job_id: UUID,
    session: AsyncSession = Depends(get_db),
):
    """Devuelve el informe .md como text/markdown (solo si está completado)."""
    job = await _get_job_or_404(session, job_id)

    if job.estado != "completado":
        raise HTTPException(status_code=409, detail="El job no está completado")

    contenido = Path(job.ruta_informe_md).read_text(encoding="utf-8")
    return Response(content=contenido, media_type="text/markdown")


# 6. Descargar archivos del job 

_ATRIBUTO_ARCHIVO: dict[str, str] = {
    "entrada": "ruta_csv_entrada",
    "fuzzy":   "ruta_csv_fuzzy",
    "reglas":  "ruta_csv_reglas",
    "informe": "ruta_informe_md",
}


@router.get("/jobs/{job_id}/descargar/{tipo}")
async def descargar_archivo(
    job_id: UUID,
    tipo: Literal["entrada", "fuzzy", "reglas", "informe"],
    session: AsyncSession = Depends(get_db),
):
    """Descarga uno de los archivos generados por el job (Content-Disposition: attachment)."""
    job = await _get_job_or_404(session, job_id)

    attr = _ATRIBUTO_ARCHIVO[tipo]
    ruta = getattr(job, attr)

    if not ruta or not Path(ruta).exists():
        raise HTTPException(
            status_code=404,
            detail=f"Archivo '{tipo}' no disponible para este job",
        )

    return FileResponse(
        path=ruta,
        filename=Path(ruta).name,
    )

# 7. Listar jobs (antes de las rutas con {job_id} para evitar ambigüedad) 

@router.get("/jobs", response_model=list[JobStatus])
async def list_jobs(
    estado: str | None = Query(None, description="Filtrar por estado"),
    limit: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
):
    """Lista los jobs más recientes, con filtro opcional por estado."""
    query = select(Job)
    if estado is not None:
        query = query.where(Job.estado == estado)
    query = query.order_by(Job.creado_en.desc()).limit(limit)

    resultado = await session.execute(query)
    jobs = resultado.scalars().all()
    return [JobStatus.model_validate(_job_to_dict(j)) for j in jobs]


# 8. Informe en PDF 

@router.get("/jobs/{job_id}/informe.pdf")
async def descargar_informe_pdf(
    job_id: UUID,
    session: AsyncSession = Depends(get_db),
):
    """Genera y descarga el informe en PDF (solo si el job está completado)."""
    job = await _get_job_or_404(session, job_id)

    if job.estado != "completado":
        raise HTTPException(status_code=409, detail="El job no está completado")

    # Acceder a todos los atributos necesarios dentro de la sesión (evita lazy-load en el thread)
    ruta_reglas = job.ruta_csv_reglas
    ruta_fuzzy  = job.ruta_csv_fuzzy
    ruta_md     = job.ruta_informe_md

    if not ruta_reglas or not ruta_fuzzy or not ruta_md:
        raise HTTPException(status_code=409, detail="Faltan archivos del job para generar el PDF")

    try:
        pdf_bytes = await asyncio.to_thread(generar_pdf_informe, job)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error al generar el PDF: {exc}")

    nombre_base = f"{job.nombre_dataset}_{job.metrica_seleccionada}_informe.pdf"
    nombre_archivo = nombre_base.replace(" ", "_").replace("/", "_")

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{nombre_archivo}"',
        },
    )


# 9. Informe global comparativo

@router.post("/informe-global")
async def informe_global(
    body: InformeGlobalRequest,
    session: AsyncSession = Depends(get_db),
):
    """Genera un informe global comparativo a partir de varios jobs completados."""
    rutas_reglas: list[str] = []
    for jid in body.job_ids:
        job = await _get_job_or_404(session, jid)
        if job.estado != "completado":
            raise HTTPException(
                status_code=409,
                detail=f"Job {jid} no está completado (estado: {job.estado!r})",
            )
        if not job.ruta_csv_reglas:
            raise HTTPException(
                status_code=409,
                detail=f"Job {jid} no tiene archivo de reglas",
            )
        rutas_reglas.append(job.ruta_csv_reglas)

    try:
        informe_md = construir_informe_global(rutas_reglas)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return Response(content=informe_md, media_type="text/markdown")
