# -*- coding: utf-8 -*-
from collections import defaultdict

from ..nlg.templates import ETIQUETA_METRICA, NIVEL_EMOJI


# ---------------------------------------------------------------------------
# 7. Párrafos narrativos — celda 12 del notebook
# ---------------------------------------------------------------------------

def parrafo_coloquial_global(tabla_cross, nombre_conjunto: str = ""):
    n = tabla_cross["Sensor"].nunique()
    total_reglas = tabla_cross["Reglas"].sum()
    _fuentes = "fuente de datos" if n == 1 else "fuentes de datos"

    if n == 1:
        sensor = tabla_cross["Sensor"].iloc[0]
        return (
            f"Se ha analizado **1 {_fuentes}** ({sensor}), "
            f"detectando **{total_reglas} patrones** de comportamiento "
            f"estadísticamente significativos."
        )

    sensor_pico  = tabla_cross.loc[tabla_cross["Lift máx"].idxmax(), "Sensor"]
    lift_pico    = tabla_cross["Lift máx"].max()
    sensor_plano = tabla_cross.loc[tabla_cross["Lift medio"].idxmin(), "Sensor"]
    lift_plano   = tabla_cross["Lift medio"].min()

    return (
        f"Se han analizado **{n} {_fuentes}** de {nombre_conjunto}, detectando un total "
        f"de **{total_reglas} patrones** de comportamiento estadísticamente significativos.\n\n"
        f"La fuente con los patrones más marcados es **{sensor_pico}** "
        f"(fuerza de asociación máxima: {lift_pico:.1f}), mientras que **{sensor_plano}** "
        f"presenta el comportamiento más uniforme (fuerza media: {lift_plano:.1f})."
    )


def parrafo_introductorio(tabla_cross, nombre_conjunto: str = ""):
    n_sensores   = tabla_cross["Sensor"].nunique()
    n_reglas     = tabla_cross["Reglas"].sum()
    conf_media_g = tabla_cross["Conf. media (%)"].mean()
    _fuentes     = "fuente de datos" if n_sensores == 1 else "fuentes de datos"

    if n_sensores == 1:
        sensor = tabla_cross["Sensor"].iloc[0]
        return (
            f"El presente informe recoge los resultados del análisis difuso sobre "
            f"**1 {_fuentes}** ({sensor}), con un total de {n_reglas} reglas de asociación "
            f"significativas. La confianza media es del {conf_media_g:.1f} %."
        )

    sensor_max_r = tabla_cross.loc[tabla_cross["Reglas"].idxmax(), "Sensor"]
    sensor_min_r = tabla_cross.loc[tabla_cross["Reglas"].idxmin(), "Sensor"]
    lift_max_g   = tabla_cross["Lift máx"].max()
    sensor_lmax  = tabla_cross.loc[tabla_cross["Lift máx"].idxmax(), "Sensor"]

    return (
        f"El presente informe agrega los resultados del análisis difuso sobre "
        f"{n_sensores} {_fuentes} de {nombre_conjunto}, comprendiendo un total de "
        f"{n_reglas} reglas de asociación significativas. "
        f"La confianza media global es del {conf_media_g:.1f} %. "
        f"La fuente con mayor riqueza de patrones es **{sensor_max_r}** y la de menor, "
        f"**{sensor_min_r}**. "
        f"El patrón más fuerte se observa en **{sensor_lmax}** con lift máximo de {lift_max_g:.1f}."
    )


def parrafo_hallazgos_comunes(comunes, n_sensores_total, nombre_conjunto: str = ""):
    if n_sensores_total == 1:
        return (
            "> El análisis comparativo de patrones compartidos requiere "
            "al menos 2 fuentes de datos."
        )
    if not comunes:
        return (
            "No se han identificado patrones que se repitan en al menos la mitad "
            "de los sensores, lo que sugiere que el comportamiento es "
            "marcadamente local en cada punto de medición."
        )
    top = comunes[:5]
    descripciones = []
    for c in top:
        tokens = c["antecedente"].split(" AND ")
        tok_legibles = []
        for t in tokens:
            if t.startswith("t_H") and len(t) == 5:
                tok_legibles.append(f"las {int(t[3:])}h")
            elif t == "t_Laborable": tok_legibles.append("días laborables")
            elif t == "t_FinSemana": tok_legibles.append("fin de semana")
            elif t == "t_Festivo":   tok_legibles.append("festivos")
            elif t == "t_Madrugada": tok_legibles.append("madrugada")
            elif t == "t_Mañana":    tok_legibles.append("mañana")
            elif t == "t_Tarde":     tok_legibles.append("tarde")
            elif t == "t_Noche":     tok_legibles.append("noche")
            else: tok_legibles.append(t.replace("t_", ""))
        ant_legible  = " + ".join(tok_legibles)
        cons_legible = ETIQUETA_METRICA.get(c["consecuente"], c["consecuente"])
        emoji        = NIVEL_EMOJI.get(c["consecuente"], "")
        descripciones.append(
            f"- {emoji} **{ant_legible}** → {cons_legible} "
            f"({c['n_sensores']}/{n_sensores_total} sensores)"
        )
    bullets = "\n".join(descripciones)
    _ref = f"en {nombre_conjunto}" if nombre_conjunto else "en el conjunto de datos"
    return (
        f"Se identifican patrones recurrentes en al menos la mitad de los sensores, "
        f"lo que sugiere regularidades temporales transversales {_ref}:\n\n"
        f"{bullets}"
    )


def parrafo_atipicos(atipicos, tabla_cross):
    if not atipicos:
        return (
            "Ninguna fuente de datos muestra desviaciones marcadas respecto al "
            "comportamiento medio del grupo en las métricas globales."
        )
    por_sensor = defaultdict(list)
    for a in atipicos:
        por_sensor[a["sensor"]].append(a)

    lineas = []
    for sensor, lista in por_sensor.items():
        partes = []
        for a in lista:
            adj = "elevado" if a["direccion"] == "alto" else "reducido"
            partes.append(
                f"{a['metrica_global']} {adj} "
                f"({a['valor']} vs mediana {a['mediana_grupo']})"
            )
        desc = "; ".join(partes)
        lineas.append(f"- El sensor **{sensor}** presenta {desc}.")

    return "Se detectan comportamientos atípicos:\n\n" + "\n".join(lineas)


def parrafo_outliers(tabla_cross):
    con_alto = tabla_cross[tabla_cross["Outlier alto"] == ""]["Sensor"].tolist()
    con_bajo = tabla_cross[tabla_cross["Outlier bajo"] == ""]["Sensor"].tolist()
    partes = []
    if con_alto:
        partes.append(
            f"🔴 Picos excepcionales detectados en: **{', '.join(con_alto)}**"
        )
    if con_bajo:
        partes.append(
            f"⚪ Caídas excepcionales detectadas en: **{', '.join(con_bajo)}**"
        )
    if not partes:
        return "Ningún sensor presenta reglas asociadas a comportamientos outlier."
    if tabla_cross["Sensor"].nunique() == 1:
        return ""
    return "\n\n".join(partes)
