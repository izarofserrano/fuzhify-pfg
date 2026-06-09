"""Detección de variable temporal, métrica e integración con LLM fallback."""

import os
import re
import json as _json

import numpy as np
import pandas as pd

from .constants import (
    USAR_LLM_FALLBACK, PROVEEDOR_LLM, _MODELO_LLM,
    _NO_METRICA, _METRICA_POSITIVA,
)

# API key por proveedor: se lee de variables de entorno (settings del servidor).
_LLM_API_KEY = os.environ.get(
    'GEMINI_API_KEY'    if PROVEEDOR_LLM == 'gemini'    else
    'ANTHROPIC_API_KEY' if PROVEEDOR_LLM == 'anthropic' else
    'OPENAI_API_KEY'    if PROVEEDOR_LLM == 'openai'    else ''
)


# ─────────────────────────────────────────────────────────────────────────────
# CAPA DE PROVEEDOR (lo único que cambia entre proveedores)
# ─────────────────────────────────────────────────────────────────────────────
def _llamar_llm(prompt, proveedor=None, modelo=None, api_key=None):
    """
    Interfaz única de LLM. Recibe un prompt (str), devuelve texto (str)
    o None si falla. Toda la dependencia de proveedor está AQUÍ y solo aquí.

    Para añadir un proveedor nuevo: añade una rama. El resto del código
    (perfilado, parseo, degradación) no se entera de qué proveedor es.
    """
    proveedor = proveedor or PROVEEDOR_LLM
    modelo    = modelo    or _MODELO_LLM.get(proveedor)
    api_key   = api_key   or _LLM_API_KEY

    if proveedor == "ninguno" or not api_key:
        return None

    try:
        if proveedor == "anthropic":
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)
            resp = client.messages.create(
                model=modelo, max_tokens=500,
                messages=[{"role": "user", "content": prompt}],
            )
            return "".join(b.text for b in resp.content if b.type == "text")

        elif proveedor == "openai":
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            resp = client.chat.completions.create(
                model=modelo, max_tokens=500,
                messages=[{"role": "user", "content": prompt}],
            )
            return resp.choices[0].message.content

        elif proveedor == "gemini":
            import requests as _req
            url = (
                f"https://generativelanguage.googleapis.com/v1beta/models/"
                f"{modelo}:generateContent"
            )
            resp = _req.post(
                url,
                headers={"x-goog-api-key": api_key},
                json={"contents": [{"parts": [{"text": prompt}]}]},
                timeout=15,
            )
            resp.raise_for_status()
            texto = (resp.json()["candidates"][0]["content"]["parts"][0]["text"])
            # Gemini a veces envuelve la respuesta en ```json ... ```
            return texto.strip().removeprefix("```json").removesuffix("```").strip()

        else:
            print(f"  (LLM) Proveedor no soportado: {proveedor!r}")
            return None

    except ImportError as e:
        print(f"  (LLM) Paquete del proveedor no instalado: {e}")
        return None
    except Exception as e:
        print(f"  (LLM) Error en la llamada ({type(e).__name__}): {e}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# LÓGICA AGNÓSTICA AL PROVEEDOR
# ─────────────────────────────────────────────────────────────────────────────
def _perfil_columnas_para_llm(df, var_tiempo, columnas):
    """Perfil AGREGADO de columnas. NO incluye datos crudos."""
    perfil = []
    N = len(df)
    for col in columnas:
        s = df[col]
        d = {"columna": col, "dtype": str(s.dtype), "n_unicos": int(s.nunique())}
        if np.issubdtype(s.dtype, np.number):
            d.update({
                "min": float(s.min()), "max": float(s.max()),
                "media": round(float(s.mean()), 4),
                "cv": round(float(s.std() / (abs(s.mean()) + 1e-9)), 4),
                "pct_unicos": round(s.nunique() / N, 4),
            })
        perfil.append(d)
    return perfil


def _detectar_metrica_via_llm(df, var_tiempo, candidatas, config=None):
    """
    Usa _llamar_llm (agnóstico al proveedor) para clasificar columnas.
    Devuelve lista de nombres de columna, o None si falla / no disponible.
    Degrada con elegancia: cualquier problema → None.
    """
    usar_llm = config.usar_llm_fallback if config is not None else USAR_LLM_FALLBACK
    if not usar_llm:
        return None

    perfil = _perfil_columnas_para_llm(df, var_tiempo, candidatas)
    prompt = (
        "Eres un asistente que clasifica columnas de un dataset temporal.\n"
        "Dada esta lista de columnas candidatas con sus estadísticos agregados "
        "(NO se incluyen datos crudos), identifica cuáles representan MÉTRICAS "
        "cuantitativas analizables (magnitudes que varían en el tiempo y tiene "
        "sentido resumir: intensidad, ocupación, consumo, temperatura, etc.) "
        "y cuáles NO lo son (identificadores, códigos, coordenadas, categorías).\n\n"
        f"Variable temporal del dataset: {var_tiempo!r}\n"
        f"Columnas candidatas:\n{_json.dumps(perfil, ensure_ascii=False, indent=2)}\n\n"
        "Responde EXCLUSIVAMENTE con un objeto JSON, sin texto adicional, "
        'con esta forma: {"metricas": ["col1", "col2"], "razonamiento": "breve"}'
    )

    api_key = (config.llm_api_key if config is not None else None) or _LLM_API_KEY
    proveedor = (config.proveedor_llm if config is not None else None) or PROVEEDOR_LLM
    texto = _llamar_llm(prompt, proveedor=proveedor, api_key=api_key)
    if texto is None:
        print("  (LLM) No disponible → se omite el fallback por LLM.")
        return None

    try:
        texto = texto.strip().replace("```json", "").replace("```", "").strip()
        data = _json.loads(texto)
        metricas = [c for c in data.get("metricas", []) if c in candidatas]
        razon = data.get("razonamiento", "")
        if metricas:
            print(f"  (LLM) Métricas detectadas: {metricas}")
            print(f"  (LLM) Razonamiento: {razon}")
            return metricas
        print("  (LLM) No identificó métricas válidas entre las candidatas.")
        return None
    except (ValueError, KeyError) as e:
        print(f"  (LLM) Respuesta no parseable ({type(e).__name__}). Fallback manual.")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# DETECCIÓN DE VARIABLE TEMPORAL
# ─────────────────────────────────────────────────────────────────────────────
def _detectar_var_tiempo(df_raw):
    _TOKENS_FECHA = {'fecha', 'date', 'day', 'dia', 'txndate', 'fec'}
    _TOKENS_HORA  = {'hora', 'time', 'hour', 'txntime', 'hh', 'hhmm'}

    def _tokenizar_col(col):
        return set(re.split(r'[_\-\s]+', col.lower())) | {col.lower()}

    cols_obj = [c for c in df_raw.columns if pd.api.types.is_string_dtype(df_raw[c])]
    cols_num = [c for c in df_raw.columns if pd.api.types.is_numeric_dtype(df_raw[c])]

    # Estrategia 1: columna datetime directa
    _candidata_solo_fecha = None
    for col in df_raw.columns:
        if not pd.api.types.is_string_dtype(df_raw[col]):
            continue
        try:
            parsed = pd.to_datetime(df_raw[col], dayfirst=True, errors='coerce')
            if parsed.isna().mean() > 0.1:     # >10% sin parsear → no es fecha
                continue

            tiene_variabilidad_hora  = parsed.dt.hour.std() > 0 or parsed.dt.minute.std() > 0
            tiene_variabilidad_fecha = parsed.dt.date.nunique() > 1

            if tiene_variabilidad_hora and tiene_variabilidad_fecha:
                print(f"  (tiempo) Columna datetime detectada: {col!r}")
                return col, df_raw
            elif tiene_variabilidad_fecha and _candidata_solo_fecha is None:
                _candidata_solo_fecha = col
        except Exception:
            pass

    # Estrategia 2: par fecha + hora separadas
    cols_fecha = [c for c in cols_obj if _tokenizar_col(c) & _TOKENS_FECHA]
    cols_hora  = [c for c in cols_obj if _tokenizar_col(c) & _TOKENS_HORA]

    if cols_fecha and cols_hora:
        col_f, col_h = cols_fecha[0], cols_hora[0]
        try:
            combinada = pd.to_datetime(
                df_raw[col_f].astype(str) + ' ' + df_raw[col_h].astype(str)
            )
            df_raw = df_raw.copy()
            df_raw['_datetime'] = combinada
            print(f"  (tiempo) Fecha+hora combinadas: {col_f!r} + {col_h!r} → '_datetime'")
            print(f"           Rango: {combinada.min()} → {combinada.max()}")
            return '_datetime', df_raw
        except Exception as e:
            print(f"  (tiempo) Combinación fallida ({e})")

    # Estrategia 3: unix timestamp numérico
    for col in cols_num:
        tokens = _tokenizar_col(col)
        if tokens & {'timestamp', 'ts', 'epoch', 'unix', 'time'}:
            try:
                parsed = pd.to_datetime(df_raw[col], unit='s', errors='coerce')
                if parsed.notna().mean() > 0.9:
                    print(f"  (tiempo) Unix timestamp detectado: {col!r}")
                    df_raw = df_raw.copy()
                    df_raw['_datetime'] = parsed
                    return '_datetime', df_raw
            except Exception:
                pass

    # Usar candidata de solo fecha si no se encontró nada mejor
    if _candidata_solo_fecha is not None:
        print(f"  (tiempo) Columna de fecha detectada (sin hora): {_candidata_solo_fecha!r}")
        return _candidata_solo_fecha, df_raw

    # Fallback: primera columna parseable como fecha
    for col in cols_obj:
        try:
            pd.to_datetime(df_raw[col])
            print(f"  (tiempo) Fallback — usando primera columna fecha: {col!r}")
            return col, df_raw
        except Exception:
            pass

    print("  No se detectó columna temporal. Especifica VAR_TIEMPO_OVERRIDE.")
    return None, df_raw


# ─────────────────────────────────────────────────────────────────────────────
# HEURÍSTICA DE DETECCIÓN DE MÉTRICA
# ─────────────────────────────────────────────────────────────────────────────
def _tokenizar(col):
    return set(re.split(r'[_\-\s]+', col.lower()))


def _detectar_var_metrica(df, var_tiempo):
    N = len(df)
    claras, ambiguas, info = [], [], {}
    for col in df.columns:
        if col == var_tiempo:
            continue
        serie = df[col]
        tokens = _tokenizar(col)
        # Intentar convertir a numérico si viene como string
        if serie.dtype == object or pd.api.types.is_string_dtype(serie):
            serie_num = pd.to_numeric(
                serie.astype(str).str.replace(',', '.', regex=False),
                errors='coerce'
            )
            # Si más del 80% se convirtió, usar la versión numérica
            if serie_num.notna().mean() > 0.8:
                serie = serie_num.dropna()
            else:
                info[col] = "texto no convertible a numérico → descartada"
                continue
        # Texto
        if serie.dtype == object:
            info[col] = f"texto → descartada"
            continue
        # Lista negra de tokens
        neg = tokens & _NO_METRICA
        if neg:
            info[col] = f"token no-métrica {neg} → descartada"
            continue
        # Estadísticos
        rango = serie.max() - serie.min()
        cv    = serie.std() / (abs(serie.mean()) + 1e-9)
        n_u   = serie.nunique()
        pct_u = n_u / N
        # Constante
        if rango < 1e-6 or cv < 0.01:
            info[col] = f"constante (cv={cv:.4f}) → descartada"
            continue
        # ID
        if pct_u > 0.95:
            info[col] = f"posible ID ({n_u} únicos) → descartada"
            continue
        # Categórica
        if n_u <= 10:
            info[col] = f"categórica ({n_u} valores) → descartada"
            continue
        # Variabilidad temporal
        try:
            tmp = df[[var_tiempo, col]].copy()
            tmp[var_tiempo] = pd.to_datetime(tmp[var_tiempo])
            tmp['_h'] = tmp[var_tiempo].dt.hour
            ratio_t = tmp.groupby('_h')[col].std().mean() / (serie.std() + 1e-9)
            if ratio_t < 0.05:
                info[col] = f"sin variabilidad temporal → descartada"
                continue
        except Exception:
            pass
        # Clasificar
        pos = tokens & _METRICA_POSITIVA
        if pos and cv > 0.1:
            claras.append(col)
            info[col] = f"✓ CLARA (token={pos}, cv={cv:.2f})"
        else:
            ambiguas.append(col)
            info[col] = f"? AMBIGUA (cv={cv:.2f}, únicos={n_u})"
    return claras, ambiguas, info
