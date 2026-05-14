from __future__ import annotations

import argparse
from datetime import timedelta

import numpy as np
import pandas as pd

from config import RAW_DIR, RANDOM_SEED, ensure_directories


ORDER_START = pd.Timestamp("2023-01-01")
ORDER_END = pd.Timestamp("2025-12-31")
SIGNUP_START = pd.Timestamp("2022-01-01")
SIGNUP_END = pd.Timestamp("2025-11-30")


CATEGORY_CONFIG = {
    "Electronics": {
        "sub_categories": {
            "Phones": (250, 1200),
            "Laptops": (550, 2200),
            "Audio": (35, 450),
            "Cameras": (180, 1400),
            "Accessories": (12, 180),
        },
        "brands": ["Aster", "Nexora", "PulseTech", "ZenByte", "Orbit"],
        "weight": 0.16,
    },
    "Fashion": {
        "sub_categories": {
            "Men Apparel": (18, 180),
            "Women Apparel": (20, 220),
            "Footwear": (35, 260),
            "Bags": (25, 320),
            "Accessories": (8, 90),
        },
        "brands": ["UrbanThread", "Modeva", "NorthStitch", "Walkway", "Luma"],
        "weight": 0.19,
    },
    "Home & Kitchen": {
        "sub_categories": {
            "Cookware": (15, 220),
            "Furniture": (90, 1200),
            "Decor": (12, 180),
            "Storage": (10, 140),
            "Appliances": (45, 650),
        },
        "brands": ["Homely", "CraftHaus", "BrightNest", "Kiva", "Elm & Co"],
        "weight": 0.17,
    },
    "Beauty": {
        "sub_categories": {
            "Skincare": (9, 120),
            "Makeup": (7, 95),
            "Haircare": (8, 110),
            "Fragrance": (18, 180),
        },
        "brands": ["Glowery", "BareBloom", "Auren", "Silka", "Citrine"],
        "weight": 0.12,
    },
    "Sports": {
        "sub_categories": {
            "Fitness": (12, 350),
            "Outdoor": (25, 550),
            "Team Sports": (10, 220),
            "Cycling": (40, 900),
        },
        "brands": ["VoltFit", "TrailPeak", "MotionLab", "ArenaPro", "Stride"],
        "weight": 0.11,
    },
    "Books": {
        "sub_categories": {
            "Fiction": (6, 40),
            "Business": (9, 65),
            "Technology": (12, 80),
            "Children": (5, 35),
        },
        "brands": ["PageMint", "Northstar Press", "Inkline", "BlueLeaf"],
        "weight": 0.08,
    },
    "Toys": {
        "sub_categories": {
            "STEM Toys": (12, 130),
            "Board Games": (10, 90),
            "Dolls": (8, 110),
            "Outdoor Toys": (15, 180),
        },
        "brands": ["BrightPlay", "WonderBox", "Kidora", "PuzzleWorks"],
        "weight": 0.08,
    },
    "Grocery": {
        "sub_categories": {
            "Pantry": (3, 45),
            "Beverages": (4, 55),
            "Organic": (5, 70),
            "Snacks": (2, 35),
        },
        "brands": ["Freshly", "HarvestLane", "DailyBite", "GreenFarm"],
        "weight": 0.09,
    },
}


LOCATIONS = [
    ("United States", "California", "Los Angeles", 0.075),
    ("United States", "California", "San Francisco", 0.050),
    ("United States", "New York", "New York", 0.070),
    ("United States", "Texas", "Austin", 0.048),
    ("United States", "Texas", "Dallas", 0.043),
    ("United States", "Illinois", "Chicago", 0.047),
    ("United States", "Florida", "Miami", 0.043),
    ("United States", "Washington", "Seattle", 0.040),
    ("United States", "Georgia", "Atlanta", 0.040),
    ("United States", "Massachusetts", "Boston", 0.034),
    ("United States", "Colorado", "Denver", 0.030),
    ("United States", "Arizona", "Phoenix", 0.030),
    ("India", "Karnataka", "Bengaluru", 0.060),
    ("India", "Maharashtra", "Mumbai", 0.045),
    ("India", "Delhi", "New Delhi", 0.035),
    ("United Kingdom", "England", "London", 0.050),
    ("United Kingdom", "England", "Manchester", 0.025),
    ("Canada", "Ontario", "Toronto", 0.040),
    ("Canada", "British Columbia", "Vancouver", 0.028),
    ("Australia", "New South Wales", "Sydney", 0.033),
    ("Australia", "Victoria", "Melbourne", 0.029),
]

FIRST_NAMES = [
    "Aarav",
    "Aisha",
    "Alex",
    "Amelia",
    "Aria",
    "Benjamin",
    "Camila",
    "Daniel",
    "Ethan",
    "Fatima",
    "Grace",
    "Hannah",
    "Isabella",
    "James",
    "Kai",
    "Liam",
    "Maya",
    "Mia",
    "Noah",
    "Olivia",
    "Priya",
    "Ravi",
    "Sofia",
    "Theo",
    "Zara",
]

LAST_NAMES = [
    "Anderson",
    "Brown",
    "Chen",
    "Davis",
    "Garcia",
    "Gupta",
    "Johnson",
    "Khan",
    "Kim",
    "Lee",
    "Martinez",
    "Miller",
    "Patel",
    "Robinson",
    "Sharma",
    "Singh",
    "Smith",
    "Taylor",
    "Thomas",
    "Wilson",
]


def _weighted_choice(values: list[str], weights: list[float], size: int, rng: np.random.Generator) -> np.ndarray:
    weights_array = np.array(weights, dtype=float)
    weights_array = weights_array / weights_array.sum()
    return rng.choice(values, size=size, p=weights_array)


def _date_strings(dates: pd.Series | pd.DatetimeIndex | np.ndarray) -> pd.Series:
    converted = pd.to_datetime(dates)
    if isinstance(converted, pd.Series):
        return converted.dt.strftime("%Y-%m-%d")
    return converted.strftime("%Y-%m-%d")


def build_products(product_count: int, rng: np.random.Generator) -> pd.DataFrame:
    categories = list(CATEGORY_CONFIG)
    category_weights = [CATEGORY_CONFIG[c]["weight"] for c in categories]
    chosen_categories = _weighted_choice(categories, category_weights, product_count, rng)

    records = []
    for idx, category in enumerate(chosen_categories, start=1):
        config = CATEGORY_CONFIG[category]
        subcats = list(config["sub_categories"])
        sub_category = rng.choice(subcats)
        low, high = config["sub_categories"][sub_category]
        brand = rng.choice(config["brands"])

        price = round(float(rng.triangular(low, (low + high) / 2.7, high)), 2)
        if category in {"Electronics", "Furniture"}:
            cost_ratio = rng.uniform(0.58, 0.78)
        elif category in {"Fashion", "Beauty"}:
            cost_ratio = rng.uniform(0.35, 0.62)
        else:
            cost_ratio = rng.uniform(0.42, 0.70)
        cost = round(price * cost_ratio, 2)

        product_code = f"{idx:04d}"
        product_name = f"{brand} {sub_category} {product_code}"
        records.append(
            {
                "product_id": f"P{idx:06d}",
                "product_name": product_name,
                "category": category,
                "sub_category": sub_category,
                "brand": brand,
                "cost_price": cost,
                "selling_price": price,
            }
        )

    products = pd.DataFrame(records)
    missing_brand_mask = rng.random(product_count) < 0.003
    products.loc[missing_brand_mask, "brand"] = np.nan
    return products


def build_customers(customer_count: int, rng: np.random.Generator) -> pd.DataFrame:
    customer_ids = np.array([f"C{i:07d}" for i in range(1, customer_count + 1)])
    names = (
        rng.choice(FIRST_NAMES, size=customer_count)
        + " "
        + rng.choice(LAST_NAMES, size=customer_count)
    )

    age = np.clip(np.round(rng.normal(37, 12, size=customer_count)), 18, 76).astype(int)
    gender = rng.choice(
        ["Female", "Male", "Non-binary", "Prefer not to say"],
        size=customer_count,
        p=[0.49, 0.48, 0.02, 0.01],
    ).astype(object)

    location_weights = [row[3] for row in LOCATIONS]
    chosen_location_idx = rng.choice(len(LOCATIONS), size=customer_count, p=np.array(location_weights) / np.sum(location_weights))
    countries = [LOCATIONS[i][0] for i in chosen_location_idx]
    states = [LOCATIONS[i][1] for i in chosen_location_idx]
    cities = [LOCATIONS[i][2] for i in chosen_location_idx]

    signup_span = (SIGNUP_END - SIGNUP_START).days
    signup_offsets = np.round(rng.beta(1.7, 1.25, size=customer_count) * signup_span).astype(int)
    signup_dates = SIGNUP_START + pd.to_timedelta(signup_offsets, unit="D")

    customers = pd.DataFrame(
        {
            "customer_id": customer_ids,
            "customer_name": names,
            "gender": gender,
            "age": age,
            "city": cities,
            "state": states,
            "country": countries,
            "signup_date": _date_strings(signup_dates),
        }
    )

    lower_gender = rng.random(customer_count) < 0.01
    customers.loc[lower_gender, "gender"] = customers.loc[lower_gender, "gender"].str.lower()
    padded_gender = rng.random(customer_count) < 0.006
    customers.loc[padded_gender, "gender"] = " " + customers.loc[padded_gender, "gender"].astype(str) + " "
    missing_name = rng.random(customer_count) < 0.002
    customers.loc[missing_name, "customer_name"] = np.nan
    missing_city = rng.random(customer_count) < 0.0015
    customers.loc[missing_city, "city"] = np.nan
    return customers


def _sample_order_dates(signup_date: pd.Timestamp, count: int, rng: np.random.Generator) -> list[pd.Timestamp]:
    start = max(pd.Timestamp(signup_date), ORDER_START)
    if start > ORDER_END:
        start = ORDER_END - pd.Timedelta(days=30)
    span = max((ORDER_END - start).days, 1)
    month_factor = {
        1: 0.82,
        2: 0.78,
        3: 0.90,
        4: 0.95,
        5: 1.00,
        6: 0.98,
        7: 1.05,
        8: 1.10,
        9: 1.02,
        10: 1.15,
        11: 1.70,
        12: 1.85,
    }
    max_factor = max(month_factor.values())
    dates: list[pd.Timestamp] = []
    attempts = 0
    while len(dates) < count and attempts < count * 50:
        attempts += 1
        candidate = start + pd.Timedelta(days=int(rng.integers(0, span + 1)))
        if rng.random() <= month_factor[candidate.month] / max_factor:
            dates.append(candidate)
    while len(dates) < count:
        dates.append(start + pd.Timedelta(days=int(rng.integers(0, span + 1))))
    return sorted(dates)


def build_orders(customers: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    tiers = rng.choice(
        ["one_time", "occasional", "repeat", "loyal", "champion"],
        size=len(customers),
        p=[0.38, 0.29, 0.20, 0.10, 0.03],
    )

    order_counts = np.zeros(len(customers), dtype=int)
    order_counts[tiers == "one_time"] = 1
    order_counts[tiers == "occasional"] = rng.integers(2, 4, size=(tiers == "occasional").sum())
    order_counts[tiers == "repeat"] = rng.integers(4, 8, size=(tiers == "repeat").sum())
    order_counts[tiers == "loyal"] = rng.integers(8, 15, size=(tiers == "loyal").sum())
    order_counts[tiers == "champion"] = rng.integers(15, 31, size=(tiers == "champion").sum())

    records = []
    order_number = 1
    payment_methods = ["Credit Card", "Debit Card", "PayPal", "Gift Card", "UPI", "Buy Now Pay Later"]
    payment_probs = [0.38, 0.20, 0.17, 0.08, 0.10, 0.07]
    statuses = ["Completed", "Shipped", "Returned", "Cancelled"]
    status_probs = [0.83, 0.08, 0.055, 0.035]

    signup_dates = pd.to_datetime(customers["signup_date"], errors="coerce").fillna(ORDER_START)
    for customer_id, signup_date, count in zip(customers["customer_id"], signup_dates, order_counts):
        dates = _sample_order_dates(signup_date, int(count), rng)
        for order_date in dates:
            status = rng.choice(statuses, p=status_probs)
            shipment_date = pd.NaT if status == "Cancelled" else order_date + pd.Timedelta(days=int(rng.integers(1, 8)))
            payment = rng.choice(payment_methods, p=payment_probs)
            records.append(
                {
                    "order_id": f"O{order_number:08d}",
                    "customer_id": customer_id,
                    "order_date": order_date.strftime("%Y-%m-%d"),
                    "shipment_date": "" if pd.isna(shipment_date) else shipment_date.strftime("%Y-%m-%d"),
                    "payment_method": payment,
                    "order_status": status,
                    "total_amount": 0.0,
                }
            )
            order_number += 1

    orders = pd.DataFrame(records)
    noisy_payment = rng.random(len(orders)) < 0.006
    orders.loc[noisy_payment & (orders["payment_method"] == "Credit Card"), "payment_method"] = "credit card"
    orders.loc[noisy_payment & (orders["payment_method"] == "PayPal"), "payment_method"] = "Pay Pal "
    return orders


def build_order_items(orders: pd.DataFrame, products: pd.DataFrame, rng: np.random.Generator) -> tuple[pd.DataFrame, pd.DataFrame]:
    item_counts = rng.choice([1, 2, 3, 4, 5], size=len(orders), p=[0.39, 0.30, 0.18, 0.09, 0.04])
    order_ids = np.repeat(orders["order_id"].to_numpy(), item_counts)
    order_months = np.repeat(pd.to_datetime(orders["order_date"]).dt.month.to_numpy(), item_counts)
    n_items = len(order_ids)

    category_weights = products["category"].map({c: CATEGORY_CONFIG[c]["weight"] for c in CATEGORY_CONFIG}).to_numpy(dtype=float)
    product_noise = rng.lognormal(mean=0.0, sigma=0.55, size=len(products))
    product_weights = category_weights * product_noise
    product_weights = product_weights / product_weights.sum()

    product_positions = rng.choice(len(products), size=n_items, p=product_weights)
    selected_products = products.iloc[product_positions].reset_index(drop=True)
    quantity = rng.choice([1, 2, 3, 4], size=n_items, p=[0.72, 0.20, 0.06, 0.02])

    price_multiplier = rng.normal(1.0, 0.025, size=n_items)
    price_per_unit = np.maximum(1.0, selected_products["selling_price"].to_numpy(dtype=float) * price_multiplier)

    base_discount = rng.choice([0.00, 0.05, 0.10, 0.15, 0.20, 0.25], size=n_items, p=[0.48, 0.18, 0.16, 0.10, 0.06, 0.02])
    seasonal_discount = np.where(
        np.isin(order_months, [11, 12]),
        rng.choice([0.00, 0.05, 0.10], size=n_items, p=[0.45, 0.38, 0.17]),
        0,
    )
    category_discount = np.where(
        selected_products["category"].isin(["Fashion", "Beauty", "Toys"]),
        rng.choice([0.00, 0.05], size=n_items, p=[0.70, 0.30]),
        0,
    )
    discount = np.minimum(base_discount + seasonal_discount + category_discount, 0.40)

    order_items = pd.DataFrame(
        {
            "order_item_id": [f"OI{i:09d}" for i in range(1, n_items + 1)],
            "order_id": order_ids,
            "product_id": selected_products["product_id"].to_numpy(),
            "quantity": quantity,
            "price_per_unit": np.round(price_per_unit, 2),
            "discount": np.round(discount, 2),
        }
    )
    order_items["line_amount"] = order_items["quantity"] * order_items["price_per_unit"] * (1 - order_items["discount"])
    order_totals = order_items.groupby("order_id", as_index=False)["line_amount"].sum()
    order_totals["line_amount"] = order_totals["line_amount"].round(2)
    orders = orders.merge(order_totals.rename(columns={"line_amount": "computed_total"}), on="order_id", how="left")
    orders["total_amount"] = orders["computed_total"].fillna(0).round(2)
    orders = orders.drop(columns=["computed_total"])
    return order_items.drop(columns=["line_amount"]), orders


def build_returns(orders: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    returned_orders = orders.loc[orders["order_status"] == "Returned", ["order_id", "shipment_date"]].copy()
    reasons = ["Damaged item", "Late delivery", "Wrong item", "Size issue", "Changed mind", "Quality issue"]
    if returned_orders.empty:
        return pd.DataFrame(columns=["return_id", "order_id", "return_reason", "return_date"])

    shipment_dates = pd.to_datetime(returned_orders["shipment_date"], errors="coerce").fillna(pd.Timestamp("2025-01-01"))
    return_offsets = rng.integers(2, 31, size=len(returned_orders))
    returns = pd.DataFrame(
        {
            "return_id": [f"R{i:07d}" for i in range(1, len(returned_orders) + 1)],
            "order_id": returned_orders["order_id"].to_numpy(),
            "return_reason": rng.choice(reasons, size=len(returned_orders), p=[0.18, 0.16, 0.15, 0.17, 0.14, 0.20]),
            "return_date": _date_strings(shipment_dates + pd.to_timedelta(return_offsets, unit="D")),
        }
    )
    return returns


def inject_duplicate_rows(df: pd.DataFrame, n: int, rng: np.random.Generator) -> pd.DataFrame:
    if len(df) == 0 or n <= 0:
        return df
    duplicated = df.sample(n=min(n, len(df)), random_state=int(rng.integers(0, 1_000_000)))
    return pd.concat([df, duplicated], ignore_index=True)


def generate(customer_count: int, product_count: int, seed: int) -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    ensure_directories()

    products = build_products(product_count, rng)
    customers = build_customers(customer_count, rng)
    orders = build_orders(customers, rng)
    order_items, orders = build_order_items(orders, products, rng)
    returns = build_returns(orders, rng)

    raw_tables = {
        "customers": inject_duplicate_rows(customers, max(25, customer_count // 400), rng),
        "products": inject_duplicate_rows(products, 5, rng),
        "orders": inject_duplicate_rows(orders, max(40, len(orders) // 1200), rng),
        "order_items": inject_duplicate_rows(order_items, max(100, len(order_items) // 2000), rng),
        "returns": inject_duplicate_rows(returns, max(5, len(returns) // 500), rng),
    }

    for name, df in raw_tables.items():
        df.to_csv(RAW_DIR / f"{name}.csv", index=False)

    return raw_tables


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic e-commerce source data.")
    parser.add_argument("--customers", type=int, default=50_000)
    parser.add_argument("--products", type=int, default=800)
    parser.add_argument("--seed", type=int, default=RANDOM_SEED)
    args = parser.parse_args()

    tables = generate(args.customers, args.products, args.seed)
    for name, df in tables.items():
        print(f"{name}: {len(df):,} raw rows -> {RAW_DIR / f'{name}.csv'}")


if __name__ == "__main__":
    main()
