"""
Convierte markdown + rutas de imágenes → HTML listo para WeasyPrint.
"""
import base64
import re
from pathlib import Path

import markdown as md_lib
from jinja2 import Environment, FileSystemLoader

_TEMPLATE_DIR = Path(__file__).parent / "templates"


def _img_base64(ruta: str) -> str:
    """Lee un PNG y lo devuelve como data-URI base64."""
    data = Path(ruta).read_bytes()
    return "data:image/png;base64," + base64.b64encode(data).decode()


def _limpiar_imagenes_md(texto: str) -> str:
    """Elimina referencias a imágenes del markdown (no disponibles en el PDF)."""
    return re.sub(r"!\[.*?\]\(.*?\)", "", texto)


def _strip_front_matter(texto: str) -> str:
    """Elimina la cabecera ---...--- del inicio del markdown si la hay."""
    s = texto.lstrip()
    if not s.startswith("---"):
        return texto
    end = s.find("\n---", 3)
    if end == -1:
        return texto
    return s[end + 4:].lstrip("\n")


def _partir_secciones(texto_md: str) -> tuple[str, str]:
    """
    Separa el markdown en resumen (primeros 2 bloques) y cuerpo (el resto).
    Descarta el front-matter de metadatos (---...---) si está presente.
    Un bloque es texto separado por línea en blanco.
    """
    texto_sin_meta = _strip_front_matter(texto_md)
    bloques = [b.strip() for b in texto_sin_meta.split("\n\n") if b.strip()]
    resumen = "\n\n".join(bloques[:2])
    cuerpo = "\n\n".join(bloques[2:])
    return resumen, cuerpo


def _md_to_html(texto: str) -> str:
    conv = md_lib.Markdown(extensions=["tables", "extra"])
    return conv.convert(_limpiar_imagenes_md(texto))


def renderizar_html(
    job_data: dict,
    ruta_plot_scatter: str,
    ruta_plot_top15: str,
    ruta_plot_fuzzy: str,
    texto_md: str,
    df_top20,
) -> str:
    """Genera el HTML completo del informe, listo para pasarlo a WeasyPrint."""
    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
        autoescape=False,
    )
    tmpl = env.get_template("informe.html")

    resumen_md, cuerpo_md = _partir_secciones(texto_md)

    return tmpl.render(
        nombre_dataset=job_data["nombre_dataset"],
        metrica=job_data["metrica_seleccionada"] or "",
        fecha=job_data["creado_en"].strftime("%d/%m/%Y %H:%M"),
        parametros=job_data["parametros"],
        resumen_html=_md_to_html(resumen_md),
        cuerpo_html=_md_to_html(cuerpo_md),
        img_scatter=_img_base64(ruta_plot_scatter),
        img_top15=_img_base64(ruta_plot_top15),
        img_fuzzy=_img_base64(ruta_plot_fuzzy),
        tabla_reglas_html=df_top20.to_html(
            index=False, border=0, classes="tabla-reglas"
        ),
    )
