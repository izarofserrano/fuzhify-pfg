import numpy as np
import pandas as pd

from .metrics import calcular_soporte, calcular_confianza, calcular_lift, evaluar_regla, calcular_aportacion
from .groups import _combinacion_valida


def beam_search_reglas(df, vars_antecedente, consecuente,
                        min_soporte, min_confianza,
                        max_profundidad, k_beam,
                        lift_minimo=1.0,
                        grupos_excluyentes=None):
    """
    Genera reglas difusas SI antecedente -> consecuente mediante beam search.
    Explora combinaciones de variables temporales de profundidad 1 a max_profundidad.
    Acepta una regla solo si su aportación marginal al soporte global supera min_soporte.
    Devuelve DataFrame ordenado por lift DESC.
    """
    if grupos_excluyentes is None:
        grupos_excluyentes = []

    reglas_validas = []
    vistos = set()
    beam_actual = [(v,) for v in vars_antecedente]
    cobertura_acumulada = np.zeros(len(df))

    for profundidad in range(1, max_profundidad + 1):
        puntuaciones = []

        for candidato in beam_actual:
            clave = tuple(sorted(candidato))
            if clave in vistos:
                continue
            vistos.add(clave)

            # Filtro semántico: descartar mes+estación incompatibles
            if not _combinacion_valida(set(clave), grupos_excluyentes):
                continue

            # Filtro de soporte mínimo
            sop = calcular_soporte(df, list(clave))
            if sop < min_soporte:
                continue

            conf = calcular_confianza(df, list(clave), consecuente)
            lift = calcular_lift(df, list(clave), consecuente)

            if conf >= min_confianza and lift >= lift_minimo:
                aportacion = calcular_aportacion(
                    df, list(clave), consecuente, cobertura_acumulada)
                if aportacion >= min_soporte:
                    reglas_validas.append(evaluar_regla(df, list(clave), consecuente))
                    mu_ant = df[list(clave)].min(axis=1).to_numpy()
                    mu_con = df[consecuente].to_numpy()
                    cobertura_acumulada = np.maximum(
                        cobertura_acumulada,
                        np.minimum(mu_ant, mu_con)
                    )

            puntuaciones.append((clave, conf))

        if not puntuaciones or profundidad == max_profundidad:
            break

        top_k = sorted(puntuaciones, key=lambda x: x[1], reverse=True)[:k_beam]

        beam_siguiente = []
        for clave, _ in top_k:
            vars_disponibles = [v for v in vars_antecedente if v not in clave]
            for nueva_var in vars_disponibles:
                nuevo = tuple(sorted(set(clave) | {nueva_var}))
                if nuevo not in vistos:
                    beam_siguiente.append(nuevo)

        beam_actual = list(dict.fromkeys(beam_siguiente))
        if not beam_actual:
            break

    if not reglas_validas:
        return pd.DataFrame(columns=["antecedente","consecuente","n_vars",
                                      "soporte","confianza","lift"])

    return (pd.DataFrame(reglas_validas)
              .drop_duplicates(subset=["antecedente","consecuente"])
              .sort_values("lift", ascending=False)
              .reset_index(drop=True))
