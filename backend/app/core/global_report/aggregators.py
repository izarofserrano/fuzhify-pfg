# -*- coding: utf-8 -*-
import math
import os
import re
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

from ..nlg.templates import (
    ETIQUETA_METRICA,
    NIVEL_EMOJI,
    NIVEL_PESO,
    HORAS_FRANJA_MAP,
    NOMBRE_FRANJA,
)
from .constants import UMBRAL_ATIPICO_MAD, UMBRAL_PATRONES_COMPARTIDOS


# ---------------------------------------------------------------------------
# 3. Carga de CSVs de reglas — celda 4 del notebook
# ---------------------------------------------------------------------------

def cargar_reglas_todos(rutas_reglas: list):
    """
    Devuelve (reglas_por_sensor, faltantes).
    reglas_por_sensor: {(sensor, metrica): df_reglas}
    Infiere sensor y metrica del nombre de fichero: {sensor}_{metrica}_reglas.csv
    Los CSVs ausentes o vacíos se registran en faltantes.
    """
    reglas = {}
    faltantes = []

    for ruta in rutas_reglas:
        if not os.path.exists(ruta):
            faltantes.append(ruta)
            continue
        df = pd.read_csv(ruta)
        if df.empty:
            faltantes.append(f"{ruta} (vacío)")
            continue
        nombre = Path(ruta).stem  # e.g. "3600_intensidad_reglas"
        m = re.match(r'^(.+)_([^_]+)_reglas$', nombre)
        if m:
            sensor, metrica = m.group(1), m.group(2)
        else:
            sensor, metrica = nombre, "desconocida"
        reglas[(sensor, metrica)] = df

    return reglas, faltantes


# ---------------------------------------------------------------------------
# 4. Funciones de agregación — celda 6 del notebook
# ---------------------------------------------------------------------------

def hora_mas_frecuente(df):
    """Hora del día (00–23) con más reglas que la mencionan en el antecedente."""
    cuentas = Counter()
    for ant in df["antecedente"]:
        for token in ant.split(" AND "):
            if token.startswith("t_H") and len(token) == 5:
                try:
                    cuentas[int(token[3:])] += 1
                except ValueError:
                    continue
    if not cuentas:
        return None
    return cuentas.most_common(1)[0][0]


def dia_mas_frecuente(df):
    """Día de la semana con más reglas que lo mencionan."""
    DIAS = {"t_Lun":"Lunes","t_Mar":"Martes","t_Mie":"Miércoles","t_Jue":"Jueves",
            "t_Vie":"Viernes","t_Sab":"Sábado","t_Dom":"Domingo"}
    cuentas = Counter()
    for ant in df["antecedente"]:
        for tok in ant.split(" AND "):
            if tok in DIAS:
                cuentas[DIAS[tok]] += 1
    if not cuentas:
        return None
    return cuentas.most_common(1)[0][0]


def _mapa_horario_sensor(df):
    """
    Para un sensor, construye {hora_int: consecuente_dominante}.
    Hora directa primero, luego herencia de franja si la hora no tiene regla propia.
    """
    mapa = {}
    for h in range(24):
        tok = f"t_H{h:02d}"
        sub = df[df["antecedente"].str.contains(tok, regex=False)]
        if not sub.empty:
            mapa[h] = sub.loc[sub["lift"].idxmax(), "consecuente"]
    for franja_tok, horas in HORAS_FRANJA_MAP.items():
        sub = df[df["antecedente"].str.contains(franja_tok, regex=False)]
        if not sub.empty:
            cons_franja = sub.loc[sub["lift"].idxmax(), "consecuente"]
            for h in horas:
                if h not in mapa:
                    mapa[h] = cons_franja
    return mapa


def _nivel_franja_dominante(df_reglas, horas):
    """
    Nivel más relevante de una franja por votación ponderada (lift × confianza).
    """
    patron = "|".join(f"t_H{h:02d}" for h in horas)
    sub = df_reglas[df_reglas["antecedente"].str.contains(patron, regex=True)]
    if sub.empty:
        return None

    votos: dict = {}
    for _, row in sub.iterrows():
        n = row["consecuente"]
        votos[n] = votos.get(n, 0.0) + row["lift"] * row["confianza"]

    return max(votos, key=votos.get)


def _perfil_dia_sensor(df):
    """
    Genera una cadena compacta del perfil diario de un sensor.
    Ejemplo: "Madrugada | Mañana  | Tarde  | Noche "
    """
    partes = []
    for franja_tok, horas in HORAS_FRANJA_MAP.items():
        nombre_corto = NOMBRE_FRANJA[franja_tok].split(" (")[0]
        nivel = _nivel_franja_dominante(df, horas)
        if nivel is None:
            partes.append(f"{nombre_corto} —")
        else:
            emoji = NIVEL_EMOJI.get(nivel, "")
            partes.append(f"{nombre_corto} {emoji}")
    return " | ".join(partes)


def construir_tabla_cross_sensor(reglas_por_sensor, bloques):
    """
    Construye la tabla comparativa cross-sensor/dataset.
    bloques: dict con HAY_HORAS, HAY_FRANJAS, HAY_DIAS, etc.
    """
    HAY_HORAS   = bloques.get("HAY_HORAS", False)
    HAY_FRANJAS = bloques.get("HAY_FRANJAS", False)

    filas = []
    for (sensor, metrica), df in reglas_por_sensor.items():

        consec_dom = (df["consecuente"].value_counts().idxmax()
                      if not df["consecuente"].mode().empty else "—")
        emoji_dom = NIVEL_EMOJI.get(consec_dom, "")
        etiq_dom  = ETIQUETA_METRICA.get(consec_dom, consec_dom)

        fila = {
            "Sensor":          sensor,
            "Métrica":         metrica,
            "Reglas":          len(df),
            "Conf. media (%)": round(df["confianza"].mean() * 100, 1),
            "Lift medio":      round(df["lift"].mean(), 2),
            "Lift máx":        round(df["lift"].max(), 2),
            "Lift mín":        round(df["lift"].min(), 2),
            "Soporte medio":   round(df["soporte"].mean(), 4),
            "Nivel dominante": f"{emoji_dom} {etiq_dom}",
            "Outlier alto":    "✅" if "v_OutlierAlto" in df["consecuente"].values else "—",
            "Outlier bajo":    "✅" if "v_OutlierBajo" in df["consecuente"].values else "—",
        }

        if HAY_HORAS or HAY_FRANJAS:
            fila["Perfil del día"]               = _perfil_dia_sensor(df)
            fila["Hora más mencionada en reglas"] = hora_mas_frecuente(df)
        else:
            _tokens_cal = [
                t for ant in df["antecedente"]
                for t in ant.split(" AND ")
                if t.startswith("t_") and not re.match(r'^t_H\d{2}$', t)
            ]
            _mas_frecuente = (Counter(_tokens_cal).most_common(1)[0][0]
                              .replace("t_", "")
                              if _tokens_cal else "—")
            fila["Patrón calendario dominante"] = _mas_frecuente

        _dia = dia_mas_frecuente(df)
        if _dia:
            fila["Día más mencionado"] = _dia

        filas.append(fila)

    return pd.DataFrame(filas)


# ---------------------------------------------------------------------------
# 5. Patrones compartidos — celda 8 del notebook
# ---------------------------------------------------------------------------

def patrones_compartidos(reglas_por_sensor, umbral=UMBRAL_PATRONES_COMPARTIDOS):
    """
    Devuelve lista de patrones (antecedente, consecuente) que aparecen
    en al menos `umbral` proporción de los sensores.
    """
    apariciones = defaultdict(set)

    for (sensor, _metrica), df in reglas_por_sensor.items():
        for _, row in df.iterrows():
            clave = (row["antecedente"], row["consecuente"])
            apariciones[clave].add(sensor)

    n_sensores = len(set(s for s, _ in reglas_por_sensor.keys()))
    umbral_n = max(2, math.ceil(n_sensores * umbral))

    comunes = [
        {"antecedente": ant, "consecuente": cons,
         "n_sensores": len(sens), "sensores": sorted(sens)}
        for (ant, cons), sens in apariciones.items()
        if len(sens) >= umbral_n
    ]
    comunes.sort(key=lambda x: -x["n_sensores"])
    return comunes


# ---------------------------------------------------------------------------
# 6. Detección de atípicos — celda 10 del notebook
# ---------------------------------------------------------------------------

def detectar_atipicos(tabla_cross):
    """
    Marca como atípico un sensor que esté a más de UMBRAL_ATIPICO_MAD·MAD
    de la mediana del grupo en cualquier métrica numérica clave.
    """
    metricas_num = ["Reglas", "Conf. media (%)", "Lift medio", "Lift máx"]
    atipicos = []

    for met in metricas_num:
        if met not in tabla_cross.columns:
            continue
        valores = tabla_cross[met].astype(float)
        mediana = valores.median()
        mad = (valores - mediana).abs().median()
        if mad == 0:
            continue
        for _, row in tabla_cross.iterrows():
            v = float(row[met])
            desviacion = (v - mediana) / mad
            if abs(desviacion) >= UMBRAL_ATIPICO_MAD:
                atipicos.append({
                    "sensor":         row["Sensor"],
                    "metrica_global": met,
                    "valor":          v,
                    "mediana_grupo":  round(mediana, 2),
                    "direccion":      "alto" if desviacion > 0 else "bajo",
                    "desviacion_mad": round(abs(desviacion), 1),
                })
    return atipicos


def comparar_perfiles_dia(tabla_cross):
    """
    Compara perfiles temporales entre sensores.
    Usa 'Perfil del día' si hay horas/franjas,
    o 'Patrón calendario dominante' si el dataset es diario.
    """
    if "Perfil del día" in tabla_cross.columns:
        col_perfil  = "Perfil del día"
        etiq_perfil = "perfil diario"
    elif "Patrón calendario dominante" in tabla_cross.columns:
        col_perfil  = "Patrón calendario dominante"
        etiq_perfil = "patrón calendario dominante"
    else:
        return ["No hay información de perfil temporal disponible."]

    perfiles = dict(zip(tabla_cross["Sensor"], tabla_cross[col_perfil]))
    if len(perfiles) == 1:
        return []
    grupos = defaultdict(list)
    for sensor, perfil in perfiles.items():
        grupos[perfil].append(sensor)

    frases = []
    for perfil, sensores in sorted(grupos.items(), key=lambda x: -len(x[1])):
        if len(sensores) > 1:
            frases.append(
                f"Las fuentes **{', '.join(sensores)}** comparten el mismo "
                f"{etiq_perfil}: *{perfil}*."
            )
        else:
            frases.append(
                f"La fuente **{sensores[0]}** tiene {etiq_perfil} propio: *{perfil}*."
            )
    return frases
