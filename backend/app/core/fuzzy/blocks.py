"""Generación de variables difusas temporales (t_*) y de métrica (v_*)."""

import numpy as np
import pandas as pd

from .constants import NOMBRES_MESES, TOL_HORAS
from .ramps import tol, trapecio


# ─────────────────────────────────────────────────────────────────────────────
# HELPER: GEOMETRÍA RUSPINI PARA BLOQUES TEMPORALES
# ─────────────────────────────────────────────────────────────────────────────

def _s_ruspini(duracion_bloque, gran, tolerancia, n_muestras_rampa=3):
    """
    Calcula el semiancho de transición (s) para la geometría Ruspini de un bloque.

    La geometría Ruspini para un bloque [inicio, fin] de duración D es:
        a = inicio - s
        b = inicio + s
        c = fin    - s
        d = fin    + s

    donde s es el semiancho de la zona de transición compartida con los bloques
    vecinos. Esta geometría garantiza que dos trapecios consecutivos se crucen
    exactamente en 0.5 en la frontera del bloque, y que la suma de pertenencias
    valga 1 en todo el dominio (condición de Ruspini).

    s se calcula como el máximo entre:
      - la rampa proporcional: tolerancia * duracion_bloque
      - el suelo mínimo de muestras: n_muestras_rampa * granularidad

    pero topado a duracion_bloque/2 - epsilon para que la meseta sea positiva.
    """
    s_prop   = tolerancia * duracion_bloque
    s_suelo  = n_muestras_rampa * gran
    # s_max garantiza que la meseta tenga duración positiva.
    # max(..., gran) evita que s_max sea negativo cuando gran > duracion_bloque/2
    # (caso teórico: GEN_* impide que ocurra en producción, pero es protección defensiva).
    s_max    = max(gran, duracion_bloque / 2 - gran / 2)
    return min(s_max, max(s_prop, s_suelo))


def _trapecio_ruspini(x, inicio, fin, s):
    """
    Trapecio Ruspini para el bloque [inicio, fin] con semiancho de transición s.

        a = inicio - s   (empieza a subir)
        b = inicio + s   (alcanza grado 1)
        c = fin    - s   (empieza a bajar)
        d = fin    + s   (llega a 0)

    Invariante: en x = inicio, este trapecio y el anterior dan 0.5 cada uno → suma 1.
    """
    a = inicio - s
    b = inicio + s
    c = fin    - s
    d = fin    + s
    return trapecio(x, a, b, c, d)


# ─────────────────────────────────────────────────────────────────────────────
# BLOQUES TEMPORALES
# ─────────────────────────────────────────────────────────────────────────────

def gen_t_anios(df, x, t0, x_max, anio_inicio, anio_fin, config):
    """BLOQUE 1: AÑO (t_2024, t_2025, ...). Una columna difusa por año."""
    gran  = config.granularidad_s
    n_ram = config.n_muestras_rampa

    for anio in range(anio_inicio, anio_fin + 1):
        inicio_anio = pd.Timestamp(year=anio,     month=1, day=1)
        fin_anio    = pd.Timestamp(year=anio + 1, month=1, day=1)

        inicio_s = (inicio_anio - t0).total_seconds()
        fin_s    = (fin_anio    - t0).total_seconds()
        dur      = fin_s - inicio_s

        s = _s_ruspini(dur, gran, tol(config.tol_anios), n_ram)
        df[f"t_{anio}"] = _trapecio_ruspini(x, inicio_s, fin_s, s)

    return df


def gen_t_meses(df, x, t0, x_max, anio_inicio, anio_fin, config):
    """BLOQUE 2: MESES (t_Ene, t_Feb, ...). Una columna difusa por mes."""
    gran  = config.granularidad_s
    n_ram = config.n_muestras_rampa

    for num_mes, nombre_mes in enumerate(NOMBRES_MESES, start=1):
        col_difusa = np.zeros_like(x, dtype=float)

        for anio in range(anio_inicio, anio_fin + 1):
            inicio_mes = pd.Timestamp(year=anio, month=num_mes, day=1)
            fin_mes    = (pd.Timestamp(year=anio + 1, month=1, day=1)
                          if num_mes == 12
                          else pd.Timestamp(year=anio, month=num_mes + 1, day=1))

            inicio_s = (inicio_mes - t0).total_seconds()
            fin_s    = (fin_mes    - t0).total_seconds()

            if fin_s < 0 or inicio_s > x_max:
                continue

            dur = fin_s - inicio_s
            s   = _s_ruspini(dur, gran, tol(config.tol_meses), n_ram)
            col_difusa = np.maximum(col_difusa, _trapecio_ruspini(x, inicio_s, fin_s, s))

        df[f"t_{nombre_mes}"] = col_difusa

    return df


def gen_t_dias(df, x, t0, x_max, var_tiempo, config):
    """BLOQUE 3: DÍAS DE LA SEMANA (t_Lun … t_Dom)."""
    gran  = config.granularidad_s
    n_ram = config.n_muestras_rampa

    indice_lunes = df[df[var_tiempo].dt.weekday == 0].index[0]
    b0           = int(df.loc[indice_lunes, "segundos"])

    duracion_dia    = 24 * 3600
    duracion_semana = 7  * duracion_dia
    nombres_dias    = ["Lun", "Mar", "Mie", "Jue", "Vie", "Sab", "Dom"]

    s = _s_ruspini(duracion_dia, gran, tol(config.tol_semanas), n_ram)

    for n_dia, nombre in enumerate(nombres_dias):
        dia_difuso = np.zeros_like(x, dtype=float)
        offset_dia = n_dia * duracion_dia

        k = 0
        while True:
            inicio = b0 + offset_dia + k * duracion_semana
            if inicio > x_max + duracion_semana:
                break
            fin = inicio + duracion_dia
            dia_difuso = np.maximum(dia_difuso, _trapecio_ruspini(x, inicio, fin, s))
            k += 1

        df[f"t_{nombre}"] = dia_difuso

    return df


def gen_t_horas(df, x, t0, x_max, var_tiempo, config):
    """BLOQUE 4: HORAS DEL DÍA (t_H00 … t_H23)."""
    gran  = config.granularidad_s
    n_ram = config.n_muestras_rampa

    duracion_hora = 3600
    duracion_dia  = 24 * 3600

    mascara_medianoche = (df[var_tiempo].dt.hour == 0) & (df[var_tiempo].dt.minute == 0)
    if mascara_medianoche.any():
        b0_hora = int(df.loc[mascara_medianoche.idxmax(), "segundos"])
    else:
        primer_dia = df[var_tiempo].min().normalize() + pd.Timedelta(days=1)
        b0_hora    = int((primer_dia - t0).total_seconds())

    s = _s_ruspini(duracion_hora, gran, tol(config.tol_horas), n_ram)

    for hora in range(24):
        col_difusa  = np.zeros_like(x, dtype=float)
        offset_hora = hora * duracion_hora

        k = 0
        while True:
            inicio = b0_hora + offset_hora + k * duracion_dia
            if inicio > x_max + duracion_dia:
                break
            fin = inicio + duracion_hora
            col_difusa = np.maximum(col_difusa, _trapecio_ruspini(x, inicio, fin, s))
            k += 1

        df[f"t_H{hora:02d}"] = col_difusa

    return df


def gen_t_laborables(df, config):
    """BLOQUE 5: LABORABLE / FIN DE SEMANA. Depende de gen_t_dias."""
    df["t_Laborable"] = df[["t_Lun", "t_Mar", "t_Mie", "t_Jue", "t_Vie"]].max(axis=1).round(4)
    df["t_FinSemana"] = df[["t_Sab", "t_Dom"]].max(axis=1).round(4)
    return df


def gen_t_festivos(df, var_tiempo, anio_inicio, anio_fin, config):
    """BLOQUE 10: DÍAS FESTIVOS (t_Festivo). Usa librería holidays."""
    try:
        import holidays as hol_lib
        anios_datos = list(range(anio_inicio, anio_fin + 1))
        if config.subdiv_festivos and config.subdiv_festivos.strip():
            festivos_set = set(hol_lib.country_holidays(
                config.pais_festivos, subdiv=config.subdiv_festivos, years=anios_datos
            ).keys())
        else:
            festivos_set = set(hol_lib.country_holidays(
                config.pais_festivos, years=anios_datos
            ).keys())

        df["t_Festivo"] = (
            df[var_tiempo].dt.date.apply(lambda d: 1.0 if d in festivos_set else 0.0)
        )
    except ImportError:
        print("  Librería 'holidays' no disponible. Generando t_Festivo=0.")
        df["t_Festivo"] = 0.0
    except Exception as e:
        print(f"  Error al obtener festivos: {e}")
        df["t_Festivo"] = 0.0

    return df


def gen_t_quincenas(df, x, t0, x_max, anio_inicio, anio_fin, config):
    """BLOQUE 6: PRIMERA / SEGUNDA QUINCENA DEL MES (t_Q1mes, t_Q2mes)."""
    gran  = config.granularidad_s
    n_ram = config.n_muestras_rampa

    for nombre_col, dia_inicio, dia_fin_offset in [
        ("t_Q1mes", 1,  15),
        ("t_Q2mes", 16, None),
    ]:
        col_difusa = np.zeros_like(x, dtype=float)

        for anio in range(anio_inicio, anio_fin + 1):
            for mes in range(1, 13):
                inicio = pd.Timestamp(year=anio, month=mes, day=dia_inicio)

                if dia_fin_offset is None:
                    fin = (pd.Timestamp(year=anio + 1, month=1, day=1)
                           if mes == 12
                           else pd.Timestamp(year=anio, month=mes + 1, day=1))
                else:
                    fin = pd.Timestamp(year=anio, month=mes, day=dia_fin_offset,
                                       hour=23, minute=59, second=59)

                inicio_s = (inicio - t0).total_seconds()
                fin_s    = (fin    - t0).total_seconds()

                if fin_s < 0 or inicio_s > x_max:
                    continue

                dur = fin_s - inicio_s
                s   = _s_ruspini(dur, gran, tol(config.tol_quincenas), n_ram)
                col_difusa = np.maximum(col_difusa, _trapecio_ruspini(x, inicio_s, fin_s, s))

        df[nombre_col] = col_difusa

    return df


def gen_t_estaciones(df, x, t0, x_max, anio_inicio, anio_fin, config):
    """BLOQUE 7: ESTACIONES DEL AÑO (t_Primavera, t_Verano, t_Otonio, t_Invierno)."""
    gran  = config.granularidad_s
    n_ram = config.n_muestras_rampa

    estaciones = {
        "t_Primavera": ((3, 20), (6, 20)),
        "t_Verano":    ((6, 21), (9, 22)),
        "t_Otonio":    ((9, 23), (12, 20)),
    }

    for nombre_col, ((m_ini, d_ini), (m_fin, d_fin)) in estaciones.items():
        col_difusa = np.zeros_like(x, dtype=float)

        for anio in range(anio_inicio, anio_fin + 1):
            inicio_ts = pd.Timestamp(year=anio, month=m_ini, day=d_ini)
            fin_ts    = pd.Timestamp(year=anio, month=m_fin, day=d_fin)

            inicio_s = (inicio_ts - t0).total_seconds()
            fin_s    = (fin_ts    - t0).total_seconds()

            if fin_s < 0 or inicio_s > x_max:
                continue

            dur = fin_s - inicio_s
            s   = _s_ruspini(dur, gran, tol(config.tol_estaciones), n_ram)
            col_difusa = np.maximum(col_difusa, _trapecio_ruspini(x, inicio_s, fin_s, s))

        df[nombre_col] = col_difusa

    # Invierno (cruza el año: 21 dic → 19 marz del año siguiente)
    col_invierno = np.zeros_like(x, dtype=float)
    for anio in range(anio_inicio - 1, anio_fin + 1):
        inicio_ts = pd.Timestamp(year=anio,     month=12, day=21)
        fin_ts    = pd.Timestamp(year=anio + 1, month=3,  day=19)

        inicio_s = (inicio_ts - t0).total_seconds()
        fin_s    = (fin_ts    - t0).total_seconds()

        if fin_s < 0 or inicio_s > x_max:
            continue

        dur = fin_s - inicio_s
        s   = _s_ruspini(dur, gran, tol(config.tol_estaciones), n_ram)
        col_invierno = np.maximum(col_invierno, _trapecio_ruspini(x, inicio_s, fin_s, s))

    df["t_Invierno"] = col_invierno
    return df


def gen_t_franjas(df, config):
    """BLOQUE 8: FRANJAS DEL DÍA (t_Madrugada, t_Mañana, t_Tarde, t_Noche)."""
    franjas = {
        "t_Madrugada": [f"t_H{h:02d}" for h in range(0,  7)],
        "t_Mañana":    [f"t_H{h:02d}" for h in range(7,  14)],
        "t_Tarde":     [f"t_H{h:02d}" for h in range(14, 21)],
        "t_Noche":     [f"t_H{h:02d}" for h in range(21, 24)],
    }
    for nombre_franja, cols_horas in franjas.items():
        existing_cols = [col for col in cols_horas if col in df.columns]
        if existing_cols:
            df[nombre_franja] = df[existing_cols].max(axis=1).round(4)
        else:
            df[nombre_franja] = 0.0
    return df


def gen_t_minutos(df, x, t0, x_max, var_tiempo, config):
    """BLOQUE 9: MINUTOS DEL RELOJ (cuartos de hora: t_M00, t_M15, t_M30, t_M45)."""
    gran  = config.granularidad_s
    n_ram = config.n_muestras_rampa

    duracion_cuarto = 15 * 60
    duracion_hora_s = 3600

    mascara_mm00 = (df[var_tiempo].dt.minute == 0) & (df[var_tiempo].dt.second == 0)
    if mascara_mm00.any():
        b0_min = int(df.loc[mascara_mm00.idxmax(), "segundos"])
    else:
        primer_h = df[var_tiempo].min().floor("H") + pd.Timedelta(hours=1)
        b0_min   = int((primer_h - t0).total_seconds())

    s = _s_ruspini(duracion_cuarto, gran, tol(config.tol_horas), n_ram)

    for cuarto_idx, minuto_inicio in enumerate([0, 15, 30, 45]):
        col_difusa = np.zeros_like(x, dtype=float)
        offset_min = minuto_inicio * 60

        k = 0
        while True:
            inicio = b0_min + offset_min + k * duracion_hora_s
            if inicio > x_max + duracion_hora_s:
                break
            fin = inicio + duracion_cuarto
            col_difusa = np.maximum(col_difusa, _trapecio_ruspini(x, inicio, fin, s))
            k += 1

        df[f"t_M{minuto_inicio:02d}"] = col_difusa

    return df


# ─────────────────────────────────────────────────────────────────────────────
# BLOQUES DE MÉTRICA
# ─────────────────────────────────────────────────────────────────────────────

def gen_v_metrica(df, var_metrica, config):
    """Genera las 7 variables difusas de métrica: v_MuyBaja…v_MuyAlta, v_Mediana, outliers."""
    serie = df[var_metrica]

    max_val = serie.max()
    min_val = serie.min()
    p10 = serie.quantile(0.10)
    p25 = serie.quantile(0.25)
    p35 = serie.quantile(0.35)
    p45 = serie.quantile(0.45)
    p50 = serie.quantile(0.50)
    p55 = serie.quantile(0.55)
    p65 = serie.quantile(0.65)
    p75 = serie.quantile(0.75)
    p90 = serie.quantile(0.90)

    df["v_MuyBaja"] = trapecio(serie, min_val - 1, min_val, p10, p25)
    df["v_Baja"]    = trapecio(serie, p10, p25, p35, p45)
    df["v_Media"]   = trapecio(serie, p35, p45, p55, p65)
    df["v_Alta"]    = trapecio(serie, p55, p65, p75, p90)
    df["v_MuyAlta"] = trapecio(serie, p75, p90, max_val, max_val + 1)

    # Mediana (indicador de proximidad al valor central, no partición)
    df["v_Mediana"] = trapecio(serie, p25, p50, p50, p75)

    # Outliers (media ± 2·std, indicadores de valores extremos)
    mean_val     = serie.mean()
    std_val      = serie.std()
    m_minus_2std = mean_val - 2 * std_val
    m_plus_2std  = mean_val + 2 * std_val

    df["v_OutlierBajo"] = trapecio(serie, min_val - 1, min_val, m_minus_2std, mean_val - std_val)
    df["v_OutlierAlto"] = trapecio(serie, mean_val + std_val, m_plus_2std, max_val, max_val + 1)

    # Variables absolutas con escala lógica
    generar_variables_absolutas(df, var_metrica)

    return df


def calcular_breakpoints_logicos(min_v, max_v):
    """
    Dado el rango real de la variable, devuelve breakpoints redondos que cubren
    ese rango uniformemente (entre 3 y 6 intervalos).
    Los breakpoints extremos se extienden media escala hacia fuera para garantizar
    que los trapecios de los extremos cubran el rango completo sin insertar
    valores crudos no redondeados.
    """
    rango = max_v - min_v
    if rango == 0:
        return [min_v]

    escalones_candidatos = [
        0.01, 0.02, 0.025, 0.05,
        0.1,  0.2,  0.25,  0.5,
        1,    2,    2.5,   5,
        10,   20,   25,    50,
        100,  200,  250,   500,
        1000, 2000, 2500,  5000,
    ]

    escalon = None
    for e in escalones_candidatos:
        if 3 <= rango / e <= 6:
            escalon = e
            break
    if escalon is None:
        escalon = round(rango / 4, 2)

    # Breakpoints interiores: múltiplos redondos del escalón dentro del rango
    primer_bp = np.ceil(min_v / escalon) * escalon
    breakpoints = []
    bp = primer_bp
    while bp <= max_v + escalon * 0.01:
        breakpoints.append(round(bp, 10))
        bp += escalon


    return breakpoints


def generar_variables_absolutas(df, var_metrica, tolerancia=0.2):
    """
    Genera variables difusas absolutas (v_abs_*) con geometría Ruspini triangular.

    Cada breakpoint bp_i genera un triángulo (b=c=bp_i) cuyos extremos tocan
    los breakpoints vecinos, garantizando que las pertenencias sumen 1 en el
    rango interior [bps[0], bps[-1]] (condición de Ruspini).

    """
    min_v = df[var_metrica].min()
    max_v = df[var_metrica].max()
    bps   = calcular_breakpoints_logicos(min_v, max_v)
    n     = len(bps)

    cols_generadas = []

    for i, bp in enumerate(bps):
        # Extremo izquierdo de la rampa: breakpoint vecino izquierdo, o espejo
        a = bps[i - 1] if i > 0     else bp - (bps[1] - bp)
        # Extremo derecho de la rampa: breakpoint vecino derecho, o espejo
        d = bps[i + 1] if i < n - 1 else bp + (bp - bps[i - 1])

        # Triángulo: b = c = bp (vértice en el valor exacto, Ruspini garantizado)
        nombre_bp = str(round(bp, 4)).replace(".", "_").replace("-", "neg")
        col = f"v_abs_{nombre_bp}"
        df[col] = trapecio(df[var_metrica], a, bp, bp, d)
        cols_generadas.append(col)

    return cols_generadas


# ─────────────────────────────────────────────────────────────────────────────
# LIMPIEZA
# ─────────────────────────────────────────────────────────────────────────────

def filtrar_variables_constantes(df, prefijos=('t_', 'v_')):
    """Elimina columnas difusas que son constantes (todo 0 o todo 1)."""
    cols_difusas   = [c for c in df.columns if any(c.startswith(p) for p in prefijos)]
    cols_eliminar  = [c for c in cols_difusas if df[c].nunique() <= 1]
    df_filtrado    = df.drop(columns=cols_eliminar)
    print(f"Columnas eliminadas por ser constantes: {cols_eliminar}")
    return df_filtrado