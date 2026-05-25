import numpy as np
import pandas as pd


def calcular_soporte(df, columnas):
    """
    Soporte difuso = suma(min(mu1, mu2, ...)) / N
    Acepta str (1 columna) o lista (intersección AND difusa).
    """
    if isinstance(columnas, str):
        mu = df[columnas]
    else:
        mu = df[list(columnas)].min(axis=1)
    return float(mu.sum() / len(df))


def calcular_confianza(df, antecedente, consecuente):

    ant = [antecedente] if isinstance(antecedente, str) else list(antecedente)
    sop_a = calcular_soporte(df, ant)
    if sop_a == 0:
        return 0.0
    # Soporte conjunto: min de mu_antecedente y mu_consecuente
    mu_ant = df[ant].min(axis=1)          # t-norma del antecedente
    mu_con = df[consecuente]              # pertenencia del consecuente
    sop_ac = float(np.minimum(mu_ant, mu_con).sum() / len(df))
    return float(sop_ac / sop_a)


def calcular_lift(df, antecedente, consecuente):
    """
    Lift = Confianza(A->C) / Soporte(C)
    Lift > 1  -> A y C aparecen juntos más de lo esperado por azar.
    Lift = 1  -> independientes (regla trivial).
    Lift < 1  -> A inhibe C.
    """
    sop_c = calcular_soporte(df, consecuente)
    if sop_c == 0:
        return 0.0
    return float(calcular_confianza(df, antecedente, consecuente) / sop_c)


def evaluar_regla(df, antecedente, consecuente):
    """Devuelve un dict con todas las métricas de una regla."""
    ant = [antecedente] if isinstance(antecedente, str) else list(antecedente)
    return {
        "antecedente": " AND ".join(ant),
        "consecuente": consecuente,
        "n_vars":      len(ant),
        "soporte":     round(calcular_soporte(df, ant),                4),
        "confianza":   round(calcular_confianza(df, ant, consecuente),  4),
        "lift":        round(calcular_lift(df, ant, consecuente),       4),
    }


def calcular_aportacion(df, columnas_antecedente, consecuente, cobertura_acumulada):
    """
    Mide cuánto soporte NUEVO aporta una regla sobre lo ya cubierto.
    cobertura_acumulada es un array con el máximo grado de pertenencia
    ya acumulado por las reglas aceptadas anteriormente.
    """
    mu_ant = df[list(columnas_antecedente)].min(axis=1).to_numpy()
    mu_con = df[consecuente].to_numpy()
    mu_regla = np.minimum(mu_ant, mu_con)
    aportacion = np.maximum(0, mu_regla - cobertura_acumulada)
    return float(aportacion.sum() / len(df))
