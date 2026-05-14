from __future__ import annotations

import pandas as pd

from config import PROCESSED_DIR, RAW_DIR, TABLE_OUTPUT_DIR, ensure_directories


PRIMARY_KEYS = {
    "customers": "customer_id",
    "products": "product_id",
    "orders": "order_id",
    "order_items": "order_item_id",
    "returns": "return_id",
}


def _standardize_text(series: pd.Series) -> pd.Series:
    return series.astype("string").str.strip()


def _title(series: pd.Series) -> pd.Series:
    return _standardize_text(series).str.replace(r"\s+", " ", regex=True).str.title()


def _load_raw() -> dict[str, pd.DataFrame]:
    return {name: pd.read_csv(RAW_DIR / f"{name}.csv") for name in PRIMARY_KEYS}


def _drop_duplicate_rows(df: pd.DataFrame, table: str) -> tuple[pd.DataFrame, int, int]:
    original = len(df)
    df = df.drop_duplicates()
    after_row_dedup = len(df)
    df = df.drop_duplicates(subset=[PRIMARY_KEYS[table]], keep="first")
    return df.copy(), original - after_row_dedup, after_row_dedup - len(df)


def clean() -> dict[str, pd.DataFrame]:
    ensure_directories()
    raw = _load_raw()
    quality_rows = []

    cleaned = {}
    for table, df in raw.items():
        before = len(df)
        df, duplicate_rows, duplicate_keys = _drop_duplicate_rows(df, table)
        quality_rows.append(
            {
                "table_name": table,
                "raw_rows": before,
                "duplicate_rows_removed": duplicate_rows,
                "duplicate_primary_keys_removed": duplicate_keys,
                "rows_after_deduplication": len(df),
            }
        )
        cleaned[table] = df

    customers = cleaned["customers"]
    customers["customer_id"] = _standardize_text(customers["customer_id"])
    customers["customer_name"] = _title(customers["customer_name"])
    customers["gender"] = _title(customers["gender"])
    gender_map = {
        "Female": "Female",
        "Male": "Male",
        "Non-Binary": "Non-binary",
        "Prefer Not To Say": "Prefer not to say",
    }
    customers["gender"] = customers["gender"].map(gender_map).fillna("Unknown")
    customers["age"] = pd.to_numeric(customers["age"], errors="coerce").clip(18, 90).round()
    customers["age"] = customers["age"].fillna(customers["age"].median()).astype(int)
    for col in ["city", "state", "country"]:
        customers[col] = _title(customers[col]).fillna("Unknown")
    missing_name = customers["customer_name"].isna() | (customers["customer_name"] == "")
    customers.loc[missing_name, "customer_name"] = "Customer " + customers.loc[missing_name, "customer_id"].astype(str)
    customers["signup_date"] = pd.to_datetime(customers["signup_date"], errors="coerce")
    customers["signup_date"] = customers["signup_date"].fillna(customers["signup_date"].median()).dt.strftime("%Y-%m-%d")

    products = cleaned["products"]
    for col in ["product_id", "product_name", "category", "sub_category", "brand"]:
        products[col] = _standardize_text(products[col])
    products["product_name"] = products["product_name"].fillna("Unknown Product")
    products["category"] = products["category"].fillna("Uncategorized")
    products["sub_category"] = products["sub_category"].fillna("Uncategorized")
    products["brand"] = products["brand"].fillna("Private Label")
    for col in ["cost_price", "selling_price"]:
        products[col] = pd.to_numeric(products[col], errors="coerce")
        products[col] = products[col].fillna(products[col].median()).round(2)
    products["cost_price"] = products[["cost_price", "selling_price"]].min(axis=1).round(2)

    orders = cleaned["orders"]
    orders["order_id"] = _standardize_text(orders["order_id"])
    orders["customer_id"] = _standardize_text(orders["customer_id"])
    orders["payment_method"] = _title(orders["payment_method"])
    orders["payment_method"] = orders["payment_method"].replace({"Pay Pal": "PayPal"})
    orders["order_status"] = _title(orders["order_status"])
    orders["order_status"] = orders["order_status"].where(
        orders["order_status"].isin(["Completed", "Shipped", "Returned", "Cancelled"]),
        "Completed",
    )
    orders["order_date"] = pd.to_datetime(orders["order_date"], errors="coerce")
    orders["order_date"] = orders["order_date"].fillna(orders["order_date"].median())
    orders["shipment_date"] = pd.to_datetime(orders["shipment_date"], errors="coerce")
    missing_ship = orders["shipment_date"].isna() & (orders["order_status"] != "Cancelled")
    orders.loc[missing_ship, "shipment_date"] = orders.loc[missing_ship, "order_date"] + pd.Timedelta(days=4)
    orders["total_amount"] = pd.to_numeric(orders["total_amount"], errors="coerce").fillna(0)
    orders = orders[orders["customer_id"].isin(set(customers["customer_id"]))].copy()

    order_items = cleaned["order_items"]
    for col in ["order_item_id", "order_id", "product_id"]:
        order_items[col] = _standardize_text(order_items[col])
    order_items["quantity"] = pd.to_numeric(order_items["quantity"], errors="coerce").fillna(1).clip(1, 99).astype(int)
    order_items["price_per_unit"] = pd.to_numeric(order_items["price_per_unit"], errors="coerce").fillna(0).clip(lower=0).round(2)
    order_items["discount"] = pd.to_numeric(order_items["discount"], errors="coerce").fillna(0).clip(0, 0.60).round(2)
    order_items = order_items[
        order_items["order_id"].isin(set(orders["order_id"]))
        & order_items["product_id"].isin(set(products["product_id"]))
    ].copy()

    recalculated_totals = order_items.assign(
        line_amount=order_items["quantity"] * order_items["price_per_unit"] * (1 - order_items["discount"])
    ).groupby("order_id", as_index=False)["line_amount"].sum()
    recalculated_totals["line_amount"] = recalculated_totals["line_amount"].round(2)
    orders = orders.drop(columns=["total_amount"]).merge(
        recalculated_totals.rename(columns={"line_amount": "total_amount"}),
        on="order_id",
        how="left",
    )
    orders["total_amount"] = orders["total_amount"].fillna(0).round(2)
    orders = orders[orders["order_id"].isin(set(order_items["order_id"]))].copy()

    returns = cleaned["returns"]
    returns["return_id"] = _standardize_text(returns["return_id"])
    returns["order_id"] = _standardize_text(returns["order_id"])
    returns["return_reason"] = _title(returns["return_reason"]).fillna("Unknown")
    returns["return_date"] = pd.to_datetime(returns["return_date"], errors="coerce")
    returns = returns[returns["order_id"].isin(set(orders["order_id"]))].copy()
    returns["return_date"] = returns["return_date"].fillna(pd.to_datetime(orders["order_date"]).max()).dt.strftime("%Y-%m-%d")

    orders["order_date"] = orders["order_date"].dt.strftime("%Y-%m-%d")
    orders["shipment_date"] = orders["shipment_date"].dt.strftime("%Y-%m-%d").fillna("")

    processed = {
        "customers": customers.sort_values("customer_id"),
        "products": products.sort_values("product_id"),
        "orders": orders.sort_values("order_id"),
        "order_items": order_items.sort_values("order_item_id"),
        "returns": returns.sort_values("return_id"),
    }

    for table, df in processed.items():
        df.to_csv(PROCESSED_DIR / f"{table}.csv", index=False)

    quality = pd.DataFrame(quality_rows)
    final_counts = pd.DataFrame(
        [{"table_name": table, "processed_rows": len(df)} for table, df in processed.items()]
    )
    quality = quality.merge(final_counts, on="table_name", how="left")
    quality.to_csv(TABLE_OUTPUT_DIR / "data_quality_report.csv", index=False)

    return processed


def main() -> None:
    processed = clean()
    for name, df in processed.items():
        print(f"{name}: {len(df):,} clean rows -> {PROCESSED_DIR / f'{name}.csv'}")


if __name__ == "__main__":
    main()

