from __future__ import annotations

from pathlib import Path

import pandas as pd
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
TABLE_DIR = ROOT / "outputs" / "tables"
SQL_DIR = ROOT / "outputs" / "sql"
ASSET_DIR = ROOT / "assets"


COLORS = {
    "bg": "#f4f7fb",
    "panel": "#ffffff",
    "ink": "#102033",
    "muted": "#667085",
    "border": "#d9e2ef",
    "blue": "#2563eb",
    "teal": "#0f766e",
    "purple": "#7c3aed",
    "orange": "#c2410c",
    "red": "#dc2626",
    "green": "#15803d",
    "navy": "#111827",
    "light_blue": "#dbeafe",
    "light_teal": "#ccfbf1",
    "light_purple": "#ede9fe",
    "light_orange": "#ffedd5",
    "light_green": "#dcfce7",
}


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size=size)
    return ImageFont.load_default()


FONTS = {
    "title": font(34, True),
    "subtitle": font(16),
    "h2": font(22, True),
    "h3": font(16, True),
    "body": font(14),
    "small": font(12),
    "tiny": font(10),
    "metric": font(28, True),
}


def money(value: float) -> str:
    if abs(value) >= 1_000_000:
        return f"${value / 1_000_000:.1f}M"
    if abs(value) >= 1_000:
        return f"${value / 1_000:.1f}K"
    return f"${value:,.0f}"


def number(value: float) -> str:
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if value >= 1_000:
        return f"{value / 1_000:.1f}K"
    return f"{value:,.0f}"


def pct(value: float) -> str:
    return f"{value:.1f}%"


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))


def blend(color: str, alpha: float, background: str = "#ffffff") -> tuple[int, int, int]:
    fg = hex_to_rgb(color)
    bg = hex_to_rgb(background)
    return tuple(int(bg[i] * (1 - alpha) + fg[i] * alpha) for i in range(3))


def canvas(title: str, subtitle: str, size: tuple[int, int] = (1600, 950)) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGB", size, COLORS["bg"])
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle((28, 26, size[0] - 28, 120), radius=22, fill=COLORS["navy"])
    draw.text((60, 48), title, fill="#ffffff", font=FONTS["title"])
    draw.text((62, 91), subtitle, fill="#cbd5e1", font=FONTS["subtitle"])
    return img, draw


def panel(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], title: str | None = None) -> None:
    draw.rounded_rectangle(box, radius=18, fill=COLORS["panel"], outline=COLORS["border"], width=1)
    if title:
        draw.text((box[0] + 22, box[1] + 18), title, fill=COLORS["ink"], font=FONTS["h2"])


def arrow(draw: ImageDraw.ImageDraw, start: tuple[int, int], end: tuple[int, int], color: str = "#64748b") -> None:
    draw.line((*start, *end), fill=color, width=4)
    x1, y1 = end
    draw.polygon([(x1, y1), (x1 - 14, y1 - 8), (x1 - 14, y1 + 8)], fill=color)


def wrapped(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, max_width: int, fill: str, fnt: ImageFont.ImageFont, line_gap: int = 5) -> int:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if draw.textlength(candidate, font=fnt) <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    x, y = xy
    _, text_top, _, text_bottom = draw.textbbox((x, y), "Ag", font=fnt)
    line_h = text_bottom - text_top
    for idx, line in enumerate(lines):
        draw.text((x, y + idx * (line_h + line_gap)), line, fill=fill, font=fnt)
    return y + len(lines) * (line_h + line_gap)


def row_count(path: Path) -> int:
    return max(sum(1 for _ in path.open("r", encoding="utf-8")) - 1, 0)


def load_tables() -> dict[str, pd.DataFrame]:
    return {
        "kpis": pd.read_csv(TABLE_DIR / "executive_kpis.csv"),
        "quality": pd.read_csv(TABLE_DIR / "data_quality_report.csv"),
        "monthly": pd.read_csv(TABLE_DIR / "monthly_revenue.csv"),
        "category": pd.read_csv(TABLE_DIR / "category_performance.csv"),
        "rfm": pd.read_csv(TABLE_DIR / "rfm_segment_summary.csv"),
        "retention": pd.read_csv(TABLE_DIR / "cohort_retention.csv"),
        "discount": pd.read_csv(TABLE_DIR / "discount_analysis.csv"),
        "products": pd.read_csv(TABLE_DIR / "product_performance.csv"),
        "geo": pd.read_csv(TABLE_DIR / "geographic_performance.csv"),
    }


def stage_card(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    label: str,
    title: str,
    lines: list[str],
    fill: str,
    accent: str,
) -> None:
    x0, y0, x1, y1 = box
    draw.rounded_rectangle(box, radius=18, fill=fill, outline=COLORS["border"], width=1)
    draw.ellipse((x0 + 18, y0 + 18, x0 + 54, y0 + 54), fill=accent)
    draw.text((x0 + 30, y0 + 25), label, fill="#ffffff", font=FONTS["h3"])
    draw.text((x0 + 70, y0 + 20), title, fill=COLORS["ink"], font=FONTS["h3"])
    y = y0 + 68
    for line in lines:
        draw.text((x0 + 24, y), line, fill=COLORS["muted"], font=FONTS["small"])
        y += 23


def workflow_screenshot() -> None:
    img, draw = canvas(
        "End-to-End Analytics Workflow",
        "From synthetic source data to SQL, Python analytics, and Power BI-ready reporting",
    )
    counts = {
        "customers": row_count(PROCESSED_DIR / "customers.csv"),
        "orders": row_count(PROCESSED_DIR / "orders.csv"),
        "items": row_count(PROCESSED_DIR / "order_items.csv"),
        "products": row_count(PROCESSED_DIR / "products.csv"),
    }
    stages = [
        ("1", "Generate Data", [f"{number(counts['customers'])} customers", f"{number(counts['orders'])} orders", f"{number(counts['items'])} order items"], COLORS["light_blue"], COLORS["blue"]),
        ("2", "Clean Data", ["dedupe rows", "standardize formats", "validate keys"], COLORS["light_teal"], COLORS["teal"]),
        ("3", "SQL Database", ["normalized schema", "PK/FK relationships", "views and indexes"], COLORS["light_purple"], COLORS["purple"]),
        ("4", "SQL Analysis", ["CTEs and joins", "window functions", "ranking and growth"], COLORS["light_orange"], COLORS["orange"]),
        ("5", "Python Analytics", ["EDA", "RFM segmentation", "cohort retention"], COLORS["light_green"], COLORS["green"]),
        ("6", "Power BI", ["import tables", "DAX measures", "dashboard pages"], "#fee2e2", COLORS["red"]),
    ]
    x_positions = [50, 310, 570, 830, 1090, 1350]
    for idx, stage in enumerate(stages):
        x = x_positions[idx]
        stage_card(draw, (x, 180, x + 210, 340), *stage)
        if idx < len(stages) - 1:
            arrow(draw, (x + 214, 260), (x + 254, 260))

    panel(draw, (50, 410, 760, 840), "Generated Project Artifacts")
    artifacts = [
        ("Data", "raw and processed CSV tables"),
        ("Database", "SQLite database plus PostgreSQL scripts"),
        ("SQL", "10 exported query result tables"),
        ("Python", "notebook, RFM, cohort, forecast, and insights"),
        ("Power BI", "import model, DAX, theme, and dashboard guide"),
    ]
    y = 470
    for label, text in artifacts:
        draw.rounded_rectangle((82, y, 176, y + 34), radius=8, fill="#eff6ff")
        draw.text((102, y + 8), label, fill=COLORS["blue"], font=FONTS["h3"])
        draw.text((200, y + 8), text, fill=COLORS["ink"], font=FONTS["body"])
        y += 62

    panel(draw, (820, 410, 1550, 840), "Scale and Validation")
    metrics = [
        ("Customers", number(counts["customers"]), COLORS["blue"]),
        ("Orders", number(counts["orders"]), COLORS["teal"]),
        ("Order Items", number(counts["items"]), COLORS["purple"]),
        ("Products", number(counts["products"]), COLORS["orange"]),
    ]
    for idx, (label, value, color) in enumerate(metrics):
        x = 850 + (idx % 2) * 330
        y = 480 + (idx // 2) * 130
        draw.rounded_rectangle((x, y, x + 285, y + 88), radius=14, fill="#ffffff", outline=COLORS["border"])
        draw.rounded_rectangle((x + 16, y + 18, x + 24, y + 70), radius=4, fill=color)
        draw.text((x + 42, y + 17), label, fill=COLORS["muted"], font=FONTS["body"])
        draw.text((x + 42, y + 42), value, fill=COLORS["ink"], font=FONTS["metric"])
    draw.text((850, 750), "Integrity checks: SQLite integrity_check = ok, foreign_key_check = no issues", fill=COLORS["green"], font=FONTS["h3"])
    img.save(ASSET_DIR / "process_workflow.png", optimize=True, quality=95)


def table_box(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], name: str, fields: list[str], color: str) -> None:
    x0, y0, x1, y1 = box
    draw.rounded_rectangle(box, radius=16, fill="#ffffff", outline=COLORS["border"], width=1)
    draw.rounded_rectangle((x0, y0, x1, y0 + 44), radius=16, fill=color)
    draw.rectangle((x0, y0 + 28, x1, y0 + 44), fill=color)
    draw.text((x0 + 18, y0 + 12), name, fill="#ffffff", font=FONTS["h3"])
    y = y0 + 58
    for field in fields:
        field_color = COLORS["ink"] if field.startswith("PK") or field.startswith("FK") else COLORS["muted"]
        draw.text((x0 + 18, y), field, fill=field_color, font=FONTS["small"])
        y += 22


def data_model_screenshot() -> None:
    img, draw = canvas(
        "Normalized Data Model",
        "Primary keys, foreign keys, and fact/dimension structure used for SQL and Power BI",
        (1600, 1000),
    )
    boxes = {
        "customers": (70, 190, 410, 430),
        "orders": (630, 190, 970, 470),
        "items": (630, 610, 970, 870),
        "products": (1190, 610, 1530, 870),
        "returns": (1190, 190, 1530, 380),
    }
    table_box(draw, boxes["customers"], "customers", ["PK customer_id", "customer_name", "gender, age", "city, state, country", "signup_date"], COLORS["blue"])
    table_box(draw, boxes["orders"], "orders", ["PK order_id", "FK customer_id", "order_date, shipment_date", "payment_method", "order_status", "total_amount"], COLORS["teal"])
    table_box(draw, boxes["items"], "order_items", ["PK order_item_id", "FK order_id", "FK product_id", "quantity", "price_per_unit", "discount"], COLORS["purple"])
    table_box(draw, boxes["products"], "products", ["PK product_id", "product_name", "category", "sub_category", "brand", "cost_price, selling_price"], COLORS["orange"])
    table_box(draw, boxes["returns"], "returns", ["PK return_id", "FK order_id", "return_reason", "return_date"], COLORS["red"])

    arrow(draw, (410, 310), (630, 310), COLORS["muted"])
    draw.text((488, 286), "1 to many", fill=COLORS["muted"], font=FONTS["small"])
    arrow(draw, (800, 470), (800, 610), COLORS["muted"])
    draw.text((818, 530), "1 to many", fill=COLORS["muted"], font=FONTS["small"])
    arrow(draw, (970, 740), (1190, 740), COLORS["muted"])
    draw.text((1045, 716), "many to 1", fill=COLORS["muted"], font=FONTS["small"])
    arrow(draw, (970, 310), (1190, 285), COLORS["muted"])
    draw.text((1040, 260), "1 to many", fill=COLORS["muted"], font=FONTS["small"])

    panel(draw, (70, 520, 410, 870), "Model Notes")
    notes = [
        "Orders is the transaction header fact table.",
        "Order_items stores product-level line facts.",
        "Products and customers behave as dimensions.",
        "Returns is optional and links to returned orders.",
        "Power BI can also use fact_sales_lines as a denormalized visual table.",
    ]
    y = 585
    for note in notes:
        y = wrapped(draw, (92, y), "- " + note, 278, COLORS["muted"], FONTS["body"], 4) + 10
    img.save(ASSET_DIR / "process_data_model.png", optimize=True, quality=95)


def mini_table(draw: ImageDraw.ImageDraw, x: int, y: int, rows: list[tuple[str, str]], width: int = 440) -> None:
    row_h = 34
    for idx, (left, right) in enumerate(rows):
        yy = y + idx * row_h
        fill = "#f8fafc" if idx % 2 == 0 else "#ffffff"
        draw.rectangle((x, yy, x + width, yy + row_h), fill=fill)
        draw.text((x + 12, yy + 8), left, fill=COLORS["ink"], font=FONTS["small"])
        draw.text((x + width - 130, yy + 8), right, fill=COLORS["muted"], font=FONTS["small"])


def sql_process_screenshot(tables: dict[str, pd.DataFrame]) -> None:
    img, draw = canvas(
        "SQL Analysis Process",
        "Advanced SQL outputs using joins, CTEs, window functions, ranking, aggregates, and date functions",
        (1600, 1000),
    )
    panel(draw, (48, 170, 520, 880), "SQL Techniques Covered")
    techniques = [
        ("Joins", "customers, orders, order_items, products, returns"),
        ("CTEs", "monthly revenue, first orders, churn history"),
        ("Window Functions", "running totals, lag growth, ranks"),
        ("Ranking", "top customers, product dense ranks"),
        ("Date Functions", "month buckets, YoY and MoM growth"),
        ("Aggregates", "AOV, CLV, revenue, margin, units"),
    ]
    y = 238
    for label, text in techniques:
        draw.rounded_rectangle((80, y, 470, y + 74), radius=12, fill="#f8fafc", outline=COLORS["border"])
        draw.text((102, y + 12), label, fill=COLORS["blue"], font=FONTS["h3"])
        wrapped(draw, (102, y + 38), text, 330, COLORS["muted"], FONTS["small"], 2)
        y += 92

    panel(draw, (560, 170, 1030, 880), "Query Output Files")
    files = sorted(SQL_DIR.glob("*.csv"))
    rows = []
    for path in files[:10]:
        rows.append((path.stem.replace("_", " "), f"{row_count(path):,} rows"))
    mini_table(draw, 592, 238, rows, 400)

    panel(draw, (1070, 170, 1550, 500), "Executive KPIs")
    k = tables["kpis"].iloc[0]
    metrics = [
        ("Revenue", money(float(k["total_revenue"]))),
        ("Orders", number(float(k["total_orders"]))),
        ("AOV", money(float(k["average_order_value"]))),
        ("Repeat Rate", pct(float(k["repeat_customer_rate_pct"]))),
        ("Return Rate", pct(float(k["return_rate_pct"]))),
    ]
    y = 240
    for label, value in metrics:
        draw.text((1100, y), label, fill=COLORS["muted"], font=FONTS["body"])
        draw.text((1390, y), value, fill=COLORS["ink"], font=FONTS["h3"])
        y += 44

    panel(draw, (1070, 530, 1550, 880), "Top SQL Business Outputs")
    monthly = tables["monthly"].sort_values("revenue", ascending=False).head(3)
    category = (
        tables["category"]
        .groupby("category", as_index=False)["gross_profit"]
        .sum()
        .sort_values("gross_profit", ascending=False)
        .head(3)
    )
    rows = []
    for row in monthly.itertuples(index=False):
        rows.append((f"Peak month {str(row.order_month)[:7]}", money(float(row.revenue))))
    for row in category.itertuples(index=False):
        rows.append((f"Profit category {row.category}", money(float(row.gross_profit))))
    mini_table(draw, 1100, 598, rows, 400)
    img.save(ASSET_DIR / "process_sql_analysis.png", optimize=True, quality=95)


def draw_bar_chart(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    data: pd.DataFrame,
    label_col: str,
    value_col: str,
    color: str,
) -> None:
    x0, y0, x1, y1 = box
    left = x0 + 180
    top = y0 + 62
    max_v = max(float(data[value_col].max()), 1)
    gap = 10
    bar_h = (y1 - top - 28 - gap * (len(data) - 1)) / len(data)
    for idx, row in data.reset_index(drop=True).iterrows():
        y = top + idx * (bar_h + gap)
        label = str(row[label_col])
        if len(label) > 19:
            label = label[:16] + "..."
        value = float(row[value_col])
        w = (x1 - left - 70) * value / max_v
        draw.text((x0 + 26, y + 6), label, fill=COLORS["ink"], font=FONTS["small"])
        draw.rounded_rectangle((left, y, left + w, y + bar_h), radius=5, fill=color)
        draw.text((left + w + 8, y + 6), money(value), fill=COLORS["muted"], font=FONTS["small"])


def draw_heatmap(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], retention: pd.DataFrame) -> None:
    x0, y0, x1, y1 = box
    data = retention.head(9).copy()
    month_cols = [c for c in data.columns if c != "cohort_month"][:10]
    left = x0 + 88
    top = y0 + 66
    cell_w = (x1 - left - 24) / len(month_cols)
    cell_h = (y1 - top - 26) / len(data)
    for j, col in enumerate(month_cols):
        draw.text((left + j * cell_w + 7, top - 22), f"M{col}", fill=COLORS["muted"], font=FONTS["tiny"])
    for i, row in data.reset_index(drop=True).iterrows():
        draw.text((x0 + 24, top + i * cell_h + 7), str(row["cohort_month"])[:7], fill=COLORS["muted"], font=FONTS["tiny"])
        for j, col in enumerate(month_cols):
            value = row[col]
            intensity = 0 if pd.isna(value) else min(float(value) / 100, 1)
            fill = blend(COLORS["teal"], 0.08 + intensity * 0.80)
            x = left + j * cell_w
            y = top + i * cell_h
            draw.rounded_rectangle((x, y, x + cell_w - 5, y + cell_h - 5), radius=4, fill=fill)
            if not pd.isna(value):
                draw.text((x + 7, y + 6), f"{float(value):.0f}", fill=COLORS["ink"], font=FONTS["tiny"])


def python_process_screenshot(tables: dict[str, pd.DataFrame]) -> None:
    img, draw = canvas(
        "Python Analytics Process",
        "Pandas cleaning validation, exploratory analysis, RFM segmentation, cohorts, forecasting, and insights",
        (1600, 1000),
    )
    panel(draw, (50, 170, 510, 480), "Data Cleaning Summary")
    quality = tables["quality"]
    rows = []
    for row in quality.itertuples(index=False):
        rows.append((str(row.table_name), f"{int(row.processed_rows):,} clean rows"))
    mini_table(draw, 82, 238, rows, 380)

    panel(draw, (545, 170, 1055, 480), "RFM Segment Revenue")
    draw_bar_chart(
        draw,
        (545, 170, 1055, 480),
        tables["rfm"].sort_values("revenue", ascending=False),
        "customer_segment",
        "revenue",
        COLORS["purple"],
    )

    panel(draw, (1090, 170, 1550, 480), "Retention Cohorts")
    draw_heatmap(draw, (1090, 170, 1550, 480), tables["retention"])

    panel(draw, (50, 525, 510, 880), "Advanced Python Outputs")
    outputs = [
        ("RFM segmentation", "48K+ customer-level scores"),
        ("Cohort analysis", "monthly retention matrix"),
        ("Churn indicators", "recency-driven risk labels"),
        ("Market basket", "top co-purchased products"),
        ("Forecasting", "6-month seasonal revenue forecast"),
        ("Power BI exports", "curated import-ready CSVs"),
    ]
    y = 590
    for label, text in outputs:
        draw.text((82, y), label, fill=COLORS["blue"], font=FONTS["h3"])
        draw.text((255, y), text, fill=COLORS["muted"], font=FONTS["small"])
        y += 44

    panel(draw, (545, 525, 1055, 880), "Discount Impact")
    discount = tables["discount"].copy()
    draw_bar_chart(draw, (545, 525, 1055, 880), discount, "discount_bucket", "gross_profit", COLORS["orange"])

    panel(draw, (1090, 525, 1550, 880), "Regional Analytics")
    geo = tables["geo"].head(8)
    rows = [(f"{row.city}, {row.state}", money(float(row.revenue))) for row in geo.itertuples(index=False)]
    mini_table(draw, 1120, 595, rows, 390)
    img.save(ASSET_DIR / "process_python_analytics.png", optimize=True, quality=95)


def main() -> None:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    tables = load_tables()
    workflow_screenshot()
    data_model_screenshot()
    sql_process_screenshot(tables)
    python_process_screenshot(tables)
    for name in [
        "process_workflow.png",
        "process_data_model.png",
        "process_sql_analysis.png",
        "process_python_analytics.png",
    ]:
        print(f"Created {ASSET_DIR / name}")


if __name__ == "__main__":
    main()
