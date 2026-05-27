from .templates import (
    ETIQUETA_TEMPORAL, ETIQUETA_METRICA_COLOQUIAL, ETIQUETA_METRICA_TECNICA,
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
            meses_en_regla = tokens & grupos_excluyentes[0] if grupos_excluyentes else set()
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
    if tokens & MINUTOS:    return "minuto"
    if tokens & FRANJAS:    return "franja"
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

    FIX v3: umbral de solapamiento bajado de 0.5 → 0.4 para recuperar el
    agrupamiento que se perdía al ordenar por lift antes de iterar.
    El primer registro (mayor lift) actúa como ancla del grupo; el resto
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
