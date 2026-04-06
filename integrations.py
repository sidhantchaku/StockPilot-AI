import re
from io import StringIO

import pandas as pd
import requests


def _safe_float(value, fallback=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def fetch_shopify_inventory(store_domain: str, access_token: str, limit: int = 100) -> pd.DataFrame:
    url = f"https://{store_domain.strip().rstrip('/')}/admin/api/2024-04/products.json"
    response = requests.get(
        url,
        headers={"X-Shopify-Access-Token": access_token.strip()},
        params={"limit": max(1, min(limit, 250))},
        timeout=20,
    )
    response.raise_for_status()
    products = response.json().get("products", [])

    rows = []
    for product in products:
        variants = product.get("variants", [])
        for variant in variants:
            rows.append(
                {
                    "Product": variant.get("sku") or variant.get("title") or product.get("title"),
                    "Quantity": variant.get("inventory_quantity") if variant.get("inventory_quantity") is not None else 0,
                    "Unit Price": _safe_float(variant.get("price"), 0.0),
                    "Area/Location": product.get("vendor") or "Online Store",
                    "Last Sale Date": pd.Timestamp.utcnow().date().isoformat(),
                }
            )
    return pd.DataFrame(rows)


def fetch_woocommerce_inventory(
    store_url: str,
    consumer_key: str,
    consumer_secret: str,
    per_page: int = 100,
) -> pd.DataFrame:
    url = f"{store_url.strip().rstrip('/')}/wp-json/wc/v3/products"
    response = requests.get(
        url,
        params={
            "consumer_key": consumer_key.strip(),
            "consumer_secret": consumer_secret.strip(),
            "per_page": max(1, min(per_page, 100)),
        },
        timeout=20,
    )
    response.raise_for_status()
    products = response.json()

    rows = []
    for product in products:
        rows.append(
            {
                "Product": product.get("sku") or product.get("name"),
                "Quantity": product.get("stock_quantity") if product.get("stock_quantity") is not None else 0,
                "Unit Price": _safe_float(product.get("regular_price"), 0.0),
                "Area/Location": "WooCommerce",
                "Last Sale Date": pd.Timestamp.utcnow().date().isoformat(),
            }
        )
    return pd.DataFrame(rows)


def _google_sheet_to_csv_url(sheet_input: str) -> str:
    text = sheet_input.strip()
    if "docs.google.com/spreadsheets" in text:
        match = re.search(r"/d/([a-zA-Z0-9-_]+)", text)
        if not match:
            raise ValueError("Could not parse Google Sheet ID from URL.")
        sheet_id = match.group(1)
        gid_match = re.search(r"[?&]gid=(\d+)", text)
        gid = gid_match.group(1) if gid_match else "0"
        return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    return text


def fetch_google_sheets_inventory(sheet_input: str) -> pd.DataFrame:
    csv_url = _google_sheet_to_csv_url(sheet_input)
    return pd.read_csv(csv_url)


def fetch_erp_csv_inventory(csv_url: str) -> pd.DataFrame:
    response = requests.get(csv_url.strip(), timeout=20)
    response.raise_for_status()
    return pd.read_csv(StringIO(response.text))


def fetch_erp_api_inventory(api_url: str, bearer_token: str | None = None) -> pd.DataFrame:
    headers = {}
    if bearer_token and bearer_token.strip():
        headers["Authorization"] = f"Bearer {bearer_token.strip()}"
    response = requests.get(api_url.strip(), headers=headers, timeout=20)
    response.raise_for_status()
    payload = response.json()
    if isinstance(payload, dict):
        if "data" in payload and isinstance(payload["data"], list):
            payload = payload["data"]
        else:
            payload = [payload]
    if not isinstance(payload, list):
        raise ValueError("ERP API response must be a list or a dict containing a list under 'data'.")
    return pd.DataFrame(payload)
