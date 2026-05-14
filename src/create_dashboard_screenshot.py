from __future__ import annotations

from pathlib import Path

import pandas as pd
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
TABLE_DIR = ROOT / "outputs" / "tables"
ASSET_DIR = ROOT / "assets"
SCREENSHOT_PATH = ASSET_DIR / "powerbi_dashboard_screenshot.png"


COLORS = {
    "bg": "#f4f7fb",
    "panel": "#ffffff",
    "border": "#d9e2ef",
    "ink": "#102033",
    "muted": "#667085",
    "blue": "#2563eb",
    "teal": "#0f766e",
    "red": "#dc2626",
    "purple": "#7c3aed",
    "orange": "#c2410c",
    "green": "#15803d",
    "slate": "#334155",
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
    "h2": font(18, True),
    "card_label": font(14),
    "card_value": font(27, True),
    "small": font(12),
    "table": font(13),
    "table_bold": font(13, True),
}


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))


def blend(color: str, alpha: float, background: str = "#ffffff") -> tuple[int, int, int]:
    fg = hex_to_rgb(color)
    bg = hex_to_rgb(background)
    return tuple(int(bg[i] * (1 - alpha) + fg[i] * alpha) for i in range(3))


def money(value: float) -> str:
    abs_value = abs(value)
    if abs_value >= 1_000_000:
        return f"${value / 1_000_000:.1f}M"
    if abs_value >= 1_000:
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


def panel(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], title: str | None = None) -> None:
    draw.rounded_rectangle(box, radius=18, fill=COLORS["panel"], outline=COLORS["border"], width=1)
    if title:
        draw.text((box[0] + 22, box[1] + 16), title, fill=COLORS["ink"], font=FONTS["h2"])


def kpi_card(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    label: str,
    value: str,
    accent: str,
) -> None:
    panel(draw, box)
    x0, y0, x1, y1 = box
    draw.rounded_rectangle((x0 + 16, y0 + 18, x0 + 24, y1 - 18), radius=4, fill=accent)
    draw.text((x0 + 38, y0 + 19), label, fill=COLORS["muted"], font=FONTS["card_label"])
    draw.text((x0 + 38, y0 + 46), value, fill=COLORS["ink"], font=FONTS["card_value"])


def draw_line_chart(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    data: pd.DataFrame,
    x_col: str,
    y_col: str,
    color: str,
) -> None:
    x0, y0, x1, y1 = box
    chart = (x0 + 54, y0 + 58, x1 - 26, y1 - 42)
    cx0, cy0, cx1, cy1 = chart
    values = data[y_col].astype(float).tolist()
    min_v, max_v = min(values), max(values)
    span = max(max_v - min_v, 1)
    draw.line((cx0, cy1, cx1, cy1), fill="#d4dbe7", width=1)
    draw.line((cx0, cy0, cx0, cy1), fill="#d4dbe7", width=1)
    draw.text((cx0 - 45, cy0 - 8), money(max_v), fill=COLORS["muted"], font=FONTS["small"])
    draw.text((cx0 - 45, cy1 - 10), money(min_v), fill=COLORS["muted"], font=FONTS["small"])
    points = []
    for idx, value in enumerate(values):
        px = cx0 + idx * (cx1 - cx0) / max(len(values) - 1, 1)
        py = cy1 - (value - min_v) / span * (cy1 - cy0)
        points.append((px, py))
    draw.line(points, fill=color, width=4, joint="curve")
    for px, py in points[::3]:
        draw.ellipse((px - 4, py - 4, px + 4, py + 4), fill=color)
    for idx in [0, len(data) // 3, 2 * len(data) // 3, len(data) - 1]:
        month = pd.to_datetime(data.iloc[idx][x_col]).strftime("%b %y")
        px = cx0 + idx * (cx1 - cx0) / max(len(values) - 1, 1)
        draw.text((px - 20, cy1 + 13), month, fill=COLORS["muted"], font=FONTS["small"])


def draw_bar_chart(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    data: pd.DataFrame,
    label_col: str,
    value_col: str,
    color: str,
    money_values: bool = True,
) -> None:
    x0, y0, x1, y1 = box
    chart = (x0 + 190, y0 + 58, x1 - 34, y1 - 26)
    cx0, cy0, cx1, cy1 = chart
    data = data.head(7).copy()
    max_v = max(float(data[value_col].max()), 1)
    gap = 9
    bar_h = (cy1 - cy0 - gap * (len(data) - 1)) / len(data)
    for idx, row in data.reset_index(drop=True).iterrows():
        y = cy0 + idx * (bar_h + gap)
        label = str(row[label_col])
        if len(label) > 21:
            label = label[:18] + "..."
        value = float(row[value_col])
        width = (cx1 - cx0) * value / max_v
        draw.text((x0 + 22, y + bar_h * 0.25), label, fill=COLORS["slate"], font=FONTS["small"])
        draw.rounded_rectangle((cx0, y, cx0 + width, y + bar_h), radius=5, fill=color)
        text = money(value) if money_values else number(value)
        draw.text((cx0 + width + 8, y + bar_h * 0.23), text, fill=COLORS["muted"], font=FONTS["small"])


def draw_table(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    data: pd.DataFrame,
) -> None:
    x0, y0, x1, _ = box
    left = x0 + 22
    top = y0 + 56
    widths = [250, 95, 90]
    headers = ["Product", "Revenue", "Margin"]
    x = left
    for header, width in zip(headers, widths):
        draw.text((x, top), header, fill=COLORS["muted"], font=FONTS["table_bold"])
        x += width
    draw.line((left, top + 24, x1 - 22, top + 24), fill="#e5eaf2", width=1)
    for idx, row in data.head(8).reset_index(drop=True).iterrows():
        y = top + 36 + idx * 28
        name = str(row["product_name"])
        if len(name) > 31:
            name = name[:28] + "..."
        margin = f"{float(row['profit_margin_pct']):.1f}%"
        draw.text((left, y), name, fill=COLORS["ink"], font=FONTS["table"])
        draw.text((left + widths[0], y), money(float(row["revenue"])), fill=COLORS["ink"], font=FONTS["table"])
        draw.text((left + widths[0] + widths[1], y), margin, fill=COLORS["ink"], font=FONTS["table"])


def draw_heatmap(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], retention: pd.DataFrame) -> None:
    x0, y0, x1, y1 = box
    data = retention.head(10).copy()
    month_cols = [c for c in data.columns if c != "cohort_month"][:10]
    left, top = x0 + 90, y0 + 58
    cell_w = (x1 - left - 24) / len(month_cols)
    cell_h = (y1 - top - 24) / len(data)
    for j, col in enumerate(month_cols):
        draw.text((left + j * cell_w + 8, top - 22), f"M{col}", fill=COLORS["muted"], font=FONTS["small"])
    for i, row in data.reset_index(drop=True).iterrows():
        month = str(row["cohort_month"])[:7]
        draw.text((x0 + 22, top + i * cell_h + 7), month, fill=COLORS["muted"], font=FONTS["small"])
        for j, col in enumerate(month_cols):
            value = row[col]
            if pd.isna(value):
                fill = "#f8fafc"
                label = ""
            else:
                intensity = min(float(value) / 100, 1)
                fill = blend(COLORS["teal"], 0.10 + intensity * 0.78)
                label = f"{float(value):.0f}"
            x = left + j * cell_w
            y = top + i * cell_h
            draw.rounded_rectangle((x, y, x + cell_w - 5, y + cell_h - 5), radius=4, fill=fill)
            if label:
                draw.text((x + 8, y + 6), label, fill=COLORS["ink"], font=FONTS["small"])


def main() -> None:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    kpis = pd.read_csv(TABLE_DIR / "executive_kpis.csv").iloc[0]
    monthly = pd.read_csv(TABLE_DIR / "monthly_revenue.csv")
    category = pd.read_csv(TABLE_DIR / "category_performance.csv")
    rfm = pd.read_csv(TABLE_DIR / "rfm_segment_summary.csv")
    products = pd.read_csv(TABLE_DIR / "product_performance.csv")
    retention = pd.read_csv(TABLE_DIR / "cohort_retention.csv")

    img = Image.new("RGB", (1600, 1000), COLORS["bg"])
    draw = ImageDraw.Draw(img)

    draw.rounded_rectangle((28, 26, 1572, 118), radius=22, fill="#111827")
    draw.text((58, 48), "E-commerce Customer Analytics Dashboard", fill="#ffffff", font=FONTS["title"])
    draw.text((60, 89), "Power BI dashboard preview | Revenue, retention, RFM segmentation, and product performance", fill="#cbd5e1", font=FONTS["subtitle"])
    for i, label in enumerate(["Date: 2023-2025", "Country: All", "Category: All"]):
        x = 1060 + i * 160
        draw.rounded_rectangle((x, 54, x + 138, 89), radius=8, fill="#1f2937", outline="#374151")
        draw.text((x + 12, 62), label, fill="#e5e7eb", font=FONTS["small"])

    card_y, card_h = 142, 96
    card_w, gap = 242, 16
    cards = [
        ("Total Revenue", money(float(kpis["total_revenue"])), COLORS["blue"]),
        ("Total Orders", number(float(kpis["total_orders"])), COLORS["teal"]),
        ("Customers", number(float(kpis["total_customers"])), COLORS["purple"]),
        ("AOV", money(float(kpis["average_order_value"])), COLORS["orange"]),
        ("Repeat Rate", pct(float(kpis["repeat_customer_rate_pct"])), COLORS["green"]),
        ("Return Rate", pct(float(kpis["return_rate_pct"])), COLORS["red"]),
    ]
    for idx, (label, value, accent) in enumerate(cards):
        x = 28 + idx * (card_w + gap)
        kpi_card(draw, (x, card_y, x + card_w, card_y + card_h), label, value, accent)

    panel(draw, (28, 264, 928, 548), "Monthly Revenue Trend")
    draw_line_chart(draw, (28, 264, 928, 548), monthly, "order_month", "revenue", COLORS["teal"])

    category_chart = category.groupby("category", as_index=False)["gross_profit"].sum().sort_values("gross_profit", ascending=False)
    panel(draw, (950, 264, 1572, 548), "Gross Profit by Category")
    draw_bar_chart(draw, (950, 264, 1572, 548), category_chart, "category", "gross_profit", COLORS["blue"])

    panel(draw, (28, 570, 530, 956), "Revenue by RFM Segment")
    draw_bar_chart(draw, (28, 570, 530, 956), rfm.sort_values("revenue", ascending=False), "customer_segment", "revenue", COLORS["purple"])

    panel(draw, (552, 570, 1048, 956), "Cohort Retention Heatmap")
    draw_heatmap(draw, (552, 570, 1048, 956), retention)

    panel(draw, (1070, 570, 1572, 956), "Top Products")
    draw_table(draw, (1070, 570, 1572, 956), products.sort_values("revenue", ascending=False))

    img.save(SCREENSHOT_PATH, optimize=True, quality=95)
    print(f"Dashboard screenshot written to {SCREENSHOT_PATH}")


if __name__ == "__main__":
    main()

