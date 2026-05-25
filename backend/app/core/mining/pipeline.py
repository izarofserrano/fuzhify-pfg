from dataclasses import dataclass, field

import pandas as pd

from .constants import MIN_SOPORTE, MIN_CONFIANZA, MAX_PROF, K_BEAM, TOP_POR_CONSECUENTE
from .beam import beam_search_reglas
from .filters import filtrar_redundantes, filtrar_por_jerarquia, filtrar_top_por_consecuente
from .groups import _construir_grupos, construir_jerarquia


@dataclass
class MinerConfig:
    min_soporte: float         = MIN_SOPORTE
    min_confianza: float       = MIN_CONFIANZA
    lift_minimo: float         = 2.0          # "Sorprendentes" — default del notebook
    max_prof: int              = MAX_PROF
    k_beam: int                = K_BEAM
    top_por_consecuente: int   = TOP_POR_CONSECUENTE


def minar_reglas(df_fuzzy: pd.DataFrame, config: MinerConfig = None) -> pd.DataFrame:
    """
    Pipeline completo de minería de reglas de asociación difusas.

    Entrada:  df_fuzzy — CSV fuzzificado (salida de src01).
    Salida:   DataFrame con columnas [antecedente, consecuente, soporte,
              confianza, lift, n_vars], ordenado por lift DESC.
    """
    if config is None:
        config = MinerConfig()

    vars_t = [c for c in df_fuzzy.columns if c.startswith("t_")]
    vars_v = [c for c in df_fuzzy.columns
              if c.startswith("v_")
              and not c.startswith("v_abs_")
              and c != "v_Mediana"]

    grupos_excluyentes = _construir_grupos(df_fuzzy.columns)
    jerarquia = construir_jerarquia(df_fuzzy.columns)

    todos = []
    for consecuente in vars_v:
        df_r = beam_search_reglas(
            df_fuzzy,
            vars_antecedente   = vars_t,
            consecuente        = consecuente,
            min_soporte        = config.min_soporte,
            min_confianza      = config.min_confianza,
            max_profundidad    = config.max_prof,
            k_beam             = config.k_beam,
            lift_minimo        = config.lift_minimo,
            grupos_excluyentes = grupos_excluyentes,
        )
        if not df_r.empty:
            todos.append(df_r)

    if todos:
        df_reglas = (pd.concat(todos, ignore_index=True)
                       .sort_values("lift", ascending=False)
                       .reset_index(drop=True))
    else:
        df_reglas = pd.DataFrame(columns=["antecedente", "consecuente", "n_vars",
                                           "soporte", "confianza", "lift"])

    if not df_reglas.empty:
        df_reglas = filtrar_redundantes(df_reglas, min_confianza=config.min_confianza)
        df_reglas = filtrar_por_jerarquia(df_reglas, jerarquia, min_confianza=config.min_confianza)
        df_reglas = filtrar_top_por_consecuente(df_reglas, config.top_por_consecuente)

    return df_reglas
