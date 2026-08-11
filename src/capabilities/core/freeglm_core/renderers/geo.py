"""Render GIS files (GeoJSON, KML, SHP) via geopandas + matplotlib."""

from __future__ import annotations

import os
from typing import Any


def render(path: str, **opts: Any) -> list:
    try:
        import geopandas as gpd
    except ImportError:
        raise RuntimeError('Missing dependency — install with: pip install "freeglm[viz]"')

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from freeglm_core.renderers import fig_to_image, labeled_image

    budget = opts.get("budget", "large")
    ext = os.path.splitext(path)[1].lower()

    if ext == ".kml":
        try:
            import fiona

            fiona.drvsupport.supported_drivers["KML"] = "r"
        except ImportError:
            pass
        gdf = gpd.read_file(path, driver="KML")
    else:
        gdf = gpd.read_file(path)

    if gdf.empty:
        raise ValueError("No features found in GIS file")

    fig, ax = plt.subplots(figsize=(12, 10))

    has_numeric = any(gdf[col].dtype.kind in "iufb" for col in gdf.columns if col != "geometry")
    numeric_col = None
    if has_numeric:
        for col in gdf.columns:
            if col != "geometry" and gdf[col].dtype.kind in "iuf":
                numeric_col = col
                break

    if numeric_col:
        gdf_with = gdf[gdf[numeric_col].notna()]
        gdf_without = gdf[gdf[numeric_col].isna()]
        if not gdf_without.empty:
            gdf_without.plot(ax=ax, color="#5B9BD5", edgecolor="black", linewidth=0.5, alpha=0.4)
        if not gdf_with.empty:
            gdf_with.plot(
                ax=ax,
                column=numeric_col,
                cmap="YlOrRd",
                legend=True,
                edgecolor="black",
                linewidth=0.3,
                alpha=0.8,
                legend_kwds={"label": numeric_col, "shrink": 0.6},
            )
    else:
        geom_types = set(gdf.geometry.geom_type)
        if geom_types & {"Point", "MultiPoint"}:
            gdf.plot(ax=ax, color="#E74C3C", markersize=15, alpha=0.7, edgecolor="black", linewidth=0.3)
        elif geom_types & {"LineString", "MultiLineString"}:
            gdf.plot(ax=ax, color="#3498DB", linewidth=1.5, alpha=0.8)
        else:
            gdf.plot(ax=ax, color="#5B9BD5", edgecolor="black", linewidth=0.5, alpha=0.7)

    ax.set_title(os.path.basename(path), fontsize=14, fontweight="bold", pad=12)
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")

    info = f"{len(gdf)} features"
    cols = [c for c in gdf.columns if c != "geometry"]
    if cols:
        info += f" | columns: {', '.join(cols[:8])}"
        if len(cols) > 8:
            info += f" (+{len(cols) - 8} more)"
    ax.text(0.02, -0.06, info, transform=ax.transAxes, fontsize=8, color="gray")

    ax.grid(True, alpha=0.3)

    img = fig_to_image(fig, pad_inches=0.3)
    return labeled_image(f"[{os.path.basename(path)}] {info}", img, budget)
