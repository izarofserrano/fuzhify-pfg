from dataclasses import dataclass
from datetime import date as _date

import pandas as pd

from .constants import MIN_REGLAS_GRUPO
from .detection import (
    detectar_bloques,
    detectar_granularidad,
    detectar_var_tiempo,
    _construir_grupos_src03,
)
from .templates import (
    ETIQUETA_METRICA_COLOQUIAL,
    ETIQUETA_METRICA_TECNICA,
    ETIQUETA_METRICA,
    NIVEL_EMOJI,
    NIVEL_COLOQUIAL,
    NIVEL_PESO,
    HORAS_FRANJA_MAP,
    NOMBRE_FRANJA,
    HORAS,
    FRANJAS,
    ANIOS,
    MESES,
    ESTACIONES,
)
from .verbalize import (
    parsear_antecedente,
    verbalizar_antecedente,
    es_combinacion_valida,
    categoria_dominante,
    franja_de_tokens,
    listar_en_español,
    construir_calidad,
    regla_a_frase,
    agrupar_reglas,
)


# ── Config ───────────────────────────────────────────────────────────────────

@dataclass
class NLGConfig:
    nombre_dataset: str    = ""
    metrica: str           = ""          # si vacío, se auto-detecta del CSV
    min_reglas_grupo: int  = MIN_REGLAS_GRUPO
    var_tiempo: str        = ""          # si vacío, se auto-detecta
    min_soporte: float     = 0.005
    min_confianza: float   = 0.50
    lift_minimo: float     = 1.0
    max_prof: int          = 3
    k_beam: int            = 10
    top_por_consecuente: int = 10
    pais: str              = "ES"
    subdiv: str            = ""
    usar_llm_sintesis: bool      = False
    proveedor_llm: str           = "gemini"
    llm_api_key: str | None      = None


# ---------------------------------------------------------------------------
# 5. grupo_a_parrafo - celda 9 del notebook
# ---------------------------------------------------------------------------

def grupo_a_parrafo(filas, nombre_metrica, consecuente, min_reglas, modo="tecnico"):
    """
    Convierte un grupo de filas (mismo consecuente + contexto similar) en un
    párrafo narrativo. Si el grupo tiene < min_reglas, genera frases sueltas.

    modo="tecnico":   incluye confianza y lift entre paréntesis (apéndice).
    modo="coloquial": omite las cifras técnicas (cuerpo del informe).
    """
    diccionario = (ETIQUETA_METRICA_COLOQUIAL if modo == "coloquial"
                   else ETIQUETA_METRICA_TECNICA)
    desc_v = diccionario.get(consecuente, consecuente)
    filas_ordenadas = sorted(filas, key=lambda r: -r["lift"])

    # ── Caso A: grupo pequeño → frases individuales ───────────────────────
    if len(filas_ordenadas) < min_reglas:
        return "\n".join(regla_a_frase(f, nombre_metrica, modo=modo)
                         for f in filas_ordenadas)

    # ── Caso B: grupo amplio → párrafo narrativo ──────────────────────────
    conjuntos = [parsear_antecedente(f["antecedente"]) for f in filas_ordenadas]
    contexto_comun = conjuntos[0].copy()
    for c in conjuntos[1:]:
        contexto_comun &= c

    # Calcular tokens específicos de cada regla
    especificos = [c - contexto_comun for c in conjuntos]

    # ── Caso B.1: los detalles diferenciales son solo años → frase simple ──
    solo_anios = all(e <= ANIOS or not e for e in especificos)
    if solo_anios:
        desc_ctx = verbalizar_antecedente(contexto_comun) if contexto_comun \
                   else verbalizar_antecedente(conjuntos[0])
        prefijo  = "A" if contexto_comun & HORAS else "En"

        if modo == "tecnico":
            conf_media = sum(f["confianza"] for f in filas_ordenadas) / len(filas_ordenadas)
            lift_max   = max(f["lift"] for f in filas_ordenadas)
            return (
                f"{prefijo} {desc_ctx}, la {nombre_metrica} tiende a ser {desc_v} "
                f"(confianza media {int(round(conf_media*100))} %, "
                f"lift máximo {lift_max:.1f})."
            )
        else:  # coloquial
            return (
                f"{prefijo} {desc_ctx}, la {nombre_metrica} tiende a ser {desc_v}."
            )

    # ── Caso B.2: párrafo narrativo completo ──────────────────────────────
    detalles = []
    for f, especif in zip(filas_ordenadas, especificos):
        if especif:
            especif_filtrado = especif - ANIOS if (especif - ANIOS) else especif
            desc = verbalizar_antecedente(especif_filtrado)
        else:
            desc = verbalizar_antecedente(parsear_antecedente(f["antecedente"]))

        if modo == "tecnico":
            conf_pct = int(round(f["confianza"] * 100))
            detalles.append(f"{desc} ({conf_pct} %)")
        else:  # coloquial
            detalles.append(desc)

    if contexto_comun:
        ctx_desc = verbalizar_antecedente(contexto_comun)
        intro = (
            f"En el contexto de {ctx_desc}, la {nombre_metrica} tiende a ser "
            f"{desc_v}, especialmente en {listar_en_español(detalles)}."
        )
    else:
        intro = (
            f"La {nombre_metrica} tiende a ser {desc_v} en los siguientes "
            f"contextos: {listar_en_español(detalles)}."
        )

    if modo == "tecnico":
        conf_media = sum(f["confianza"] for f in filas_ordenadas) / len(filas_ordenadas)
        lift_max   = max(f["lift"] for f in filas_ordenadas)
        stats = (
            f"Este patrón se observa con una confianza media del "
            f"{int(round(conf_media*100))} % y un lift máximo de {lift_max:.1f}."
        )
        return intro + " " + stats
    else:  # coloquial
        return intro


# ---------------------------------------------------------------------------
# 6a. Narrativa diaria - celda 11 del notebook
# ---------------------------------------------------------------------------

def _consecuente_hora(df_reglas, hora):
    """Devuelve (consecuente, lift) con más lift para una hora específica."""
    tok = f"t_H{hora:02d}"
    mask = df_reglas["antecedente"].str.contains(tok, regex=False)
    sub = df_reglas[mask]
    if sub.empty:
        return None
    idx = sub["lift"].idxmax()
    return sub.loc[idx, "consecuente"], sub.loc[idx, "lift"]


def _consecuente_franja(df_reglas, franja_tok):
    """Devuelve (consecuente, lift) más fuerte para una franja entera."""
    mask = df_reglas["antecedente"].str.contains(franja_tok, regex=False)
    sub = df_reglas[mask]
    if sub.empty:
        return None
    idx = sub["lift"].idxmax()
    return sub.loc[idx, "consecuente"], sub.loc[idx, "lift"]


def _mapa_horario(df_reglas):
    """
    Construye un diccionario {hora: consecuente_dominante} basado en la regla
    con mayor lift para cada hora.
    """
    mapa = {}
    for h in range(24):
        tok = f"t_H{h:02d}"
        mask = df_reglas["antecedente"].str.contains(tok, regex=False)
        sub = df_reglas[mask]
        if not sub.empty:
            idx = sub["lift"].idxmax()
            mapa[h] = sub.loc[idx, "consecuente"]
    return mapa


def _nota_fds(df_reglas, mapa_horario, nombre_metrica):
    """
    Genera la nota de fin de semana solo si hay reglas que la justifiquen,
    y distingue entre 'inversión' y 'reducción'.
    """
    NIVELES_ALTOS = {"v_OutlierAlto", "v_MuyAlta", "v_Alta"}
    NIVELES_BAJOS = {"v_Baja", "v_MuyBaja", "v_OutlierBajo"}

    hay_fds = any(
        "t_FinSemana" in a or "t_Sab" in a or "t_Dom" in a
        for a in df_reglas["antecedente"]
    )
    if not hay_fds:
        return None

    # Detectar si alguna franja laboral alta tiene contraparte baja en fds
    hay_inversion = False
    for franja_tok, horas in HORAS_FRANJA_MAP.items():
        niveles_lab = [
            mapa_horario[h] for h in horas
            if h in mapa_horario
            and any("t_Laborable" in a and f"t_H{h:02d}" in a
                    for a in df_reglas["antecedente"])
        ]
        niveles_fds = [
            mapa_horario[h] for h in horas
            if h in mapa_horario
            and any(
                ("t_FinSemana" in a or "t_Sab" in a or "t_Dom" in a)
                and f"t_H{h:02d}" in a
                for a in df_reglas["antecedente"]
            )
        ]
        if any(n in NIVELES_ALTOS for n in niveles_lab) and \
           any(n in NIVELES_BAJOS for n in niveles_fds):
            hay_inversion = True
            break

    if hay_inversion:
        return (
            "Los **fines de semana** invierten el patrón laboral: "
            "las franjas de mayor actividad entre semana presentan "
            + nombre_metrica + " sensiblemente más bajo."
        )
    else:
        return (
            "Los **fines de semana** el " + nombre_metrica + " se reduce respecto a los días laborables, "
            "aunque sin llegar a invertir el patrón general."
        )


def _parrafo_coloquial(df_reglas, mapa_horario, nombre_metrica, nombre_franja=None):
    """
    Genera prosa narrativa por franjas, variando la estructura sintáctica
    para evitar repetición y fusionando el contexto de forma fluida.
    """
    if nombre_franja is None:
        nombre_franja = NOMBRE_FRANJA

    def _nivel_franja(horas):
        # Recoge TODAS las reglas de la franja, no solo el pico por hora
        patron = "|".join(f"t_H{h:02d}" for h in horas)
        sub = df_reglas[df_reglas["antecedente"].str.contains(patron, regex=True)]
        if sub.empty:
            return None

        # Suma lift × confianza por nivel
        votos: dict = {}
        for _, row in sub.iterrows():
            n = row["consecuente"]
            votos[n] = votos.get(n, 0.0) + row["lift"] * row["confianza"]

        return max(votos, key=votos.get)

    def _ctx_franja(sub, horas):
        """Devuelve dict con flags de contexto para la franja."""
        ants = list(sub["antecedente"])
        return {
            "lab": any("t_Laborable" in a for a in ants),
            "fds": any(("t_FinSemana" in a or "t_Sab" in a or "t_Dom" in a) for a in ants),
            "ago": any("t_Ago" in a for a in ants),
            "fes": any("t_Festivo" in a for a in ants),
        }

    def _outlier_matiz(nivel_clave, horas):
        """Devuelve texto del matiz puntual si aplica, o ''."""
        niveles_en_franja = [mapa_horario.get(h) for h in horas if h in mapa_horario]
        if "v_OutlierAlto" in niveles_en_franja and nivel_clave != "v_OutlierAlto":
            h = next(h for h in horas if mapa_horario.get(h) == "v_OutlierAlto")
            return f"pico excepcional a las {h} h"
        if "v_OutlierBajo" in niveles_en_franja and nivel_clave != "v_OutlierBajo":
            h = next(h for h in horas if mapa_horario.get(h) == "v_OutlierBajo")
            return f"mínimo absoluto a las {h} h"
        return ""

    # Plantillas con estructura sintáctica diferente por franja
    def _frase_madrugada(rango, nivel, emoji, matiz, ctx, **kwargs):
        base = f"De madrugada ({rango}), el " + nombre_metrica + " es **" + nivel + "**"
        detalles = []
        if matiz:
            if ctx["lab"]:
                detalles.append(f"llegando a ser {matiz} en laborables")
            else:
                detalles.append(matiz)
        elif ctx["lab"] and ctx["fds"]:
            detalles.append("más pronunciado en días laborables que en fin de semana")
        if ctx["ago"]:
            detalles.append("con variación en agosto")
        sufijo = (", " + ", ".join(detalles)) if detalles else ""
        return base + sufijo + "."

    def _frase_manana(rango, nivel, emoji, matiz, ctx, nivel_prev=None, nivel_clave=None):
        # Verbo según comparación con franja previa (madrugada)
        if nivel_prev is not None and nivel_clave is not None:
            p_act  = NIVEL_PESO.get(nivel_clave, 0)
            p_prev = NIVEL_PESO.get(nivel_prev, 0)
            if p_act > p_prev + 1:
                if nivel_prev == "v_OutlierBajo":
                    verbo = "mejora hasta niveles"
                else:
                    verbo = "sube hasta niveles"
            elif p_act < p_prev - 1:
                verbo = "baja a niveles"
            elif p_act == p_prev:
                verbo = "se mantiene en niveles"
            else:
                verbo = "se sitúa en niveles"
        else:
            verbo = "alcanza niveles"

        base = f"Al llegar la mañana ({rango}), el {nombre_metrica} {verbo} **{nivel}**"
        detalles = []
        if ctx["lab"] and ctx["fds"]:
            detalles.append("en días laborables; se reduce sensiblemente en fin de semana")
        elif ctx["lab"]:
            detalles.append("sobre todo en días laborables")
        if ctx["fes"]:
            detalles.append("y cae en festivos")
        if ctx["ago"]:
            detalles.append("con un patrón distinto en agosto")
        sufijo = (", " + ", ".join(detalles)) if detalles else ""
        return base + sufijo + "."

    def _frase_tarde(rango, nivel, emoji, matiz, ctx, nivel_prev=None, nivel_clave=None):
        if nivel_prev is not None and nivel_clave is not None:
            p_act = NIVEL_PESO.get(nivel_clave, 0)
            p_prev = NIVEL_PESO.get(nivel_prev, 0)
            if p_act > p_prev + 1:
                verbo = "sube a niveles"
            elif p_act < p_prev - 1:
                verbo = "desciende a niveles"
            elif p_act == p_prev:
                verbo = "se mantiene"
            else:
                verbo = "queda en niveles"
        else:
            verbo = "se sitúa en niveles"

        base = f"Por la tarde ({rango}), el {nombre_metrica} {verbo} **{nivel}**"
        detalles = []
        if ctx["lab"] and ctx["fds"]:
            detalles.append("especialmente entre semana, con calma en fin de semana")
        elif ctx["lab"]:
            detalles.append("con mayor intensidad en días laborables")
        if ctx["ago"]:
            detalles.append("aunque agosto rompe este patrón")
        sufijo = (", " + ", ".join(detalles)) if detalles else ""
        return base + sufijo + "."

    def _frase_noche(rango, nivel, emoji, matiz, ctx, nivel_prev=None, nivel_clave=None):
        if nivel_prev is not None and nivel_clave is not None:
            p_act = NIVEL_PESO.get(nivel_clave, 0)
            p_prev = NIVEL_PESO.get(nivel_prev, 0)
            if p_act < p_prev - 1:
                verbo = "cae a un nivel"
            elif p_act > p_prev + 1:
                verbo = "repunta a un nivel"
            elif p_act == p_prev:
                verbo = "se mantiene en un nivel"
            else:
                verbo = "queda en un nivel"
        else:
            verbo = "se sitúa en un nivel"

        base = f"Al caer la noche ({rango}), el {nombre_metrica} {verbo} **{nivel}**"
        detalles = []
        if matiz:
            detalles.append(f"con un {matiz}")
        if ctx["fds"]:
            detalles.append("algo más escaso en fin de semana")
        sufijo = (", " + ", ".join(detalles)) if detalles else ""
        return base + sufijo + "."

    PLANTILLAS = {
        "t_Madrugada": _frase_madrugada,
        "t_Mañana":    _frase_manana,
        "t_Tarde":     _frase_tarde,
        "t_Noche":     _frase_noche,
    }

    frases = []
    nivel_prev = None
    for franja_tok, horas in HORAS_FRANJA_MAP.items():
        nivel_clave = _nivel_franja(horas)
        if nivel_clave is None:
            nombre_corto = NOMBRE_FRANJA[franja_tok].split(" ")[0].lower()
            frases.append(
                f"{'Por la' if nombre_corto in ('tarde','noche') else 'Durante la'} "
                f"{nombre_corto} el sistema no detecta ningún patrón temporal estable."
            )
            nivel_prev = None
            continue

        nivel = NIVEL_COLOQUIAL[nivel_clave]
        emoji = NIVEL_EMOJI[nivel_clave]
        rango = f"{horas[0]}–{horas[-1]} h"

        patron_horas = "|".join([f"t_H{h:02d}" for h in horas])
        mask = (
            df_reglas["antecedente"].str.contains(franja_tok, regex=False) |
            df_reglas["antecedente"].str.contains(patron_horas, regex=True)
        )
        ctx   = _ctx_franja(df_reglas[mask], horas)
        matiz = _outlier_matiz(nivel_clave, horas)

        frase = PLANTILLAS[franja_tok](
            rango, nivel, emoji, matiz, ctx,
            nivel_prev=nivel_prev, nivel_clave=nivel_clave
        )
        frases.append(frase)
        nivel_prev = nivel_clave

    texto = " ".join(frases)

    notas = []

    nota_fds = _nota_fds(df_reglas, mapa_horario, nombre_metrica)
    if nota_fds:
        notas.append(nota_fds)

    tiene_fes = any("t_Festivo" in a for a in df_reglas["antecedente"])
    if tiene_fes:
        notas.append(
            "Los **festivos** se comportan de forma similar al fin de semana "
            "con independencia del día de la semana en que caigan."
        )

    if notas:
        texto += "\n\n" + " ".join(notas)

    return texto


def _detalle_por_franja(df_reglas, nombre_metrica, min_reglas_grupo=2):
    """
    Sección técnica organizada por franja horaria.
    Dentro de cada franja, reglas ordenadas por consecuente (mayor→menor) y lift.
    """
    lineas = []
    ORDEN = ["v_OutlierAlto","v_MuyAlta","v_Alta","v_Media",
             "v_Baja","v_MuyBaja","v_OutlierBajo"]

    for franja_tok, horas in HORAS_FRANJA_MAP.items():
        nombre_f = NOMBRE_FRANJA[franja_tok]
        patron_horas = "|".join([f"t_H{h:02d}" for h in horas])
        mask = (
            df_reglas["antecedente"].str.contains(franja_tok, regex=False) |
            df_reglas["antecedente"].str.contains(patron_horas, regex=True)
        )
        sub = df_reglas[mask].copy()
        if sub.empty:
            continue

        sub = sub.sort_values("lift", ascending=False)
        lineas.append(f"### {nombre_f}")
        lineas.append("")

        for cons in ORDEN:
            sub_c = sub[sub["consecuente"] == cons]
            if sub_c.empty:
                continue
            desc_v = ETIQUETA_METRICA.get(cons, cons)
            emoji  = NIVEL_EMOJI.get(cons, "")
            for _, row in sub_c.iterrows():
                tokens   = parsear_antecedente(row["antecedente"])
                desc_t   = verbalizar_antecedente(tokens)
                conf_pct = int(round(row["confianza"] * 100))
                lift_val = f"{row['lift']:.1f}"
                cal      = construir_calidad(df_reglas)(row)
                lineas.append(
                    f"- **{desc_v.capitalize()}** {cal}: "
                    f"{desc_t} (confianza {conf_pct} %, lift {lift_val})"
                )
        lineas.append("")

    return "\n".join(lineas)


def _parrafo_calendario(df_reglas, nombre_metrica, lift_min=3.0, top_n=3):
    """
    Genera un párrafo con las reglas no horarias más fuertes (mes, estación, año).
    Solo se incluye cuando existen reglas con lift >= lift_min.
    """
    TOKENS_NO_HORARIOS = MESES | ESTACIONES | ANIOS
    TOKENS_HORARIOS    = HORAS | FRANJAS

    mask = df_reglas["antecedente"].apply(
        lambda a: bool(parsear_antecedente(a) & TOKENS_NO_HORARIOS)
                  and not bool(parsear_antecedente(a) & TOKENS_HORARIOS)
    )
    sub = df_reglas[mask & (df_reglas["lift"] >= lift_min)] \
            .sort_values("lift", ascending=False) \
            .head(top_n)

    if sub.empty:
        return None

    lineas = ["## Patrones estacionales y de calendario", ""]
    lineas.append(
        "_Los siguientes patrones no están ligados a una franja horaria concreta "
        "sino a períodos del calendario con comportamiento diferencial._"
    )
    lineas.append("")
    for _, row in sub.iterrows():
        tokens  = parsear_antecedente(row["antecedente"])
        desc_t  = verbalizar_antecedente(tokens)
        desc_v  = ETIQUETA_METRICA.get(row["consecuente"], row["consecuente"])
        emoji   = NIVEL_EMOJI.get(row["consecuente"], "")
        conf    = int(round(row["confianza"] * 100))
        lineas.append(
            f"- En **{desc_t}**, la {nombre_metrica} tiende a ser "
            f"**{desc_v}** (confianza {conf} %, lift {row['lift']:.1f})."
        )
    return "\n".join(lineas)


def _generar_glosario_breve(metrica):
    """Glosario corto, sin jerga técnica: para la cabecera."""
    return (
        "> ### Niveles de la métrica analizada (" + metrica + ") \n"
        "> Escala desde **excepcionalmente bajo** hasta **excepcionalmente alto**, "
        "calculada a partir de la desviación sobre la media histórica del propio sensor.\n"
        ">\n"
        "> Cuando el patrón es *muy diferenciado* del comportamiento normal se describe "
        "*'de forma notable'* o *'muy marcada'*. Cuando es solo una *tendencia*, se dice así."
    )


def _generar_glosario_tecnico():
    """Glosario completo: para insertar al INICIO del apéndice técnico."""
    return (
        "> ### Glosario técnico (apéndice)\n"
        "> * **Confianza:** probabilidad (0–100 %) de que el patrón sea cierto cuando "
        "se da el contexto. Confianza 80 % significa que, en ese contexto, el la métrica "
        "se comporta así 8 de cada 10 veces.\n"
        "> * **Lift:** cuántas veces más probable es el evento respecto al azar. "
        "Lift 5.0 significa que el patrón es 5 veces más frecuente en ese contexto "
        "que en el resto del tiempo.\n"
        "> * **Outlier inferior/superior:** valor más allá de 2 desviaciones típicas "
        "de la media histórica del sensor."
    )


# ---------------------------------------------------------------------------
# Síntesis LLM con prompt específico por sección
# ---------------------------------------------------------------------------

def _sintetizar_con_prompt(prompt: str, config) -> str | None:
    """
    Llama al LLM con un prompt a medida. Degrada con elegancia si falla
    o si usar_llm_sintesis=False.
    """
    if not config.usar_llm_sintesis:
        return None
    try:
        from app.core.fuzzy.heuristic import _llamar_llm
        respuesta = _llamar_llm(
            prompt,
            proveedor=config.proveedor_llm,
            api_key=config.llm_api_key,
        )
        if respuesta and len(respuesta.strip()) > 20:
            lineas_resp = respuesta.strip().splitlines()
            return "\n> ".join(lineas_resp)
        return None
    except Exception:
        return None


# ---------------------------------------------------------------------------
# 6b. generar_resumen - celda 12 del notebook (adaptada a parámetros explícitos)
# ---------------------------------------------------------------------------

def generar_resumen(df_reglas, dataset, metrica, min_reglas_grupo=2,
                    bloques=None, granularidad_desc="desconocida",
                    grupos_excluyentes=None, config=None):
    """
    Genera el resumen completo en Markdown.

    Estructura:
      0. Cabecera de metadatos
      1. Cabecera
      2. Narrativa coloquial
      3. Sección de patrones estacionales (si aplica)
      4. Análisis técnico por franja horaria (si hay horas/franjas)
      5. Apéndice con agrupamiento por nivel
      6. Estadísticas globales
    """
    if bloques is None:
        bloques = {}
    if grupos_excluyentes is None:
        grupos_excluyentes = []
    if config is None:
        config = NLGConfig()

    fecha_actual = _date.today().strftime("%d/%m/%Y")
    nombre_metrica = metrica.replace("_", " ")

    HAY_HORAS      = bloques.get("HAY_HORAS", False)
    HAY_FRANJAS    = bloques.get("HAY_FRANJAS", False)
    HAY_MESES      = bloques.get("HAY_MESES", False)
    HAY_ESTACIONES = bloques.get("HAY_ESTACIONES", False)

    # Filtrar combinaciones semánticamente inválidas
    n_antes = len(df_reglas)
    df_reglas = df_reglas[
        df_reglas["antecedente"].apply(
            lambda a: es_combinacion_valida(a, grupos_excluyentes)
        )
    ].reset_index(drop=True)
    n_filtradas = n_antes - len(df_reglas)
    if n_filtradas > 0:
        print(f"☢️  {n_filtradas} regla(s) eliminadas por combinación inválida.")

    # Ordenar por lift DESC: necesario para que agrupar_reglas sea determinista
    df_reglas = df_reglas.sort_values("lift", ascending=False).reset_index(drop=True)

    mapa_horario = _mapa_horario(df_reglas)

    lineas = []

    # ── 0. Cabecera de metadatos ─────────────────────────────────────────────
    lineas.append("---")
    lineas.append("**Fuzhify**: Informe de análisis difuso")
    lineas.append("")
    lineas.append("| | |")
    lineas.append("|---|---|")
    lineas.append(f"| **Dataset** | {dataset} |")
    lineas.append(f"| **Métrica** | {metrica} |")
    lineas.append(f"| **Fecha** | {fecha_actual} |")
    lineas.append(f"| **min_soporte** | {config.min_soporte} |")
    lineas.append(f"| **min_confianza** | {config.min_confianza} |")
    lineas.append(f"| **lift_minimo** | {config.lift_minimo} |")
    lineas.append(f"| **max_prof** | {config.max_prof} |")
    lineas.append(f"| **k_beam** | {config.k_beam} |")
    lineas.append(f"| **top_por_consecuente** | {config.top_por_consecuente} |")
    lineas.append(f"| **pais** | {config.pais} |")
    lineas.append(f"| **subdiv** | {config.subdiv or 'nacional'} |")
    lineas.append(f"| **min_reglas_grupo** | {config.min_reglas_grupo} |")
    lineas.append("")
    lineas.append("---")
    lineas.append("")

    # ── 1. Cabecera ─────────────────────────────────────────────────────────
    lineas.append(f"# Resumen de comportamiento: {dataset}")
    lineas.append("")
    lineas.append(f"**Métrica analizada:** {nombre_metrica.capitalize()}  ")
    lineas.append(f"**Total de reglas analizadas:** {len(df_reglas)}")
    lineas.append("")

    lineas.append(_generar_glosario_breve(metrica))

    # ── 2. Narrativa coloquial ──────────────────────────────────────────────
    if HAY_HORAS or HAY_FRANJAS:
        lineas.append(f"## ¿Cómo se comporta **{nombre_metrica}** a lo largo del día?")
        lineas.append(f"> Esta sección resume el comportamiento de **{nombre_metrica}** "
                      f"en lenguaje sencillo, sin tecnicismos.")
        lineas.append("")
        lineas.append(_parrafo_coloquial(df_reglas, mapa_horario, nombre_metrica))
    else:
        lineas.append(f"## Patrones detectados")
        lineas.append(
            f"> Este dataset tiene granularidad **{granularidad_desc}**: "
            f"no hay patrones por franja horaria. "
            f"Los patrones detectados son {'estacionales y de calendario' if HAY_MESES or HAY_ESTACIONES else 'temporales'}."
        )
    lineas.append("")

    parrafo_cal = _parrafo_calendario(df_reglas, nombre_metrica)
    if parrafo_cal:
        lineas.append(parrafo_cal)
        lineas.append("")

    # ── 3. Análisis técnico por franja ──────────────────────────────────────
    if HAY_HORAS or HAY_FRANJAS:
        lineas.append("## Análisis por franja horaria")
        lineas.append("")
        lineas.append(
            "Detalle de los patrones detectados, organizados por momento del día. "
            "Cada punto indica el nivel de " + metrica + " más probable en ese contexto, "
            "junto con la confianza y el lift de la regla."
        )
        lineas.append("")
        texto_franjas = _detalle_por_franja(df_reglas, nombre_metrica, min_reglas_grupo)
        lineas.append(texto_franjas)
        _sint_franjas = _sintetizar_con_prompt(
            f"Resume en 3-4 frases en castellano los patrones más relevantes detectados "
            f"en el análisis por franja horaria de {nombre_metrica}. Destaca los momentos "
            f"del día con comportamiento más diferenciado y si hay diferencias entre días "
            f"laborables y fin de semana. Usa lenguaje natural sin tecnicismos, no menciones "
            f"valores numéricos de confianza ni lift.\n\nDatos:\n{texto_franjas}",
            config,
        )
        if _sint_franjas:
            lineas.append(
                f"\n> **Resumen generado con IA a partir de los datos anteriores**\n"
                f">\n"
                f"> *{_sint_franjas}*"
            )

    # ── 4. Apéndice ─────────────────────────────────────────────────────────
    lineas.append("---")
    lineas.append("")
    lineas.append("## Apéndice: Análisis por nivel de " + metrica)
    lineas.append("")
    lineas.append("")
    lineas.append(_generar_glosario_tecnico())
    lineas.append("")
    lineas.append(
        f"*Mismas reglas organizadas por nivel de **{metrica}** (de mayor a menor valor).*"
    )
    lineas.append("")

    ORDEN_CONSECUENTE = [
        "v_OutlierAlto", "v_MuyAlta", "v_Alta",
        "v_Media",
        "v_Baja", "v_MuyBaja", "v_OutlierBajo",
    ]
    consecuentes_en_datos = df_reglas["consecuente"].unique()
    consecuentes_ordenados = [c for c in ORDEN_CONSECUENTE if c in consecuentes_en_datos]
    for c in consecuentes_en_datos:
        if c not in consecuentes_ordenados:
            consecuentes_ordenados.append(c)

    _lineas_niv = []
    for consecuente in consecuentes_ordenados:
        df_c = df_reglas[df_reglas["consecuente"] == consecuente].copy()
        if df_c.empty:
            continue

        desc_v = ETIQUETA_METRICA.get(consecuente, consecuente)
        emoji  = NIVEL_EMOJI.get(consecuente, "")
        # FIX: umbral de solapamiento 0.4 para recuperar agrupamiento
        # tras el sort por lift. El sort es necesario para que el párrafo
        # narrativo use la regla más fuerte como ancla del grupo.
        grupos   = agrupar_reglas(df_c, umbral_solapamiento=0.4)
        n_grupos = len(grupos)

        _lineas_niv.append(f"### {nombre_metrica.capitalize()} {desc_v}")
        _lineas_niv.append(
            f"*{len(df_c)} {'regla' if len(df_c)==1 else 'reglas'}, "
            f"agrupadas en {n_grupos} {'contexto' if n_grupos==1 else 'contextos'}* | "
            f"confianza media: {df_c['confianza'].mean()*100:.0f} %, "
            f"lift medio: {df_c['lift'].mean():.1f}"
        )
        _lineas_niv.append("")

        for grupo in grupos:
            parrafo = grupo_a_parrafo(grupo, nombre_metrica, consecuente, min_reglas_grupo)
            _lineas_niv.append(parrafo)
            _lineas_niv.append("")

    texto_apendice_niveles = "\n".join(_lineas_niv)
    lineas.append(texto_apendice_niveles)
    _sint_ap = _sintetizar_con_prompt(
        f"Resume en 3-4 frases en castellano los niveles de {nombre_metrica} "
        f"más frecuentes y en qué contextos temporales aparecen. Destaca el nivel "
        f"dominante y los patrones más llamativos. Usa lenguaje natural sin "
        f"tecnicismos.\n\nDatos:\n{texto_apendice_niveles}",
        config,
    )
    if _sint_ap:
        lineas.append(
            f"\n> **Resumen generado con IA a partir de los datos anteriores**\n"
            f">\n"
            f"> *{_sint_ap}*"
        )

    # ── 5. Estadísticas globales ─────────────────────────────────────────────
    lineas.append("---")
    lineas.append("")
    lineas.append("## Estadísticas globales del análisis")
    lineas.append("")
    lineas.append("| Métrica | Valor |")
    lineas.append("|---|---|")
    lineas.append(f"| Reglas totales | {len(df_reglas)} |")
    lineas.append(f"| Consecuentes únicos | {len(consecuentes_ordenados)} |")
    lineas.append(f"| Soporte medio | {df_reglas['soporte'].mean():.4f} |")
    lineas.append(f"| Confianza media | {df_reglas['confianza'].mean()*100:.1f} % |")
    lineas.append(f"| Lift medio | {df_reglas['lift'].mean():.2f} |")
    lineas.append(f"| Lift máximo | {df_reglas['lift'].max():.2f} |")

    return "\n".join(lineas)


# ---------------------------------------------------------------------------
# generar_informe: función pública del módulo
# ---------------------------------------------------------------------------

def _auto_detectar_metrica(df_fuzzy, var_tiempo):
    """Detecta la columna de métrica: primera columna no-temporal, no-fuzzy, no-segundos."""
    excluir = {"segundos", var_tiempo}
    for col in df_fuzzy.columns:
        if col in excluir:
            continue
        if col.startswith("t_") or col.startswith("v_"):
            continue
        return col
    return ""


def generar_informe(df_reglas: pd.DataFrame,
                    df_fuzzy: pd.DataFrame,
                    config: NLGConfig = None) -> str:
    """
    Pipeline completo NLG: reglas + fuzzy → informe Markdown.

    Entrada:
      df_reglas: CSV de reglas (salida de src02).
      df_fuzzy:  CSV fuzzificado (salida de src01).
      config:    NLGConfig con nombre_dataset, metrica, etc.

    Salida:
      String Markdown con el informe completo.
    """
    if config is None:
        config = NLGConfig()

    # Auto-detectar var_tiempo si no se indica
    var_tiempo = config.var_tiempo or detectar_var_tiempo(df_fuzzy)

    # Auto-detectar metrica si no se indica
    metrica = config.metrica or _auto_detectar_metrica(df_fuzzy, var_tiempo)

    # Detectar bloques temporales y granularidad
    bloques = detectar_bloques(df_fuzzy)
    _, granularidad_desc = detectar_granularidad(df_fuzzy, var_tiempo)

    # Construir grupos excluyentes desde los tokens presentes en las reglas
    _cols_reglas = set(
        tok
        for ant in df_reglas["antecedente"]
        for tok in ant.split(" AND ")
    )
    grupos_excluyentes = _construir_grupos_src03(_cols_reglas)

    dataset = config.nombre_dataset or metrica

    return generar_resumen(
        df_reglas,
        dataset           = dataset,
        metrica           = metrica,
        min_reglas_grupo  = config.min_reglas_grupo,
        bloques           = bloques,
        granularidad_desc = granularidad_desc,
        grupos_excluyentes = grupos_excluyentes,
        config            = config,
    )
