"""
Pipeline de análisis difuso lanzado con asyncio.create_task().
Fases: fuzzificación → minería de reglas → NLG.

Cada actualización de estado de BD abre y cierra su propia sesión
para evitar MissingGreenlet al cruzar contextos con asyncio.to_thread().
"""
import asyncio
import logging
from datetime import datetime, timezone
from uuid import UUID

import pandas as pd

from app.config import settings
from app.core.fuzzy import FuzzyConfig, fuzzificar, _leer_csv
from app.core.mining import MinerConfig, minar_reglas
from app.core.nlg import NLGConfig, generar_informe
from app.db import AsyncSessionLocal
from app.models.job import Job
from app.services.storage import ruta_fuzzy, ruta_informe, ruta_reglas

logger = logging.getLogger(__name__)


async def _actualizar_job(job_id: UUID, **campos) -> None:
    """Abre sesión, actualiza campos del job, cierra. Autocontenida."""
    async with AsyncSessionLocal() as session:
        job = await session.get(Job, job_id)
        if job is None:
            logger.error("_actualizar_job: Job %s no encontrado", job_id)
            return
        for k, v in campos.items():
            setattr(job, k, v)
        job.actualizado_en = datetime.now(tz=timezone.utc)
        await session.commit()


async def _leer_datos_job(job_id: UUID) -> dict | None:
    """Lee los datos de trabajo del job en una sesión autocontenida."""
    async with AsyncSessionLocal() as session:
        job = await session.get(Job, job_id)
        if job is None:
            return None
        return {
            "estado":              job.estado,
            "ruta_csv_entrada":    job.ruta_csv_entrada,
            "metrica_seleccionada": job.metrica_seleccionada,
            "nombre_dataset":      job.nombre_dataset,
            "parametros":          dict(job.parametros or {}),
        }


async def ejecutar_pipeline(job_id: UUID) -> None:
    """
    Pipeline completo: fuzzificación → minería → NLG.
    Lanzado con asyncio.create_task() tras confirmar la métrica.
    """
    datos = await _leer_datos_job(job_id)
    if datos is None:
        logger.error("Job %s no encontrado en BD", job_id)
        return
    if datos["estado"] != "pendiente":
        logger.error("Job %s en estado inesperado: %s", job_id, datos["estado"])
        return

    ruta_entrada = datos["ruta_csv_entrada"]
    metrica      = datos["metrica_seleccionada"]
    nombre_dataset = datos["nombre_dataset"]
    parametros   = datos["parametros"]

    try:
        await _actualizar_job(job_id, estado="ejecutando", fase_actual="fuzzy")

        # ── Fase 1: Fuzzificación (CPU-bound, sin contacto con BD) ───────────
        def _fuzzificar():
            df = _leer_csv(ruta_entrada)
            cfg = FuzzyConfig(
                var_metrica_override=metrica,
                pais_festivos=parametros.get("pais", "ES"),
                subdiv_festivos=parametros.get("subdiv"),
            )
            return fuzzificar(df, cfg)

        df_fuzzy = await asyncio.to_thread(_fuzzificar)

        ruta_f = ruta_fuzzy(job_id)
        await asyncio.to_thread(df_fuzzy.to_csv, str(ruta_f), index=False)
        await _actualizar_job(job_id, fase_actual="mining", ruta_csv_fuzzy=str(ruta_f))

        # ── Fase 2: Minería de reglas (CPU-bound, sin contacto con BD) ────────
        def _minar(_df=df_fuzzy):
            cfg = MinerConfig(
                min_soporte=float(parametros.get("min_soporte", 0.005)),
                min_confianza=float(parametros.get("min_confianza", 0.50)),
                lift_minimo=float(parametros.get("lift_minimo", 1.5)),
                max_prof=int(parametros.get("max_prof", 3)),
                k_beam=int(parametros.get("k_beam", 10)),
                top_por_consecuente=int(parametros.get("top_por_consecuente", 10)),
            )
            return minar_reglas(_df, cfg)

        df_reglas = await asyncio.to_thread(_minar)

        ruta_r = ruta_reglas(job_id)
        await asyncio.to_thread(df_reglas.to_csv, str(ruta_r), index=False)
        await _actualizar_job(job_id, fase_actual="nlg", ruta_csv_reglas=str(ruta_r))

        # ── Fase 3: NLG (CPU-bound, sin contacto con BD) ─────────────────────
        def _generar(_dr=df_reglas, _df=df_fuzzy):
            cfg = NLGConfig(
                nombre_dataset=nombre_dataset,
                metrica=metrica or "",
                min_reglas_grupo=int(parametros.get("min_reglas_grupo", 2)),
                usar_llm_sintesis=bool(parametros.get("usar_llm_sintesis", False)),
                proveedor_llm=parametros.get("proveedor_llm", "gemini"),
                llm_api_key=settings.gemini_api_key or None,
            )
            return generar_informe(_dr, _df, cfg)

        informe_md = await asyncio.to_thread(_generar)

        ruta_inf = ruta_informe(job_id)
        await asyncio.to_thread(ruta_inf.write_text, informe_md, encoding="utf-8")
        await _actualizar_job(
            job_id,
            estado="completado",
            fase_actual=None,
            ruta_informe_md=str(ruta_inf),
        )

    except Exception as exc:
        logger.exception("Error en pipeline del job %s: %s", job_id, exc)
        await _actualizar_job(
            job_id,
            estado="error",
            error_mensaje=str(exc),
            fase_actual=None,
        )
