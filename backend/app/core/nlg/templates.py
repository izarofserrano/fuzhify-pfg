# ---------------------------------------------------------------------------
# 3. Diccionarios de traducción y jerarquía temporal
# ---------------------------------------------------------------------------

# ── 3a. Etiquetas legibles para cada token temporal ────────────────────────
ETIQUETA_TEMPORAL = {
    # Años: rango 2000-2050 para cubrir cualquier dataset
    **{f"t_{y}": f"el año {y}" for y in range(2000, 2051)},
    # Meses
    "t_Ene": "enero",    "t_Feb": "febrero",  "t_Marz": "marzo",
    "t_Abr": "abril",    "t_May": "mayo",     "t_Jun": "junio",
    "t_Jul": "julio",    "t_Ago": "agosto",   "t_Sep": "septiembre",
    "t_Oct": "octubre",  "t_Nov": "noviembre", "t_Dic": "diciembre",
    # Días de la semana
    "t_Lun": "los lunes",  "t_Mar": "los martes",  "t_Mie": "los miércoles",
    "t_Jue": "los jueves", "t_Vie": "los viernes",  "t_Sab": "los sábados",
    "t_Dom": "los domingos",
    # Horas (H00–H23)
    **{f"t_H{h:02d}": f"las {h}h" for h in range(24)},
    # Franjas horarias
    "t_Madrugada": "la madrugada (0–6 h)",
    "t_Mañana":    "la mañana (7–13 h)",
    "t_Tarde":     "la tarde (14–20 h)",
    "t_Noche":     "la noche (21–23 h)",
    # Tipo de día
    "t_Laborable": "días laborables",
    "t_FinSemana": "fin de semana",
    # Quincenas
    "t_Q1mes": "la primera quincena del mes",
    "t_Q2mes": "la segunda quincena del mes",
    # Estaciones
    "t_Primavera": "primavera",
    "t_Verano":    "verano",
    "t_Otonio":    "otoño",
    "t_Invierno":  "invierno",
    # Festivos
    "t_Festivo":   "días festivos",
    # Minutos: cuartos de hora
    "t_M00": "el primer cuarto de hora (minutos 0–14)",
    "t_M15": "el segundo cuarto de hora (minutos 15–29)",
    "t_M30": "el tercer cuarto de hora (minutos 30–44)",
    "t_M45": "el último cuarto de hora (minutos 45–59)",
}

# ── 3b. Etiquetas para las variables de métrica (consecuente) ─────────────
ETIQUETA_METRICA_COLOQUIAL = {
    "v_MuyBaja":     "muy baja",
    "v_Baja":        "baja",
    "v_Media":       "media",
    "v_Alta":        "alta",
    "v_MuyAlta":     "muy alta",
    "v_OutlierBajo": "excepcionalmente baja",
    "v_OutlierAlto": "excepcionalmente alta",
}
ETIQUETA_METRICA_TECNICA = {
    "v_MuyBaja":     "muy baja",
    "v_Baja":        "baja",
    "v_Media":       "media",
    "v_Alta":        "alta",
    "v_MuyAlta":     "muy alta",
    "v_OutlierBajo": "excepcionalmente baja (outlier inferior)",
    "v_OutlierAlto": "excepcionalmente alta (outlier superior)",
}
ETIQUETA_METRICA = ETIQUETA_METRICA_TECNICA

# ── 3c. Jerarquía temporal: padre → lista de hijos ────────────────────────
JERARQUIA = {
    "t_Madrugada": [f"t_H{h:02d}" for h in range(0, 7)],
    "t_Mañana":    [f"t_H{h:02d}" for h in range(7, 14)],
    "t_Tarde":     [f"t_H{h:02d}" for h in range(14, 21)],
    "t_Noche":     [f"t_H{h:02d}" for h in range(21, 24)],
}
# Mapa inverso: hora → franja
HORA_A_FRANJA = {h: f for f, hs in JERARQUIA.items() for h in hs}

# ── 3d. Categorías temporales (para agrupar reglas) ────────────────────────
HORAS      = {f"t_H{h:02d}" for h in range(24)}
FRANJAS    = {"t_Madrugada", "t_Mañana", "t_Tarde", "t_Noche"}
MESES      = {"t_Ene","t_Feb","t_Marz","t_Abr","t_May","t_Jun",
              "t_Jul","t_Ago","t_Sep","t_Oct","t_Nov","t_Dic"}
DIAS       = {"t_Lun","t_Mar","t_Mie","t_Jue","t_Vie","t_Sab","t_Dom"}
ANIOS      = {f"t_{y}" for y in range(2000, 2051)}
TIPO_DIA   = {"t_Laborable","t_FinSemana"}
QUINCENAS  = {"t_Q1mes","t_Q2mes"}
MINUTOS    = {"t_M00","t_M15","t_M30","t_M45"}
FESTIVOS   = {"t_Festivo"}
ESTACIONES = {"t_Primavera","t_Verano","t_Otonio","t_Invierno"}

# Validación semántica
MESES_POR_ESTACION = {
    "t_Invierno":  {"t_Dic", "t_Ene", "t_Feb"},
    "t_Primavera": {"t_Marz", "t_Abr", "t_May"},
    "t_Verano":    {"t_Jun", "t_Jul", "t_Ago"},
    "t_Otonio":    {"t_Sep", "t_Oct", "t_Nov"},
}

# ── Constantes de la narrativa coloquial ───────────────────────────────────
HORAS_FRANJA_MAP = {
    "t_Madrugada": list(range(0, 7)),
    "t_Mañana":    list(range(7, 14)),
    "t_Tarde":     list(range(14, 21)),
    "t_Noche":     list(range(21, 24)),
}
NOMBRE_FRANJA = {
    "t_Madrugada": "Madrugada (0–6 h)",
    "t_Mañana":    "Mañana (7–13 h)",
    "t_Tarde":     "Tarde (14–20 h)",
    "t_Noche":     "Noche (21–23 h)",
}
NIVEL_COLOQUIAL = {
    "v_OutlierAlto": "excepcionalmente alto (un pico)",
    "v_MuyAlta": "muy alto",
    "v_Alta":    "alto",
    "v_Media":   "moderado",
    "v_Baja":    "bajo",
    "v_MuyBaja": "muy bajo",
    "v_OutlierBajo": "excepcionalmente bajo (un valle)",
}
NIVEL_EMOJI = {
    "v_OutlierAlto": "",
    "v_MuyAlta":     "",
    "v_Alta":        "",
    "v_Media":       "",
    "v_Baja":        "",
    "v_MuyBaja":     "",
    "v_OutlierBajo": "",
}
NIVEL_PESO = {
    "v_OutlierAlto": 7, "v_MuyAlta": 6, "v_Alta": 5,
    "v_Media": 4,
    "v_Baja": 3, "v_MuyBaja": 2, "v_OutlierBajo": 1,
}
