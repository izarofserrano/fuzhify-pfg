"""
Generación de gráficos PNG para el informe PDF.
Cada función escribe un PNG en el directorio temporal del sistema y devuelve su ruta.
Paleta YlOrRd, coherente con src02.
"""
import tempfile
import uuid
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # backend sin pantalla, obligatorio en servidor
import matplotlib.pyplot as plt
import pandas as pd

CMAP = "YlOrRd"


def _ruta_tmp(sufijo: str) -> str:
    d = tempfile.gettempdir()
    return str(Path(d) / f"fuzhify_{uuid.uuid4().hex[:8]}_{sufijo}.png")


def plot_soporte_confianza_lift(df_reglas: pd.DataFrame) -> str:
    """Scatter soporte vs confianza coloreado por lift. Devuelve ruta al PNG."""
    fig, ax = plt.subplots(figsize=(7, 4))
    sc = ax.scatter(
        df_reglas["soporte"],
        df_reglas["confianza"],
        c=df_reglas["lift"],
        cmap=CMAP,
        alpha=0.75,
        edgecolors="none",
        s=45,
    )
    plt.colorbar(sc, ax=ax, label="lift")
    ax.set_xlabel("Soporte")
    ax.set_ylabel("Confianza")
    ax.set_title("Soporte, Confianza y Lift de las reglas")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    ruta = _ruta_tmp("scatter")
    fig.savefig(ruta, dpi=120, bbox_inches="tight")
    plt.close(fig)
    return ruta


def plot_top15_reglas(df_reglas: pd.DataFrame) -> str:
    """Barras horizontales de las top 15 reglas ordenadas por lift. Devuelve ruta al PNG."""
    df_top = df_reglas.nlargest(min(15, len(df_reglas)), "lift").copy()
    df_top["etiqueta"] = (
        df_top["antecedente"].str[:35] + " → " + df_top["consecuente"].str[:20]
    )

    lift_min = df_top["lift"].min()
    lift_max = df_top["lift"].max()
    norm = plt.Normalize(lift_min, lift_max if lift_max > lift_min else lift_min + 1)
    cmap = plt.get_cmap(CMAP)
    colores = [cmap(norm(v)) for v in df_top["lift"].values]

    fig, ax = plt.subplots(figsize=(8, max(3, len(df_top) * 0.38)))
    ax.barh(range(len(df_top)), df_top["lift"].values, color=colores)
    ax.set_yticks(range(len(df_top)))
    ax.set_yticklabels(df_top["etiqueta"].values, fontsize=8)
    ax.set_xlabel("Lift")
    ax.set_title(f"Top {len(df_top)} reglas por lift")
    ax.grid(True, alpha=0.3, axis="x")
    fig.tight_layout()
    ruta = _ruta_tmp("top15")
    fig.savefig(ruta, dpi=120, bbox_inches="tight")
    plt.close(fig)
    return ruta


def plot_fuzzificacion_metrica(df_fuzzy: pd.DataFrame) -> str:
    """
    Proporción de activación (> 0) de cada variable difusa de la métrica (v_*).
    Devuelve ruta al PNG.
    """
    cols_v = [c for c in df_fuzzy.columns if c.startswith("v_")]

    fig, ax = plt.subplots(figsize=(7, 4))
    if not cols_v:
        ax.text(
            0.5, 0.5, "Sin variables difusas de métrica",
            ha="center", va="center", transform=ax.transAxes,
            fontsize=11, color="#888",
        )
        ax.axis("off")
    else:
        proporciones = (df_fuzzy[cols_v] > 0).mean().sort_values(ascending=False)
        p_min, p_max = proporciones.min(), proporciones.max()
        norm = plt.Normalize(p_min, p_max if p_max > p_min else p_min + 0.01)
        cmap = plt.get_cmap(CMAP)
        colores = [cmap(norm(v)) for v in proporciones.values]
        ax.bar(range(len(proporciones)), proporciones.values, color=colores)
        ax.set_xticks(range(len(proporciones)))
        ax.set_xticklabels(
            [c.replace("v_", "") for c in proporciones.index],
            rotation=30, ha="right", fontsize=9,
        )
        ax.set_ylabel("Proporción de activación")
        ax.set_title("Activación de variables difusas de la métrica")
        ax.grid(True, alpha=0.3, axis="y")
        fig.tight_layout()

    ruta = _ruta_tmp("fuzzy")
    fig.savefig(ruta, dpi=120, bbox_inches="tight")
    plt.close(fig)
    return ruta
