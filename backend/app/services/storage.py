"""
Helpers de almacenamiento local para archivos de jobs.

Estructura en disco:
    <data_dir>/<job_id>/
        entrada.csv   ← CSV original subido por el usuario
        fuzzy.csv     ← salida de src01 (fuzzificación)
        reglas.csv    ← salida de src02 (beam search)
        informe.md    ← salida de src03 (NLG)
"""
from pathlib import Path
from uuid import UUID

from app.config import settings

_BASE = Path(settings.data_dir)


def job_dir(job_id: UUID | str) -> Path:
    """Devuelve la ruta del directorio del job (sin crearlo)."""
    return _BASE / str(job_id)


def crear_dir_job(job_id: UUID | str) -> Path:
    """Crea el directorio del job si no existe y devuelve su ruta."""
    d = job_dir(job_id)
    d.mkdir(parents=True, exist_ok=True)
    return d


def ruta_entrada(job_id: UUID | str) -> Path:
    return job_dir(job_id) / "entrada.csv"


def ruta_fuzzy(job_id: UUID | str) -> Path:
    return job_dir(job_id) / "fuzzy.csv"


def ruta_reglas(job_id: UUID | str) -> Path:
    return job_dir(job_id) / "reglas.csv"


def ruta_informe(job_id: UUID | str) -> Path:
    return job_dir(job_id) / "informe.md"


def guardar_entrada(job_id: UUID | str, contenido: bytes) -> Path:
    """Guarda el CSV original subido por el usuario. Crea el dir si hace falta."""
    crear_dir_job(job_id)
    ruta = ruta_entrada(job_id)
    ruta.write_bytes(contenido)
    return ruta
