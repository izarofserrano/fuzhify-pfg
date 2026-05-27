from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Paso 1 — Subir CSV y detectar métricas candidatas
# ---------------------------------------------------------------------------

class MetricaCandidata(BaseModel):
    nombre: str
    sugerida: bool
    razon: str


class DetectMetricResponse(BaseModel):
    job_id: UUID
    nombre_dataset: str
    var_tiempo: str
    granularidad_s: int
    candidatas: list[MetricaCandidata]


# ---------------------------------------------------------------------------
# Paso 2 — Confirmar métrica y lanzar pipeline
# ---------------------------------------------------------------------------

class ParametrosPipeline(BaseModel):
    min_soporte: float = 0.005
    min_confianza: float = 0.50
    lift_minimo: Literal[1.0, 1.5, 2.0, 3.0] = 1.5   # solo 4 valores válidos
    max_prof: int = 3
    k_beam: int = 10
    top_por_consecuente: int = 10
    pais: str = "ES"
    subdiv: str | None = None
    min_reglas_grupo: int = 2
    usar_llm_sintesis: bool = False


class RunJobRequest(BaseModel):
    metrica_seleccionada: str
    parametros: ParametrosPipeline


# ---------------------------------------------------------------------------
# Paso 3 — Polling de estado
# ---------------------------------------------------------------------------

class JobStatus(BaseModel):
    id: UUID
    estado: str
    fase_actual: str | None
    metrica_seleccionada: str | None
    error_mensaje: str | None
    creado_en: datetime
    actualizado_en: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Paso 4 — Resultados: reglas y descarga del informe
# ---------------------------------------------------------------------------

class ReglaItem(BaseModel):
    antecedente: str
    consecuente: str
    soporte: float
    confianza: float
    lift: float
    n_vars: int


class ReglasResponse(BaseModel):
    total: int
    items: list[ReglaItem]
