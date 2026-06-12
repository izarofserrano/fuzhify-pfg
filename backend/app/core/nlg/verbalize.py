from .templates import (
    ETIQUETA_TEMPORAL, ETIQUETA_METRICA_COLOQUIAL, ETIQUETA_METRICA_TECNICA,
    ETIQUETA_METRICA, NIVEL_PESO,
    JERARQUIA, HORA_A_FRANJA,
    HORAS, FRANJAS, MESES, DIAS, ANIOS, TIPO_DIA, QUINCENAS, MINUTOS,
    FESTIVOS, ESTACIONES, MESES_POR_ESTACION,
)
from .constants import ESCALA_ADVERBIAL


# ---------------------------------------------------------------------------
# Funciones auxiliares de verbalización
# ---------------------------------------------------------------------------

def parsear_antecedente(ant_str):
    """Convierte la cadena 't_X AND t_Y' en un conjunto de tokens."""
    return set(t.strip() for t in ant_str.split(" AND "))


def es_combinacion_valida(antecedente_str, grupos_excluyentes=None):
    if grupos_excluyentes is None:
        grupos_excluyentes = []
    tokens = set(t.strip() for t in antecedente_str.split(" AND "))

    # Regla 1: dentro de cada grupo, máximo 1 valor
    for grupo in grupos_excluyentes:
        if len(tokens & grupo) > 1:
            return False

    # Regla 2: mes y estación deben ser compatibles
    for estacion, meses_validos in MESES_POR_ESTACION.items():
        if estacion in tokens:
            NOMBRES_MESES = {
                "t_Ene","t_Feb","t_Marz","t_Abr","t_May","t_Jun",
                "t_Jul","t_Ago","t_Sep","t_Oct","t_Nov","t_Dic"
            }
            grupo_meses = next(
                (g for g in grupos_excluyentes if g & NOMBRES_MESES),
                set()
            )
            meses_en_regla = tokens & grupo_meses
            if meses_en_regla - meses_validos:
                return False

    return True


def categoria_dominante(tokens):
    """
    Devuelve la categoría temporal de mayor resolución presente en el
    antecedente, usada para agrupar reglas temáticamente.
    Orden: horas > franjas > días semana > tipo_dia > meses > estaciones >
           quincenas > años
    """
    if tokens & HORAS:      return "hora"
    if tokens & FRANJAS:    return "franja"
    if tokens & MINUTOS:    return "minuto"
    if tokens & DIAS:       return "dia_semana"
    if tokens & FESTIVOS:   return "festivo"
    if tokens & TIPO_DIA:   return "tipo_dia"
    if tokens & MESES:      return "mes"
    if tokens & ESTACIONES: return "estacion"
    if tokens & QUINCENAS:  return "quincena"
    if tokens & ANIOS:      return "anio"
    return "otro"


def dimensiones_antecedente(tokens):
    """
    Devuelve un frozenset de todas las dimensiones temporales presentes.
    Ejemplo: {t_H18, t_Lun} → frozenset({"hora", "dia_semana"})
    """
    dims = set()
    if tokens & HORAS:      dims.add("hora")
    if tokens & MINUTOS:    dims.add("minuto")
    if tokens & FRANJAS:    dims.add("franja")
    if tokens & DIAS:       dims.add("dia_semana")
    if tokens & FESTIVOS:   dims.add("festivo")
    if tokens & TIPO_DIA:   dims.add("tipo_dia")
    if tokens & MESES:      dims.add("mes")
    if tokens & ESTACIONES: dims.add("estacion")
    if tokens & QUINCENAS:  dims.add("quincena")
    if tokens & ANIOS:      dims.add("anio")
    return frozenset(dims)


def franja_de_tokens(tokens):
    """
    Si el antecedente contiene horas, devuelve la franja horaria
    a la que pertenecen (si todas coinciden).
    """
    horas_presentes = tokens & HORAS
    franjas = {HORA_A_FRANJA.get(h) for h in horas_presentes} - {None}
    return franjas.pop() if len(franjas) == 1 else None


def verbalizar_token(tok):
    """Devuelve la descripción legible de un token temporal."""
    return ETIQUETA_TEMPORAL.get(tok, tok.replace("t_", ""))


def listar_en_español(items, conector="y"):
    """
    ['a','b','c'] → 'a, b y c'
    ['a','b']     → 'a y b'
    ['a']         → 'a'
    """
    items = list(items)
    if len(items) == 0: return ""
    if len(items) == 1: return items[0]
    return ", ".join(items[:-1]) + f" {conector} " + items[-1]


def horas_consecutivas(lista_tokens_hora):
    """
    Dado ["t_H03","t_H04","t_H05"] devuelve "entre las 3 h y las 5 h".
    Si no son consecutivas devuelve lista normal.
    """
    nums = sorted(int(t[3:]) for t in lista_tokens_hora)
    if not nums:
        return ""
    if nums == list(range(nums[0], nums[-1]+1)) and len(nums) > 1:
        return f"entre las {nums[0]} h y las {nums[-1]} h"
    return listar_en_español([f"las {n} h" for n in nums])


def verbalizar_antecedente(tokens):
    """
    Convierte un conjunto de tokens temporales en una frase natural.
    Ejemplos:
      {t_H03, t_H04, t_Laborable} → "entre las 3 h y las 4 h en días laborables"
      {t_Tarde, t_Lun}            → "la tarde de los lunes"
      {t_Verano}                  → "verano"
    """
    horas_tok   = sorted(tokens & HORAS)
    minutos_tok = sorted(tokens & MINUTOS)
    franjas_tok = sorted(tokens & FRANJAS)
    dias_tok    = sorted(tokens & DIAS)
    festivos_tok= sorted(tokens & FESTIVOS)
    tipo_tok    = sorted(tokens & TIPO_DIA)
    meses_tok   = sorted(tokens & MESES)
    est_tok     = sorted(tokens & ESTACIONES)
    quin_tok    = sorted(tokens & QUINCENAS)
    anio_tok    = sorted(tokens & ANIOS)

    partes = []

    if minutos_tok and horas_tok:
        partes.append(listar_en_español([verbalizar_token(m) for m in minutos_tok]))
        partes.append(horas_consecutivas(horas_tok))
    elif horas_tok:
        partes.append(horas_consecutivas(horas_tok))
    elif franjas_tok:
        partes.append(listar_en_español([verbalizar_token(f) for f in franjas_tok]))
    elif minutos_tok:
        partes.append(listar_en_español([verbalizar_token(m) for m in minutos_tok]))

    if festivos_tok:
        partes.append("días festivos")

    if tipo_tok:
        partes.append(listar_en_español([verbalizar_token(t) for t in tipo_tok]))
    if dias_tok:
        partes.append(listar_en_español([verbalizar_token(d) for d in dias_tok]))

    if meses_tok:
        partes.append(listar_en_español([verbalizar_token(m) for m in meses_tok]))

    if est_tok:
        partes.append(listar_en_español([verbalizar_token(e) for e in est_tok]))

    if quin_tok:
        partes.append(listar_en_español([verbalizar_token(q) for q in quin_tok]))

    if anio_tok:
        partes.append(listar_en_español([verbalizar_token(a) for a in anio_tok]))

    if not partes:
        return "condiciones no especificadas"

    resultado = partes[0]
    for p in partes[1:]:
        resultado += " en " + p
    return resultado


# ---------------------------------------------------------------------------
# Escala adverbial: umbrales de lift fijados por el usuario
# ---------------------------------------------------------------------------

def adverbio_por_lift(lift):
    """Traduce un valor de lift en el adverbio de fuerza estadística correspondiente."""
    for umbral, adverbio in ESCALA_ADVERBIAL:
        if lift >= umbral:
            return adverbio
    return "con cierta tendencia"


def construir_calidad(df_reglas=None):
    """
    Devuelve una función calidad(row) que traduce el lift de una regla en
    un adverbio de fuerza estadística.
    """
    def calidad(row):
        lift = row.get("lift", 0)

        if lift >= 3.0:
            return "de forma muy marcada"
        elif lift >= 2.0:
            return "de forma notable"
        elif lift >= 1.5:
            return "con cierta consistencia"
        else:
            return "con cierta tendencia"
    return calidad


# ---------------------------------------------------------------------------
# Generación de frases para una sola regla
# ---------------------------------------------------------------------------

def regla_a_frase(row, nombre_metrica, modo="tecnico"):
    """
    Convierte una fila del DataFrame de reglas en una frase en español.

    modo="tecnico":   incluye confianza y lift entre paréntesis.
    modo="coloquial": omite las cifras.
    """
    tokens  = parsear_antecedente(row["antecedente"])
    cat     = categoria_dominante(tokens)
    desc_t  = verbalizar_antecedente(tokens)

    diccionario = (ETIQUETA_METRICA_COLOQUIAL if modo == "coloquial"
                   else ETIQUETA_METRICA_TECNICA)
    desc_v  = diccionario.get(row["consecuente"], row["consecuente"])
    calidad = construir_calidad()(row)

    prefijos = {
        "hora":       "A",
        "franja":     "Durante",
        "dia_semana": "En",
        "tipo_dia":   "Durante los",
        "mes":        "En",
        "estacion":   "En",
        "quincena":   "Durante",
        "anio":       "En",
        "otro":       "En",
    }
    prefijo = prefijos.get(cat, "En")

    if modo == "tecnico":
        conf_pct = int(round(row["confianza"] * 100))
        lift_val = f"{row['lift']:.1f}"
        return (f"{prefijo} {desc_t}, la {nombre_metrica} tiende a ser {desc_v} "
                f"{calidad} (confianza {conf_pct} %, lift {lift_val}).")
    else:
        return (f"{prefijo} {desc_t}, la {nombre_metrica} tiende a ser {desc_v} "
                f"{calidad}.")


# ---------------------------------------------------------------------------
# Agrupación de reglas relacionadas en un párrafo
# ---------------------------------------------------------------------------

def agrupar_reglas(df_consecuente, umbral_solapamiento=0.4):
    """
    Agrupa reglas con el mismo consecuente y contexto similar en un párrafo.

    Umbral de solapamiento 0.4 para recuperar el
    agrupamiento que se perdía al ordenar por lift antes de iterar.
    El primer registro (mayor lift) actúa como ancla del grupo. El resto
    se adhiere si comparte al menos el 40 % de tokens (excl. años/festivos).

    Parámetro umbral_solapamiento: puede sobreescribirse por caller
    (p.ej. 0.5 si se quiere agrupamiento más estricto en tests futuros).
    """
    # El DataFrame ya viene ordenado por lift DESC desde generar_resumen
    registros = list(df_consecuente.iterrows())
    grupos = []
    asignado = [False] * len(registros)

    for i, (_, fila_i) in enumerate(registros):
        if asignado[i]:
            continue
        tokens_i = parsear_antecedente(fila_i["antecedente"])
        cat_i    = categoria_dominante(tokens_i)

        if cat_i == "hora":
            franja_i = franja_de_tokens(tokens_i)
        else:
            franja_i = None

        grupo_actual = [fila_i]
        asignado[i]  = True

        for j, (_, fila_j) in enumerate(registros):
            if asignado[j]:
                continue
            tokens_j = parsear_antecedente(fila_j["antecedente"])
            cat_j    = categoria_dominante(tokens_j)

            if cat_i != cat_j:
                continue
            if cat_i == "hora":
                franja_j = franja_de_tokens(tokens_j)
                if franja_i != franja_j:
                    continue
            if cat_i == "minuto":
                if (tokens_i & HORAS) != (tokens_j & HORAS):
                    continue
            if cat_i == "franja":
                if (tokens_i & FRANJAS) != (tokens_j & FRANJAS):
                    continue
            if cat_i == "dia_semana":
                if (tokens_i & DIAS) != (tokens_j & DIAS):
                    continue

            _excluir = ANIOS | FESTIVOS
            ti = tokens_i - _excluir if (tokens_i - _excluir) else tokens_i
            tj = tokens_j - _excluir if (tokens_j - _excluir) else tokens_j
            comun   = ti & tj
            solap_i = len(comun) / len(ti) if ti else 0
            solap_j = len(comun) / len(tj) if tj else 0
            if min(solap_i, solap_j) < umbral_solapamiento:
                continue

            grupo_actual.append(fila_j)
            asignado[j] = True

        grupos.append(grupo_actual)

    return grupos


def _detalle_por_dia(df_reglas, nombre_metrica, min_reglas_grupo=2):
    """
    Sección técnica organizada por tipo de día (laborable / fin de semana).
    Mismo formato de salida que _detalle_por_franja().
    """
    TOKENS_LABORABLE = {"t_Lun", "t_Mar", "t_Mie", "t_Jue", "t_Vie", "t_Laborable"}
    TOKENS_FDS       = {"t_Sab", "t_Dom", "t_FinSemana"}

    ORDEN = ["v_OutlierAlto", "v_MuyAlta", "v_Alta", "v_Media",
             "v_Baja", "v_MuyBaja", "v_OutlierBajo"]

    def _grupo_dia(ant_str):
        tokens = parsear_antecedente(ant_str)
        if tokens & TOKENS_LABORABLE:
            return "Días laborables"
        if tokens & TOKENS_FDS:
            return "Fin de semana"
        return "Sin día específico"

    lineas = []
    for nombre_grupo in ("Días laborables", "Fin de semana", "Sin día específico"):
        mask = df_reglas["antecedente"].apply(
            lambda a, ng=nombre_grupo: _grupo_dia(a) == ng
        )
        sub = df_reglas[mask].copy()
        if sub.empty:
            continue

        sub = sub.sort_values("lift", ascending=False)
        lineas.append(f"### {nombre_grupo}")
        lineas.append("")

        for cons in ORDEN:
            sub_c = sub[sub["consecuente"] == cons]
            if sub_c.empty:
                continue
            desc_v = ETIQUETA_METRICA.get(cons, cons)
            for _, row in sub_c.iterrows():
                tokens   = parsear_antecedente(row["antecedente"])
                desc_t   = verbalizar_antecedente(tokens)
                conf_pct = int(round(row["confianza"] * 100))
                lift_val = f"{row['lift']:.1f}"
                cal      = construir_calidad(df_reglas)(row)
                lineas.append(
                    f"- **{desc_v.capitalize()}** {cal}: "
                    f"{desc_t} (confianza {conf_pct} %, lift {lift_val})"
                )
        lineas.append("")

    return "\n".join(lineas)


def _detalle_por_estacion(df_reglas, nombre_metrica, min_reglas_grupo=2):
    """
    Sección técnica organizada por estación del año.
    Mismo formato de salida que _detalle_por_franja().
    """
    GRUPOS_ESTACION = [
        ("Primavera", {"t_Primavera", "t_Marz", "t_Abr", "t_May"}),
        ("Verano",    {"t_Verano",    "t_Jun",  "t_Jul", "t_Ago"}),
        ("Otoño",     {"t_Otonio",   "t_Sep",  "t_Oct", "t_Nov"}),
        ("Invierno",  {"t_Invierno", "t_Dic",  "t_Ene", "t_Feb"}),
    ]

    ORDEN = ["v_OutlierAlto", "v_MuyAlta", "v_Alta", "v_Media",
             "v_Baja", "v_MuyBaja", "v_OutlierBajo"]

    def _grupo_estacion(ant_str):
        tokens = parsear_antecedente(ant_str)
        for nombre, tok_set in GRUPOS_ESTACION:
            if tokens & tok_set:
                return nombre
        return "Sin estación específica"

    lineas = []
    nombres = [nombre for nombre, _ in GRUPOS_ESTACION] + ["Sin estación específica"]
    for nombre_grupo in nombres:
        mask = df_reglas["antecedente"].apply(
            lambda a, ng=nombre_grupo: _grupo_estacion(a) == ng
        )
        sub = df_reglas[mask].copy()
        if sub.empty:
            continue

        sub = sub.sort_values("lift", ascending=False)
        lineas.append(f"### {nombre_grupo}")
        lineas.append("")

        for cons in ORDEN:
            sub_c = sub[sub["consecuente"] == cons]
            if sub_c.empty:
                continue
            desc_v = ETIQUETA_METRICA.get(cons, cons)
            for _, row in sub_c.iterrows():
                tokens   = parsear_antecedente(row["antecedente"])
                desc_t   = verbalizar_antecedente(tokens)
                conf_pct = int(round(row["confianza"] * 100))
                lift_val = f"{row['lift']:.1f}"
                cal      = construir_calidad(df_reglas)(row)
                lineas.append(
                    f"- **{desc_v.capitalize()}** {cal}: "
                    f"{desc_t} (confianza {conf_pct} %, lift {lift_val})"
                )
        lineas.append("")

    return "\n".join(lineas)


def sintetizar_bloque_con_llm(
    bloque_texto: str,
    nombre_metrica: str,
    config,
) -> str | None:
    """
    Llama al LLM para generar un párrafo de síntesis de un bloque
    de reglas. Degrada con elegancia: si falla o no hay API key,
    devuelve None y el informe sale sin síntesis.
    """
    from app.core.fuzzy.heuristic import _llamar_llm

    if not config.usar_llm_sintesis:
        return None

    prompt = (
        f"Resume la siguiente información en 2-3 frases en castellano. "
        f"La información es el resultado de aplicar un algoritmo de "
        f"reglas de asociación difusa sobre datos temporales de "
        f"{nombre_metrica}. "
        f"Sé conciso, usa lenguaje natural y evita tecnicismos. "
        f"No menciones valores de confianza ni lift en el resumen.\n\n"
        f"Información:\n{bloque_texto}"
    )

    try:
        respuesta = _llamar_llm(
            prompt,
            proveedor=config.proveedor_llm,
            api_key=config.llm_api_key,
        )
        if respuesta and len(respuesta.strip()) > 20:
            lineas = respuesta.strip().splitlines()
            texto_blockquote = "\n> ".join(lineas)
            return texto_blockquote
        return None
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Párrafo coloquial para datasets sin granularidad horaria
# ---------------------------------------------------------------------------

def articulo_metrica(nombre_metrica: str) -> str:
    """Devuelve el artículo determinado para la métrica (castellano)."""
    return "la"


def _por_estaciones(df_reglas, nombre_metrica) -> str:
    """
    Genera un párrafo narrativo que describe el comportamiento de la
    métrica por estación, destacando el contraste entre las estaciones
    extremas y las de transición.
    """
    _TOKENS_ESTACION = {
        "Primavera": {"t_Primavera", "t_Marz", "t_Abr", "t_May"},
        "Verano":    {"t_Verano",    "t_Jun",  "t_Jul", "t_Ago"},
        "Otoño":     {"t_Otonio",   "t_Sep",  "t_Oct", "t_Nov"},
        "Invierno":  {"t_Invierno", "t_Dic",  "t_Ene", "t_Feb"},
    }
    _MESES_TOKENS = {
        "t_Ene","t_Feb","t_Marz","t_Abr","t_May","t_Jun",
        "t_Jul","t_Ago","t_Sep","t_Oct","t_Nov","t_Dic",
    }

    def _mes_destacado(reglas_sub):
        """Nombre del mes con mayor lift dentro de este subconjunto."""
        sub = reglas_sub[
            reglas_sub["antecedente"].apply(
                lambda ant: bool(
                    set(t.strip() for t in ant.split(" AND ")) & _MESES_TOKENS
                )
            )
        ]
        if sub.empty:
            return None
        best_ant = sub.loc[sub["lift"].idxmax(), "antecedente"]
        toks = set(t.strip() for t in best_ant.split(" AND ")) & _MESES_TOKENS
        return ETIQUETA_TEMPORAL.get(next(iter(toks)), None) if toks else None

    # 1. Calcular datos por estación (solo las que tienen reglas)
    datos = {}
    for est, tokens in _TOKENS_ESTACION.items():
        reglas_est = df_reglas[
            df_reglas["antecedente"].apply(
                lambda ant, tok=tokens: bool(
                    set(t.strip() for t in ant.split(" AND ")) & tok
                )
            )
        ]
        if reglas_est.empty:
            continue
        nivel = reglas_est.groupby("consecuente")["lift"].mean().idxmax()
        datos[est] = {
            "nivel":      nivel,
            "peso":       NIVEL_PESO.get(nivel, 4),
            "desc":       ETIQUETA_METRICA_COLOQUIAL.get(nivel, nivel),
            "mes":        _mes_destacado(reglas_est),
            "lift_media": reglas_est["lift"].mean(),
        }

    if not datos:
        return ""

    # Ordenar por peso desc; desempate por lift_media desc
    ords = sorted(datos.items(),
                  key=lambda x: (x[1]["peso"], x[1]["lift_media"]),
                  reverse=True)

    # ── Caso: una sola estación ────────────────────────────────────────────
    if len(ords) == 1:
        est, d = ords[0]
        sufijo = f", especialmente en {d['mes']}" if d["mes"] else ""
        return (f"En {est.lower()}, la {nombre_metrica} tiende a ser "
                f"**{d['desc']}**{sufijo}.")

    # ── Caso: dos estaciones ───────────────────────────────────────────────
    if len(ords) == 2:
        (e1, d1), (e2, d2) = ords
        s1 = f" (especialmente en {d1['mes']})" if d1["mes"] else ""
        s2 = f" (especialmente en {d2['mes']})" if d2["mes"] else ""
        return (f"{e1} muestra la {nombre_metrica} más **{d1['desc']}**{s1}. "
                f"{e2}, en cambio, registra valores **{d2['desc']}**{s2}.")

    # ── Caso general: 3-4 estaciones ──────────────────────────────────────
    peso_max = ords[0][1]["peso"]
    peso_min = ords[-1][1]["peso"]

    est_altas = [(e, d) for e, d in ords if d["peso"] == peso_max]
    est_bajas = [(e, d) for e, d in ords
                 if d["peso"] == peso_min and d["peso"] < peso_max]
    est_trans = [(e, d) for e, d in ords
                 if peso_min < d["peso"] < peso_max]

    frases = []

    # Frase alta
    nombres_alt = listar_en_español([e for e, _ in est_altas])
    verb   = "es" if len(est_altas) == 1 else "son"
    epocas = "la época" if len(est_altas) == 1 else "las épocas"
    desc_alt    = est_altas[0][1]["desc"]
    meses_alt   = [d["mes"] for _, d in est_altas if d["mes"]]
    suf_mes_alt = (f", especialmente en {listar_en_español(meses_alt)}"
                   if meses_alt else "")
    frases.append(
        f"{nombres_alt.capitalize()} {verb} {epocas} donde "
        f"la {nombre_metrica} tiende a ser **{desc_alt}**{suf_mes_alt}."
    )

    # Frase baja
    if est_bajas:
        nombres_baj = listar_en_español([e.lower() for e, _ in est_bajas])
        desc_baj    = est_bajas[0][1]["desc"]
        meses_baj   = [d["mes"] for _, d in est_bajas if d["mes"]]
        if meses_baj:
            lbl = "el mes" if len(meses_baj) == 1 else "los meses"
            suf_mes_baj = (f", con {listar_en_español(meses_baj)} "
                           f"como {lbl} de mayor contraste")
        else:
            suf_mes_baj = ""
        frases.append(
            f"En {nombres_baj}, en cambio, "
            f"la {nombre_metrica} tiende a ser **{desc_baj}**{suf_mes_baj}."
        )

    # Frases de transición
    for est, d in est_trans:
        if d["mes"]:
            frases.append(
                f"{est} actúa como período de transición: "
                f"la {nombre_metrica} tiende a ser **{d['desc']}**, "
                f"con {d['mes']} marcando ya un cambio notable."
            )
        else:
            frases.append(
                f"{est} actúa como período de transición, "
                f"con la {nombre_metrica} tendiendo a ser **{d['desc']}**."
            )

    return " ".join(frases)


def _por_meses(df_reglas, nombre_metrica) -> str:
    """
    Describe los meses con comportamiento más extremo
    (el más alto y el más bajo por lift).
    """
    _TOKENS_MES = {
        "enero": "t_Ene", "febrero": "t_Feb", "marzo": "t_Marz",
        "abril": "t_Abr", "mayo": "t_May", "junio": "t_Jun",
        "julio": "t_Jul", "agosto": "t_Ago", "septiembre": "t_Sep",
        "octubre": "t_Oct", "noviembre": "t_Nov", "diciembre": "t_Dic",
    }

    articulo = articulo_metrica(nombre_metrica)
    datos_mes = []

    for mes_nombre, token in _TOKENS_MES.items():
        reglas_mes = df_reglas[
            df_reglas["antecedente"].str.contains(token, regex=False)
        ]
        if reglas_mes.empty:
            continue
        lift_max = reglas_mes["lift"].max()
        nivel = reglas_mes.loc[reglas_mes["lift"].idxmax(), "consecuente"]
        datos_mes.append((mes_nombre, nivel, lift_max))

    if not datos_mes:
        return ""

    datos_mes.sort(key=lambda x: x[2], reverse=True)
    destacados = datos_mes[:3]

    frases = []
    for mes, nivel, _ in destacados:
        desc = ETIQUETA_METRICA_COLOQUIAL.get(nivel, nivel)
        frases.append(f"en {mes}, {articulo} {nombre_metrica} "
                      f"tiende a ser **{desc}**")

    parrafo = frases[0].capitalize()
    for f in frases[1:]:
        parrafo += f"; {f}"
    parrafo += "."
    return parrafo


def _parrafo_coloquial_temporal(df_reglas, nombre_metrica,
                                bloques) -> str:
    """
    Párrafo coloquial para datasets sin granularidad horaria.
    Usa el nivel temporal más informativo disponible.
    NO tocar _parrafo_coloquial() que es para franjas horarias.
    """
    if bloques.get("HAY_ESTACIONES"):
        return _por_estaciones(df_reglas, nombre_metrica)
    elif bloques.get("HAY_MESES"):
        return _por_meses(df_reglas, nombre_metrica)
    elif bloques.get("HAY_ANIOS"):
        return (f"Los patrones detectados muestran variación "
                f"interanual en {nombre_metrica}.")
    else:
        return (f"Los patrones detectados muestran variación "
                f"temporal en {nombre_metrica}.")
