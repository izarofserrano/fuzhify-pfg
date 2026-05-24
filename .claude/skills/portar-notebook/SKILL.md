---
name: portar-notebook
description: Use this skill when migrating a Jupyter notebook (.ipynb) into a clean, importable Python module while preserving exact behavior. Triggers include phrases like "port this notebook", "migrate notebook to module", "convert notebook to package", "extract notebook into core/", "portar notebook", "migrar notebook", or any request to move logic from a .ipynb file into a structured Python package without changing what it does. Especially useful for moving prototyping code into production-grade modules (FastAPI/Flask backends, libraries, CLI tools) while preserving numerical parity with the original notebook output.
---

# Portar notebook a módulo Python

## Filosofía: portar, no reescribir

Esta skill aplica cuando alguien quiere convertir un notebook en código modular **sin tocar la lógica de negocio**. La regla de oro:

> Si una función está fea pero funciona, se queda fea.

El objetivo NO es escribir un módulo bonito; es escribir un módulo que produzca **exactamente el mismo output** que el notebook, en forma importable, sin restos de Colab/Jupyter.

Si el usuario quiere refactorizar, eso es otra tarea posterior. Esta skill termina cuando hay paridad de salida demostrable.

## Cuándo usar esta skill

- "Migra el notebook X a un módulo en `backend/core/Y/`"
- "Necesito que esto sea importable desde FastAPI"
- "Quiero el pipeline del notebook como CLI"
- Cualquier petición que mueva código de `.ipynb` a `.py` preservando comportamiento

## Cuándo NO usar esta skill

- Si piden reescribir, refactorizar o "limpiar" el código → es otra tarea.
- Si el notebook es exploratorio (gráficos, prints, sin lógica reusable).
- Si piden añadir tests unitarios genéricos (esta skill solo añade tests de paridad).

## Flujo de trabajo

### 1. Inventario del notebook (NO escribir código aún)

Antes de tocar nada, lee el notebook completo y produce un inventario:

- **Funciones definidas**: nombre, firma, qué hace (1 línea).
- **Constantes globales**: nombre, valor, tipo. Estas son intocables.
- **Imports**: lista completa.
- **Orden de ejecución de las transformaciones**: qué celda hace qué, en qué orden.
- **Dependencias de entorno**: `drive.mount`, `os.chdir`, `userdata.get`, `@param`, `%matplotlib`, etc. Todo esto desaparece en el módulo.
- **Inputs**: qué lee (CSVs, paths).
- **Outputs**: qué escribe.

Presenta el inventario al usuario antes de continuar. Es la oportunidad para que confirme qué se porta y qué no.

### 2. Diseño del módulo (estructura mínima)

Propón una estructura de archivos con el principio "una responsabilidad por archivo, sin sobreingeniería":

```
core/<nombre_modulo>/
├── __init__.py        # exporta la función pública principal
├── constants.py       # TODAS las constantes verbatim del notebook
├── <archivo_por_responsabilidad>.py  # funciones del notebook agrupadas por tema
├── pipeline.py        # función pública que orquesta todo
└── run.py             # CLI si el usuario lo pide
```

Reglas de troceado:
- Una función del notebook → una función en el módulo. **Mismo nombre, misma firma interna.**
- Las constantes globales del notebook → `constants.py`. Mismo nombre, mismo valor.
- Configuración del usuario (los `@param` de Colab) → una `dataclass` `<Nombre>Config` con los **mismos defaults** del notebook.

### 3. Portado (las únicas modificaciones permitidas)

Copia las funciones del notebook **al pie de la letra**. Las únicas eliminaciones autorizadas:

- `from google.colab import drive`, `userdata`, etc.
- `drive.mount(...)`, `os.chdir(...)`, variables `USUARIO`, `DIRECTORIO`, `rutas`.
- Comentarios `# @param`, `# @title`, magic commands (`%matplotlib`, `!pip install`).
- Prints decorativos (`"========"`, `"Cargando..."`).
- Llamadas a `display()` y plots de visualización (a menos que el usuario los pida).

Lo que **NO se modifica**:

- Nombres de variables internas (`mu_ant`, `cobertura_acumulada`, etc.).
- Estilo de código (aunque sea inconsistente).
- Orden de operaciones.
- Defaults numéricos.
- Strings de plantillas (en NLG sobre todo: las plantillas son sagradas).

Donde el notebook lee config con `@param`, el módulo recibe esos valores como argumentos de la función `pipeline()` (o como atributos de una dataclass `Config`).

### 4. Test de paridad (obligatorio)

Crea **un solo test** que demuestre paridad numérica:

```python
def test_paridad_<modulo>():
    """
    Ejecuta pipeline() sobre el CSV de referencia y compara con la salida
    del notebook. Sin paridad, la migración no está terminada.
    """
    df_input = pd.read_csv(os.environ["PARIDAD_INPUT"])
    df_ref   = pd.read_csv(os.environ["PARIDAD_REF"])
    df_out   = pipeline(df_input, ConfigDefault())

    # Mismo conjunto de columnas
    assert set(df_out.columns) == set(df_ref.columns)

    # Mismas filas (ordena ambos por las columnas clave antes de comparar)
    cols_clave = [...]  # identificarlas
    df_out_sorted = df_out.sort_values(cols_clave).reset_index(drop=True)
    df_ref_sorted = df_ref.sort_values(cols_clave).reset_index(drop=True)

    # Comparación numérica con tolerancia
    pd.testing.assert_frame_equal(
        df_out_sorted[df_ref_sorted.columns],  # mismo orden de columnas
        df_ref_sorted,
        check_exact=False,
        atol=1e-9,
        rtol=1e-7,
    )
```

Si el módulo produce texto (Markdown, NLG), la comparación es:

```python
assert texto_modulo.strip() == texto_notebook.strip()
```

Si la paridad falla, **no se pasa a la siguiente migración**. Hay que encontrar la divergencia antes de seguir.

### 5. CLI (opcional, solo si se pide)

Si el usuario quiere ejecutar el módulo desde la terminal:

```python
# run.py
import argparse
from .pipeline import pipeline, Config

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", required=True)
    parser.add_argument("--out", required=True)
    # ... un flag por cada campo de Config
    args = parser.parse_args()

    config = Config(...)
    df = pd.read_csv(args.csv)
    out = pipeline(df, config)
    out.to_csv(args.out, index=False)

if __name__ == "__main__":
    main()
```

Uso: `python -m mi_paquete.core.modulo.run --csv in.csv --out out.csv`

## Anti-patrones (NO hacer)

- **Renombrar variables "para que se entiendan mejor".** No. El TFG/proyecto ya tiene su lenguaje. Mantenlo.
- **Añadir validación Pydantic dentro de las funciones core.** La validación va en la capa API/Pydantic, no en el core.
- **Convertir funciones en clases solo porque "es más OOP".** Si era una función en el notebook, es una función en el módulo.
- **Añadir logging estructurado donde antes había prints.** Si la persona pide quitar prints, se quitan; no se sustituyen por `logger.info()`.
- **Añadir type hints donde no los había.** Permitido añadirlos en las firmas públicas (`pipeline()`, `Config`). Prohibido cubrir el código interno con tipos que no estaban.
- **Refactorizar bucles a comprehensions o viceversa.** Se queda como está.
- **Cambiar imports.** Si el notebook hace `import numpy as np`, el módulo hace `import numpy as np`. No `from numpy import array`.

## Comunicación con el usuario

Al terminar cada notebook portado, presenta:

1. **Resumen de lo migrado:** qué funciones, qué constantes, qué archivos creados.
2. **Lista de eliminaciones realizadas:** qué se quitó (drive.mount, @param, etc.) con justificación de una línea cada uno.
3. **Estado de la paridad:** test verde / rojo, y si rojo, dónde está la divergencia.
4. **Cómo verificar:** comando exacto que el usuario tiene que ejecutar.

Ejemplo de cierre:

```
Migración completada: src01 → backend/app/core/fuzzy/

Funciones portadas: rampa_s, _heuristica, _detectar_var_tiempo,
_llamar_llm, _detectar_metrica_via_llm, generar_t_anios, generar_t_meses,
... (12 funciones en total)

Constantes portadas a constants.py: TOL_HORAS, TOLERANCIA,
N_MUESTRAS_RAMPA, defaults de GEN_*.

Eliminado:
- drive.mount (entorno Colab, no aplica en backend)
- USUARIO, rutas, os.chdir (paths hardcodeados)
- 4 bloques @param (convertidos en campos de FuzzyConfig)
- 3 prints decorativos en celda 7

Paridad: ✅ test_paridad_fuzzy.py pasa con tolerancia atol=1e-9.

Para verificar:
  cd backend
  PARIDAD_INPUT=../data/3600_intensidad.csv \
  PARIDAD_REF=../data/3600_intensidad_fuzzy_NOTEBOOK.csv \
  pytest tests/test_paridad_fuzzy.py -v
```

## Notas para defensa académica

Si el contexto es un TFG/PFG/TFM (cosa que el `CONTEXTO.md` del proyecto suele indicar), recuerda al usuario que conviene:

- Conservar el commit anterior al portado, para poder enseñar el diff "notebook → módulo" en la defensa.
- Apuntar las constantes movidas y por qué cada una tiene el valor que tiene (vendrá bien para preguntas del tribunal tipo "¿por qué TOLERANCIA=0.2?").
- El test de paridad es **el argumento principal** ante el tribunal de que la migración no introdujo regresiones. Cita el test, no la intuición.
