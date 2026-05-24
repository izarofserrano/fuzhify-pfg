"""Función trapecio y helpers de rampa difusa."""

import numpy as np

from .constants import TOLERANCIA, N_MUESTRAS_RAMPA


def tol(especifica):
    """Devuelve la tolerancia específica si está definida; si no, la por defecto."""
    return especifica if especifica is not None else TOLERANCIA


def rampa_s(tolerancia_prop, duracion_bloque, granularidad_s, n_muestras_rampa=N_MUESTRAS_RAMPA):
    """
    Calcula la rampa en SEGUNDOS para un bloque temporal.

    Toma el máximo entre:
      1) la rampa proporcional (tolerancia * duración del bloque), y
      2) un suelo mínimo de N_MUESTRAS_RAMPA * GRANULARIDAD_S.

    Así se garantiza que siempre haya muestras dentro de la rampa,
    independientemente de la relación entre granularidad y duración del bloque.
    """
    rampa_proporcional = tolerancia_prop * duracion_bloque
    rampa_minima       = n_muestras_rampa * granularidad_s
    return max(rampa_proporcional, rampa_minima)


def trapecio(x, a, b, c, d):
    x = np.asarray(x, dtype=float)
    y = np.zeros_like(x)

    m1 = (x >= a) & (x < b)
    y[m1] = (x[m1] - a) / (b - a) if b != a else 1.0

    m2 = (x >= b) & (x <= c)
    y[m2] = 1.0

    m3 = (x > c) & (x <= d)
    y[m3] = (d - x[m3]) / (d - c) if d != c else 1.0

    return np.clip(y, 0, 1).round(4)
