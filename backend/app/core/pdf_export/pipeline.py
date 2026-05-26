"""
Punto de entrada del módulo: genera el PDF completo de un job.
"""
import os
from pathlib import Path

import pandas as pd
from weasyprint import HTML

from .plots import (
    plot_fuzzificacion_metrica,
    plot_soporte_confianza_lift,
    plot_top15_reglas,
)
from .render import _TEMPLATE_DIR, renderizar_html

_COLS_TABLA = ["antecedente", "consecuente", "soporte", "confianza", "lift"]


def generar_pdf_informe(job) -> bytes:
    """
    Genera el PDF del informe a partir de un objeto Job (o duck-type equivalente).
    El job debe estar en estado 'completado' con los tres ficheros generados.
    Devuelve los bytes del PDF.
    """
    df_reglas = pd.read_csv(job.ruta_csv_reglas)
    df_fuzzy  = pd.read_csv(job.ruta_csv_fuzzy)
    texto_md  = Path(job.ruta_informe_md).read_text(encoding="utf-8")

    ruta_scatter = plot_soporte_confianza_lift(df_reglas)
    ruta_top15   = plot_top15_reglas(df_reglas)
    ruta_fuzzy   = plot_fuzzificacion_metrica(df_fuzzy)

    job_data = {
        "nombre_dataset":       job.nombre_dataset,
        "metrica_seleccionada": job.metrica_seleccionada,
        "creado_en":            job.creado_en,
        "parametros":           job.parametros,
    }

    cols_disponibles = [c for c in _COLS_TABLA if c in df_reglas.columns]
    df_top20 = df_reglas.nlargest(min(20, len(df_reglas)), "lift")[cols_disponibles].round(4)

    html_str = renderizar_html(
        job_data=job_data,
        ruta_plot_scatter=ruta_scatter,
        ruta_plot_top15=ruta_top15,
        ruta_plot_fuzzy=ruta_fuzzy,
        texto_md=texto_md,
        df_top20=df_top20,
    )

    for ruta in (ruta_scatter, ruta_top15, ruta_fuzzy):
        try:
            os.unlink(ruta)
        except OSError:
            pass

    # base_url permite que WeasyPrint resuelva href="styles.css" relativo al directorio de plantillas
    return HTML(string=html_str, base_url=str(_TEMPLATE_DIR)).write_pdf()
