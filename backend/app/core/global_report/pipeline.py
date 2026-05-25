# -*- coding: utf-8 -*-
import re
from datetime import datetime

from ..nlg.templates import HORAS_FRANJA_MAP, NOMBRE_FRANJA
from .aggregators import (
    cargar_reglas_todos,
    construir_tabla_cross_sensor,
    patrones_compartidos,
    detectar_atipicos,
    comparar_perfiles_dia,
)
from .narrative import (
    parrafo_coloquial_global,
    parrafo_introductorio,
    parrafo_hallazgos_comunes,
    parrafo_atipicos,
    parrafo_outliers,
)


def _detectar_bloques_de_reglas(reglas_por_sensor: dict) -> dict:
    """
    Infiere qué bloques temporales están presentes a partir de los tokens
    de los antecedentes de todas las reglas cargadas.
    """
    tokens: set = set()
    for df in reglas_por_sensor.values():
        for ant in df["antecedente"]:
            for t in ant.split(" AND "):
                tokens.add(t)

    return {
        "HAY_HORAS":      any(re.match(r'^t_H\d{2}$', t) for t in tokens),
        "HAY_FRANJAS":    bool(tokens & {"t_Madrugada", "t_Mañana", "t_Tarde", "t_Noche"}),
        "HAY_MINUTOS":    any(re.match(r'^t_M\d{2}$', t) for t in tokens),
        "HAY_MESES":      bool(tokens & {"t_Ene","t_Feb","t_Marz","t_Abr","t_May","t_Jun",
                                         "t_Jul","t_Ago","t_Sep","t_Oct","t_Nov","t_Dic"}),
        "HAY_ESTACIONES": bool(tokens & {"t_Primavera","t_Verano","t_Otonio","t_Invierno"}),
        "HAY_DIAS":       bool(tokens & {"t_Lun","t_Mar","t_Mie","t_Jue","t_Vie","t_Sab","t_Dom"}),
        "HAY_TIPO_DIA":   bool(tokens & {"t_Laborable","t_FinSemana"}),
        "HAY_QUINCENAS":  bool(tokens & {"t_Q1mes","t_Q2mes"}),
        "HAY_FESTIVOS":   "t_Festivo" in tokens,
        "HAY_ANIOS":      any(re.match(r'^t_\d{4}$', t) for t in tokens),
    }


def _ensamblar_informe(tabla_cross, comunes, atipicos, reglas_por_sensor,
                       nombre_conjunto: str, metricas: list,
                       nombre_metrica_global: str, bloques: dict) -> str:
    """
    Ensambla el informe Markdown completo.
    Corresponde a construir_informe_global() en la celda 14 del notebook,
    con las referencias a globales reemplazadas por parámetros.
    """
    HAY_HORAS   = bloques.get("HAY_HORAS", False)
    HAY_FRANJAS = bloques.get("HAY_FRANJAS", False)

    n_sensores = tabla_cross["Sensor"].nunique()
    fecha = datetime.now().strftime("%Y-%m-%d")
    lineas = []

    # ── 1. Cabecera ──────────────────────────────────────────────────────────
    lineas.append(f"# Informe Global Comparativo — {nombre_conjunto}")
    lineas.append("")
    lineas.append(
        f"*Generado el {fecha} "
        f"| {n_sensores} {'fuente' if n_sensores == 1 else 'fuentes'} de datos analizada{'s' if n_sensores != 1 else ''} "
        f"| {tabla_cross['Reglas'].sum()} patrones en total*"
    )
    lineas.append("")

    # ── 2. Narrativa coloquial ───────────────────────────────────────────────
    lineas.append(f"## ¿Cómo se comporta **{', '.join(metricas)}** en {nombre_conjunto}?")
    lineas.append("")
    lineas.append(
        "> Esta sección resume los hallazgos principales en lenguaje sencillo, "
        "sin tecnicismos. Los detalles técnicos se encuentran en las secciones siguientes."
    )
    lineas.append("")
    lineas.append(parrafo_coloquial_global(tabla_cross, nombre_conjunto))
    lineas.append("")

    # ── 3. Tabla comparativa global ──────────────────────────────────────────
    lineas.append("## Tabla comparativa global")
    lineas.append("")

    if HAY_HORAS or HAY_FRANJAS:
        lineas.append(
            f"Cada fila representa una fuente de datos. "
            f"La columna **Perfil del día** muestra el nivel de **{nombre_metrica_global}** "
            f"dominante en cada franja (Madrugada | Mañana | Tarde | Noche): "
            f"🔴 excepcional · 🟠 muy alto · 🟡 alto · 🟢 moderado · 🔵 bajo · 🟣 muy bajo · ⚪ mínimo."
        )
    else:
        lineas.append(
            f"Cada fila representa una fuente de datos. "
            f"La columna **Patrón calendario dominante** indica el período temporal "
            f"(mes, estación, año) más recurrente en las reglas detectadas."
        )
    lineas.append("")

    _cols_candidatas = [
        "Sensor", "Métrica", "Reglas", "Conf. media (%)", "Lift medio", "Lift máx",
        "Nivel dominante",
        "Perfil del día",
        "Patrón calendario dominante",
        "Hora más mencionada en reglas",
        "Día más mencionado",
        "Outlier alto", "Outlier bajo",
    ]
    cols_mostrar = [c for c in _cols_candidatas if c in tabla_cross.columns]
    lineas.append(tabla_cross[cols_mostrar].to_markdown(index=False))
    lineas.append("")

    # ── 4. Análisis técnico ──────────────────────────────────────────────────
    lineas.append("## Análisis técnico comparativo")
    lineas.append("")
    lineas.append(parrafo_introductorio(tabla_cross, nombre_conjunto))
    lineas.append("")

    lineas.append("### Patrones compartidos entre fuentes de datos")
    lineas.append("")
    lineas.append(parrafo_hallazgos_comunes(comunes, n_sensores, nombre_conjunto))
    lineas.append("")

    lineas.append("### Fuentes con comportamiento atípico")
    lineas.append("")
    lineas.append(parrafo_atipicos(atipicos, tabla_cross))
    lineas.append("")

    _texto_outliers = parrafo_outliers(tabla_cross)
    if _texto_outliers:
        lineas.append("### Comportamientos extremos (outliers)")
        lineas.append("")
        lineas.append(_texto_outliers)
        lineas.append("")

    _frases_perfil = comparar_perfiles_dia(tabla_cross)
    if _frases_perfil:
        if HAY_HORAS or HAY_FRANJAS:
            lineas.append("### Comparativa de perfiles de día")
            lineas.append("")
            lineas.append(
                "Cada fuente tiene un perfil diario propio. "
                "Las fuentes con perfil idéntico comparten el mismo patrón estructural."
            )
        else:
            lineas.append("### Comparativa de patrones calendario")
            lineas.append("")
            lineas.append(
                "Cada fuente tiene un patrón calendario propio. "
                "Las fuentes con patrón idéntico comparten el mismo período temporal dominante."
            )
        lineas.append("")
        for frase in _frases_perfil:
            lineas.append(frase)
            lineas.append("")

    # ── 5. Enlaces a informes individuales ──────────────────────────────────
    lineas.append("---")
    lineas.append("")
    lineas.append("## Análisis detallado por fuente de datos")
    lineas.append("")
    lineas.append(
        "Para el desglose completo de reglas, visualizaciones y narrativa, "
        "consultar los informes individuales generados por `src03`:"
    )
    lineas.append("")
    for (sensor, metrica) in sorted(reglas_por_sensor.keys()):
        nombre_m = metrica.replace("_", " ").capitalize()
        lineas.append(
            f"- [{sensor} — {nombre_m}]"
            f"(./{sensor}_{metrica}_resumen.md)"
        )
    lineas.append("")

    return "\n".join(lineas)


# ---------------------------------------------------------------------------
# Función pública del módulo
# ---------------------------------------------------------------------------

def construir_informe_global(rutas_reglas: list, nombre_conjunto: str = "") -> str:
    """
    Pipeline completo del informe global: CSVs de reglas → informe Markdown.

    Entrada:
      rutas_reglas   — lista de paths a CSVs de reglas (salida de src02).
                       Formato de nombre esperado: {sensor}_{metrica}_reglas.csv
      nombre_conjunto — etiqueta descriptiva del conjunto (p.ej. "Madrid").
                       Si está vacío, se infiere de los sensores.

    Salida:
      String Markdown con el informe global comparativo.
    """
    reglas_por_sensor, faltantes = cargar_reglas_todos(rutas_reglas)
    if not reglas_por_sensor:
        raise ValueError(f"No se pudo cargar ningún CSV de reglas. Faltantes: {faltantes}")

    bloques = _detectar_bloques_de_reglas(reglas_por_sensor)

    tabla_cross = construir_tabla_cross_sensor(reglas_por_sensor, bloques)
    comunes     = patrones_compartidos(reglas_por_sensor)
    atipicos    = detectar_atipicos(tabla_cross)

    if not nombre_conjunto:
        sensores = sorted({s for s, _ in reglas_por_sensor.keys()})
        nombre_conjunto = ", ".join(sensores)

    metricas            = sorted({m for _, m in reglas_por_sensor.keys()})
    nombre_metrica_global = metricas[0] if len(metricas) == 1 else ", ".join(metricas)

    return _ensamblar_informe(
        tabla_cross, comunes, atipicos, reglas_por_sensor,
        nombre_conjunto, metricas, nombre_metrica_global, bloques,
    )
