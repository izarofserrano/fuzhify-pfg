import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func

from app.db import Base

# Estados válidos del job (ver CONTEXTO.md — src04 endpoint)
# "esperando_metrica" → backend detectó candidatas, espera al usuario
# "pendiente"         → métrica confirmada, en cola
# "ejecutando"        → BackgroundTask corriendo
# "completado"
# "error"


class Job(Base):
    __tablename__ = "jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    estado = Column(String, nullable=False)
    fase_actual = Column(String, nullable=True)           # "fuzzy"|"mining"|"nlg"|None

    nombre_dataset = Column(Text, nullable=False)
    var_tiempo = Column(String, nullable=True)            # detectada en /detect-metric
    metricas_candidatas = Column(JSONB, nullable=True)    # [{"nombre","sugerida","razon"},...]
    metrica_seleccionada = Column(String, nullable=True)  # elegida por el usuario
    granularidad_s = Column(Integer, nullable=True)

    parametros = Column(JSONB, nullable=False)            # MIN_SOPORTE, MIN_CONFIANZA, etc.

    ruta_csv_entrada = Column(Text, nullable=False)
    ruta_csv_fuzzy = Column(Text, nullable=True)
    ruta_csv_reglas = Column(Text, nullable=True)
    ruta_informe_md = Column(Text, nullable=True)

    error_mensaje = Column(Text, nullable=True)

    creado_en = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    actualizado_en = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
