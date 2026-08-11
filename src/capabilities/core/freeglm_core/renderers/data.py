"""Render tabular data (CSV, XLSX) as markdown table text + a table image."""

from __future__ import annotations

import os
from typing import Any

MAX_ROWS = 100


def render(path: str, **opts: Any) -> list:
    ext = os.path.splitext(path)[1].lower()
    if ext == ".csv":
        return _render_csv(path, **opts)
    elif ext == ".xlsx":
        return _render_xlsx(path, **opts)
    raise ValueError(f"Unsupported data format: {ext}")


def _render_csv(path: str, **opts: Any) -> list:
    try:
        import pandas as pd
    except ImportError:
        raise RuntimeError('Missing dependency — install with: pip install "freeglm[viz]"')

    df = pd.read_csv(path, nrows=MAX_ROWS + 1)
    return _dataframe_to_blocks(df, path, budget=opts.get("budget", "large"))


def _render_xlsx(path: str, **opts: Any) -> list:
    try:
        import pandas as pd
    except ImportError:
        raise RuntimeError('Missing dependency — install with: pip install "freeglm[viz]"')

    from freeglm_core.renderers import DEFAULT_MAX_PAGES, parse_pages

    xls = pd.ExcelFile(path, engine="openpyxl")
    names = xls.sheet_names
    pages = opts.get("pages")
    indices = (
        parse_pages(pages, len(names)) if pages else range(min(len(names), opts.get("max_pages", DEFAULT_MAX_PAGES)))
    )
    budget = opts.get("budget", "large")
    result = []
    for i in indices:
        df = pd.read_excel(xls, sheet_name=names[i], nrows=MAX_ROWS + 1)
        result.extend(_dataframe_to_blocks(df, f"{path} [{names[i]}]", budget=budget))
    return result


def _dataframe_to_blocks(df, title: str, budget: str = "large") -> list:
    """Return markdown table text + matplotlib table image as content blocks."""
    total_rows = len(df)
    truncated = total_rows > MAX_ROWS
    if truncated:
        df = df.head(MAX_ROWS)

    n_rows, n_cols = df.shape
    header = f"**{title}** ({n_rows}{'+' if truncated else ''} rows, {n_cols} cols)"

    if df.empty:
        return [{"type": "text", "text": f"{header}\n\n(empty)"}]

    try:
        table_md = df.to_markdown(index=False)
    except Exception:
        table_md = df.to_string(index=False, max_rows=MAX_ROWS)

    parts = [header, table_md]
    if truncated:
        parts.append(f"... (showing first {MAX_ROWS} rows)")
    text_block = {"type": "text", "text": "\n\n".join(parts)}

    # Image first, then text (consistent with PDF/page renderers).
    result: list = []
    img = _dataframe_to_image(df, title)
    if img is not None:
        from freeglm_core.renderers import image_to_content

        result.append(image_to_content(img, budget))
    result.append(text_block)

    return result


def _dataframe_to_image(df, title: str):
    """Render a DataFrame as a matplotlib table image."""
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return None

    display_df = df.head(50)
    n_rows, n_cols = display_df.shape
    col_width = max(1.5, min(3.0, 18.0 / max(n_cols, 1)))
    fig_w = min(24, col_width * n_cols + 1)
    fig_h = min(20, 0.4 * n_rows + 1.2)

    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    ax.axis("off")
    ax.set_title(title, fontsize=12, fontweight="bold", pad=10)

    col_labels = [str(c) for c in display_df.columns]
    cell_text = display_df.astype(str).values.tolist()

    table = ax.table(
        cellText=cell_text,
        colLabels=col_labels,
        loc="center",
        cellLoc="left",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(8)
    table.scale(1, 1.3)

    for (row, col), cell in table.get_celld().items():
        if row == 0:
            cell.set_facecolor("#4472C4")
            cell.set_text_props(color="white", fontweight="bold")
        elif row % 2 == 0:
            cell.set_facecolor("#D9E2F3")
        else:
            cell.set_facecolor("#FFFFFF")
        cell.set_edgecolor("#B4C7E7")

    from freeglm_core.renderers import fig_to_image

    return fig_to_image(fig, pad_inches=0.1)
