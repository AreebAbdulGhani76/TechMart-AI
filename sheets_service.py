"""
Google Sheets Integration Service for TechMart RAG Agent
Connects to Google Sheets using Service Account credentials for:
- Products catalog: https://docs.google.com/spreadsheets/d/1RZ1U4TKfqqjY4kpbvFUQOJd_PwDlYp0I/edit?gid=1097220337#gid=1097220337
- Orders database: https://docs.google.com/spreadsheets/d/18G2BQlwSihkgC5JcCFosbMVEbSQBQE_hgvKpFogcWCI/edit?gid=1288216522#gid=1288216522
- Bank details: https://docs.google.com/spreadsheets/d/1gWgVsSVU4u1V8qTcEIKj7F81XxY02Y-0sJCdc-J6gNg/edit?gid=0#gid=0
"""

import os
import io
import re
import glob
import json
import logging
import urllib.parse
from typing import List, Dict, Any, Tuple, Optional
import pandas as pd
from google.oauth2 import service_account
from google.auth.transport.requests import AuthorizedSession

import time

logger = logging.getLogger(__name__)

# Constants for Google Sheets IDs (from environment or defaults)
PRODUCTS_SHEET_ID = os.environ.get("PRODUCTS_SHEET_ID", "1RZ1U4TKfqqjY4kpbvFUQOJd_PwDlYp0I")
PRODUCTS_GID = int(os.environ.get("PRODUCTS_GID", 1097220337))

ORDERS_SHEET_ID = os.environ.get("ORDERS_SHEET_ID", "18G2BQlwSihkgC5JcCFosbMVEbSQBQE_hgvKpFogcWCI")
ORDERS_GID = int(os.environ.get("ORDERS_GID", 1288216522))

BANK_DETAILS_SHEET_ID = os.environ.get("BANK_DETAILS_SHEET_ID", "1gWgVsSVU4u1V8qTcEIKj7F81XxY02Y-0sJCdc-J6gNg")
BANK_DETAILS_GID = int(os.environ.get("BANK_DETAILS_GID", 0))

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOCAL_BACKUP_BANK_FILE = os.path.join(_BASE_DIR, "bank_details_local_backup.json")
LOCAL_BACKUP_ORDERS_FILE = os.path.join(_BASE_DIR, "orders_local_backup.json")

# In-Memory High Speed Caching
_ORDERS_CACHE: Optional[List[Dict[str, Any]]] = None
_ORDERS_CACHE_TIME: float = 0
_BANK_CACHE: Optional[List[Dict[str, Any]]] = None
_BANK_CACHE_TIME: float = 0
_PRODUCTS_CACHE: Optional[pd.DataFrame] = None
_PRODUCTS_CACHE_TIME: float = 0
_SESSION_CACHE: Optional[AuthorizedSession] = None
_SESSION_CACHE_TIME: float = 0

CACHE_TTL = 120.0  # Cache in memory for 2 minutes


def clear_cache():
    """Invalidates in-memory caches to fetch fresh data from Google Sheets."""
    global _ORDERS_CACHE, _BANK_CACHE, _PRODUCTS_CACHE, _ORDERS_CACHE_TIME, _BANK_CACHE_TIME, _PRODUCTS_CACHE_TIME
    _ORDERS_CACHE = None
    _ORDERS_CACHE_TIME = 0
    _BANK_CACHE = None
    _BANK_CACHE_TIME = 0
    _PRODUCTS_CACHE = None
    _PRODUCTS_CACHE_TIME = 0


def find_credentials_file() -> Optional[str]:
    """Finds the Google Service Account JSON file from env or workspace root."""
    env_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if env_path:
        resolved = env_path if os.path.isabs(env_path) else os.path.join(_BASE_DIR, env_path)
        if os.path.exists(resolved):
            return resolved

    patterns = [
        os.path.join(_BASE_DIR, "leads-data-*.json"),
        os.path.join(_BASE_DIR, "*serviceaccount*.json"),
        os.path.join(_BASE_DIR, "*credentials*.json"),
    ]
    for pattern in patterns:
        matches = glob.glob(pattern)
        if matches:
            return matches[0]

    return None


def get_authorized_session() -> Optional[AuthorizedSession]:
    """Creates an authenticated Google API session using Service Account credentials."""
    global _SESSION_CACHE, _SESSION_CACHE_TIME
    now = time.time()
    if _SESSION_CACHE is not None and (now - _SESSION_CACHE_TIME) < 1800:
        return _SESSION_CACHE

    creds_path = find_credentials_file()
    if not creds_path:
        logger.warning("No service account credentials JSON found.")
        return None

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive.readonly"
    ]
    try:
        creds = service_account.Credentials.from_service_account_file(creds_path, scopes=scopes)
        _SESSION_CACHE = AuthorizedSession(creds)
        _SESSION_CACHE_TIME = now
        return _SESSION_CACHE
    except Exception as e:
        logger.error(f"Failed to create authorized session: {e}")
        return None


def fetch_products_dataframe(force_refresh: bool = False) -> pd.DataFrame:
    """
    Fetches the live products catalog directly from Google Sheets/Drive with caching.
    """
    global _PRODUCTS_CACHE, _PRODUCTS_CACHE_TIME
    now = time.time()
    if not force_refresh and _PRODUCTS_CACHE is not None and (now - _PRODUCTS_CACHE_TIME) < CACHE_TTL:
        return _PRODUCTS_CACHE

    session = get_authorized_session()
    if not session:
        raise RuntimeError("Service account credentials not configured.")

    url = f"https://docs.google.com/spreadsheets/d/{PRODUCTS_SHEET_ID}/export?format=xlsx"
    resp = session.get(url)

    if resp.status_code == 200:
        df = pd.read_excel(io.BytesIO(resp.content))
        col_map = {col: col.strip() for col in df.columns}
        df.rename(columns=col_map, inplace=True)
        _PRODUCTS_CACHE = df
        _PRODUCTS_CACHE_TIME = now
        return df
    else:
        if _PRODUCTS_CACHE is not None:
            return _PRODUCTS_CACHE
        raise RuntimeError(f"Failed to fetch products from Google Sheets (HTTP {resp.status_code}): {resp.text}")


def fetch_orders(force_refresh: bool = False) -> List[Dict[str, Any]]:
    """
    Fetches live orders from the orders Google Sheet with caching.
    """
    global _ORDERS_CACHE, _ORDERS_CACHE_TIME
    now = time.time()
    if not force_refresh and _ORDERS_CACHE is not None and (now - _ORDERS_CACHE_TIME) < CACHE_TTL:
        return _ORDERS_CACHE

    session = get_authorized_session()
    if not session:
        return _load_local_orders()

    url = f"https://sheets.googleapis.com/v4/spreadsheets/{ORDERS_SHEET_ID}/values/Sheet1"
    try:
        resp = session.get(url)
        if resp.status_code == 200:
            data = resp.json()
            values = data.get("values", [])
            if not values:
                return []
            header = [str(h).strip() for h in values[0]]
            records = []
            for row_idx, row in enumerate(values[1:], start=2):
                item = {"_row_number": row_idx}
                for i, h in enumerate(header):
                    item[h] = row[i].strip() if i < len(row) else ""
                records.append(item)

            local_overrides = _load_local_orders_overrides()
            for rec in records:
                oid = rec.get("order_id")
                if oid and oid in local_overrides:
                    rec["Status"] = local_overrides[oid]

            _ORDERS_CACHE = records
            _ORDERS_CACHE_TIME = now
            return records
        else:
            logger.warning(f"Error fetching orders from Google Sheets: {resp.status_code}")
            return _load_local_orders()
    except Exception as ex:
        logger.error(f"Exception fetching orders: {ex}")
        return _load_local_orders()


def find_order(order_query: str) -> Optional[Dict[str, Any]]:
    """
    Finds an order by order_id (e.g. 'ORD-101') or customer name or product.
    """
    orders = fetch_orders()
    clean_q = order_query.strip().lower()
    
    # 1. Exact or partial match on order_id
    for o in orders:
        oid = str(o.get("order_id", "")).strip().lower()
        if clean_q == oid or (len(clean_q) >= 4 and clean_q in oid):
            return o

    # 2. Match on customer name
    for o in orders:
        cust = str(o.get("customer", "")).strip().lower()
        if clean_q in cust or cust in clean_q:
            return o

    return None


def get_next_order_id() -> str:
    """Generates the next sequential Order ID (e.g. ORD-110)."""
    orders = fetch_orders(force_refresh=True)
    max_num = 100
    for o in orders:
        oid = str(o.get("order_id", "")).strip().upper()
        match = re.search(r'ORD-(\d+)', oid)
        if match:
            try:
                num = int(match.group(1))
                if num > max_num:
                    max_num = num
            except ValueError:
                pass
    return f"ORD-{max_num + 1}"


def find_product_details_by_name(query_name: str) -> Dict[str, Any]:
    """Finds product details (Model Name, category, product, price, stock) from the live products catalog."""
    try:
        df = fetch_products_dataframe()
        if df is not None and not df.empty:
            q = str(query_name).strip().lower()

            # 1. Exact match on Model Name
            for _, row in df.iterrows():
                m = str(row.get("Model Name", "")).strip()
                if m.lower() == q:
                    cat = str(row.get("Category", "Laptop")).strip()
                    return {
                        "model_name": m,
                        "product": cat.lower(),
                        "category": "electronics",
                        "price": float(row.get("price", 0.0)),
                        "stock": int(row.get("stock", 0)) if pd.notna(row.get("stock")) else 0,
                        "brand": str(row.get("Brand", ""))
                    }

            # 2. Substring match
            for _, row in df.iterrows():
                m = str(row.get("Model Name", "")).strip()
                b = str(row.get("Brand", "")).strip()
                full_name = f"{b} {m}".lower()
                if q in full_name or m.lower() in q or q in m.lower():
                    cat = str(row.get("Category", "Laptop")).strip()
                    return {
                        "model_name": m,
                        "product": cat.lower(),
                        "category": "electronics",
                        "price": float(row.get("price", 0.0)),
                        "stock": int(row.get("stock", 0)) if pd.notna(row.get("stock")) else 0,
                        "brand": b
                    }
    except Exception as ex:
        logger.warning(f"Error looking up product details: {ex}")

    return {
        "model_name": query_name,
        "product": "electronics",
        "category": "electronics",
        "price": 0.0,
        "stock": 1,
        "brand": ""
    }


def create_new_order(
    customer: str,
    model_name: str,
    product: Optional[str] = None,
    category: Optional[str] = None,
    email: Optional[str] = None
) -> Dict[str, Any]:
    """
    Creates a new customer order and updates the live orders Google Sheet:
    Columns: order_id, customer, Model Name, product, category, days_ago, Status, Email
    """
    order_id = get_next_order_id()
    prod_info = find_product_details_by_name(model_name)
    resolved_model = prod_info.get("model_name") or model_name
    resolved_product = product or prod_info.get("product") or "laptop"
    resolved_category = category or prod_info.get("category") or "electronics"
    price = prod_info.get("price", 0.0)
    stock = prod_info.get("stock", 0)
    cust_email = str(email or "").strip()

    row_data = [
        str(order_id).strip(),
        str(customer).strip(),
        str(resolved_model).strip(),
        str(resolved_product).strip(),
        str(resolved_category).strip(),
        "0",
        "Order Placed",
        cust_email
    ]

    session = get_authorized_session()
    sheet_synced = False
    error_msg = None

    if session:
        append_url = f"https://sheets.googleapis.com/v4/spreadsheets/{ORDERS_SHEET_ID}/values/Sheet1!A:H:append?valueInputOption=USER_ENTERED"
        body = {"values": [row_data]}
        try:
            resp = session.post(append_url, json=body)
            if resp.status_code == 200:
                sheet_synced = True
            else:
                error_msg = f"HTTP {resp.status_code}: {resp.text}"
        except Exception as ex:
            error_msg = str(ex)

    # Invalidate cache so the new order appears immediately in live lookups
    clear_cache()

    return {
        "success": True,
        "sheet_synced": sheet_synced,
        "order_id": order_id,
        "customer": customer,
        "email": cust_email,
        "model_name": resolved_model,
        "product": resolved_product,
        "category": resolved_category,
        "days_ago": 0,
        "status": "Order Placed",
        "price": price,
        "stock": stock,
        "error": error_msg
    }


def evaluate_refund_eligibility(order: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluates refund eligibility according to TechMart Store Policy:
    - Policy: Electronics (laptops, phones, tablets, headphones, etc.) must be returned within 15 days.
    - Other items: 30 days.
    - Items marked as 'Final Sale' are ineligible.
    - If days_ago <= threshold -> ELIGIBLE.
    - If days_ago > threshold -> NOT ELIGIBLE.
    """
    order_id = order.get("order_id", "Unknown")
    customer = order.get("customer", "Customer")
    model_name = order.get("Model Name", order.get("product", "Item"))
    product = str(order.get("product", "")).lower()
    category = str(order.get("category", "")).lower()
    status = order.get("Status", "").strip()

    try:
        days_ago = int(float(order.get("days_ago", 0)))
    except (ValueError, TypeError):
        days_ago = 0

    # Determine product classification
    is_electronics = (
        "electronic" in category
        or any(k in product for k in ["laptop", "phone", "tablet", "headphone", "keyboard", "watch", "earbud", "macbook", "galaxy"])
        or any(k in model_name.lower() for k in ["laptop", "phone", "tablet", "macbook", "galaxy", "wh-", "xps"])
    )

    allowed_days = 15 if is_electronics else 30
    item_type_label = "Electronics (15-day policy)" if is_electronics else "General Merchandise (30-day policy)"

    # Check already approved
    if status.lower() in ["return approved", "refund approved", "refund processing", "refunded"]:
        return {
            "eligible": True,
            "already_approved": True,
            "order_id": order_id,
            "customer": customer,
            "model_name": model_name,
            "days_ago": days_ago,
            "allowed_days": allowed_days,
            "category": category,
            "status": status,
            "item_type": item_type_label,
            "message": f"Order {order_id} has already been approved for return/refund (Status: '{status}')."
        }

    if days_ago <= allowed_days:
        eligible = True
        message = (
            f"✅ Order **{order_id}** is **ELIGIBLE** for a refund!\n"
            f"- Customer: {customer}\n"
            f"- Product: {model_name}\n"
            f"- Order Age: {days_ago} days ago (within the {allowed_days}-day limit for {item_type_label}).\n"
            f"Please collect banking information to disburse the refund."
        )
    else:
        eligible = False
        message = (
            f"❌ Order **{order_id}** is **NOT ELIGIBLE** for a refund.\n"
            f"- Customer: {customer}\n"
            f"- Product: {model_name}\n"
            f"- Order Age: {days_ago} days ago, which exceeds the {allowed_days}-day limit for {item_type_label}.\n"
            f"Under store policy, returns cannot be accepted beyond this window."
        )

    return {
        "eligible": eligible,
        "already_approved": False,
        "order_id": order_id,
        "customer": customer,
        "model_name": model_name,
        "days_ago": days_ago,
        "allowed_days": allowed_days,
        "category": category,
        "status": status,
        "item_type": item_type_label,
        "message": message
    }


def fetch_bank_details(force_refresh: bool = False) -> List[Dict[str, Any]]:
    """Fetches submitted bank details from Google Sheets with caching."""
    global _BANK_CACHE, _BANK_CACHE_TIME
    now = time.time()
    if not force_refresh and _BANK_CACHE is not None and (now - _BANK_CACHE_TIME) < CACHE_TTL:
        return _BANK_CACHE

    session = get_authorized_session()
    records = []

    if session:
        url = f"https://sheets.googleapis.com/v4/spreadsheets/{BANK_DETAILS_SHEET_ID}/values/Sheet1"
        try:
            resp = session.get(url)
            if resp.status_code == 200:
                values = resp.json().get("values", [])
                if values:
                    header = [str(h).strip() for h in values[0]]
                    for row in values[1:]:
                        item = {}
                        for i, h in enumerate(header):
                            item[h] = row[i].strip() if i < len(row) else ""
                        records.append(item)
        except Exception as ex:
            logger.error(f"Error fetching bank details from sheets: {ex}")

    # Merge local backups if any are not yet in remote sheet
    local_records = _load_local_bank_details()
    existing_orders = {r.get("order_id") for r in records}
    for loc in local_records:
        if loc.get("order_id") not in existing_orders:
            records.append(loc)

    _BANK_CACHE = records
    _BANK_CACHE_TIME = now
    return records


def submit_bank_details(
    order_id: str,
    customer: str,
    product: str,
    bank_name: str,
    account_number: str,
    mobile_number: str
) -> Dict[str, Any]:
    """
    Submits banking information to the bank_details Google Sheet.
    Also updates order status to 'Return Approved'.
    Handles permission limitations gracefully by persisting locally if remote write is restricted.
    """
    clear_cache()
    session = get_authorized_session()
    sheet_synced = False
    status_updated = False
    error_msg = None

    row_data = [
        str(order_id).strip(),
        str(customer).strip(),
        str(product).strip(),
        str(bank_name).strip(),
        str(account_number).strip(),
        str(mobile_number).strip()
    ]

    # 1. Try appending to Google Sheet
    if session:
        append_url = f"https://sheets.googleapis.com/v4/spreadsheets/{BANK_DETAILS_SHEET_ID}/values/Sheet1!A:F:append?valueInputOption=USER_ENTERED"
        body = {"values": [row_data]}
        try:
            resp = session.post(append_url, json=body)
            if resp.status_code == 200:
                sheet_synced = True
            elif resp.status_code == 403:
                error_msg = "Google Sheets service account has 'Viewer' access. (Grant 'Editor' to ai-agent@leads-data-509913.iam.gserviceaccount.com to auto-sync to cloud)."
            else:
                error_msg = f"HTTP {resp.status_code}: {resp.text}"
        except Exception as ex:
            error_msg = str(ex)

    # 2. Always persist to local backup for data durability
    _save_local_bank_detail({
        "order_id": order_id,
        "customer": customer,
        "product": product,
        "Bank_Name": bank_name,
        "Account Number": account_number,
        "Mobile Number": mobile_number,
        "_cloud_synced": sheet_synced
    })

    # 3. Update order status in orders sheet
    update_res = update_order_status(order_id, "Return Approved")
    status_updated = update_res.get("success", False)

    return {
        "success": True,
        "sheet_synced": sheet_synced,
        "status_updated": status_updated,
        "notice": error_msg,
        "record": {
            "order_id": order_id,
            "customer": customer,
            "product": product,
            "bank_name": bank_name,
            "account_number": account_number,
            "mobile_number": mobile_number
        }
    }


def update_order_status(order_id: str, new_status: str = "Return Approved") -> Dict[str, Any]:
    """Updates order status in orders sheet (or records local override)."""
    orders = fetch_orders()
    target_row = None
    for o in orders:
        if str(o.get("order_id", "")).strip().lower() == str(order_id).strip().lower():
            target_row = o
            break

    # Record local override
    _save_local_order_override(order_id, new_status)

    session = get_authorized_session()
    if session and target_row and "_row_number" in target_row:
        row_num = target_row["_row_number"]
        # Column G is Status in Sheet1!G{row_num}
        url = f"https://sheets.googleapis.com/v4/spreadsheets/{ORDERS_SHEET_ID}/values/Sheet1!G{row_num}?valueInputOption=USER_ENTERED"
        try:
            resp = session.put(url, json={"values": [[new_status]]})
            if resp.status_code == 200:
                return {"success": True, "cloud_synced": True}
        except Exception:
            pass

    return {"success": True, "cloud_synced": False}


# -------------------------------------------------------------
# Local Storage Helpers (Fallback & Persistence)
# -------------------------------------------------------------
def _load_local_orders() -> List[Dict[str, Any]]:
    extracted_path = os.path.join(_BASE_DIR, "extracted_sheet_data.json")
    if os.path.exists(extracted_path):
        try:
            with open(extracted_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                rows = data.get("rows", [])
                if rows:
                    header = rows[0]
                    records = []
                    for r_idx, r in enumerate(rows[1:], start=2):
                        item = {"_row_number": r_idx}
                        for i, h in enumerate(header):
                            item[h] = r[i] if i < len(r) else ""
                        records.append(item)
                    return records
        except Exception:
            pass
    return []


def _load_local_orders_overrides() -> Dict[str, str]:
    if os.path.exists(LOCAL_BACKUP_ORDERS_FILE):
        try:
            with open(LOCAL_BACKUP_ORDERS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_local_order_override(order_id: str, status: str):
    overrides = _load_local_orders_overrides()
    overrides[order_id] = status
    with open(LOCAL_BACKUP_ORDERS_FILE, "w", encoding="utf-8") as f:
        json.dump(overrides, f, indent=2)


def _load_local_bank_details() -> List[Dict[str, Any]]:
    if os.path.exists(LOCAL_BACKUP_BANK_FILE):
        try:
            with open(LOCAL_BACKUP_BANK_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []


def _save_local_bank_detail(record: Dict[str, Any]):
    existing = _load_local_bank_details()
    # Check if duplicate
    found = False
    for i, r in enumerate(existing):
        if r.get("order_id") == record.get("order_id"):
            existing[i] = record
            found = True
            break
    if not found:
        existing.append(record)

    with open(LOCAL_BACKUP_BANK_FILE, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2)


def get_service_account_email() -> str:
    """Returns the client email for the Google Service Account."""
    creds_path = find_credentials_file()
    if creds_path and os.path.exists(creds_path):
        try:
            with open(creds_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("client_email", "ai-agent@leads-data-509913.iam.gserviceaccount.com")
        except Exception:
            pass
    return "ai-agent@leads-data-509913.iam.gserviceaccount.com"


def get_pending_bank_details() -> List[Dict[str, Any]]:
    """Returns local bank details that have not yet been synced to Google Sheets."""
    local_records = _load_local_bank_details()
    return [r for r in local_records if not r.get("_cloud_synced", False)]


def sync_pending_bank_details() -> Dict[str, Any]:
    """
    Attempts to sync all pending local bank details to the Google Sheet.
    Call this when the user grants 'Editor' permission to the service account.
    """
    session = get_authorized_session()
    if not session:
        return {"success": False, "synced": 0, "remaining": 0, "error": "No service account session available."}

    local_records = _load_local_bank_details()
    unsynced_indices = [i for i, r in enumerate(local_records) if not r.get("_cloud_synced", False)]

    if not unsynced_indices:
        return {"success": True, "synced": 0, "remaining": 0, "message": "All bank details are already synced to Google Sheets."}

    synced_count = 0
    error_msg = None
    client_email = get_service_account_email()

    for idx in unsynced_indices:
        rec = local_records[idx]
        row_data = [
            str(rec.get("order_id", "")).strip(),
            str(rec.get("customer", "")).strip(),
            str(rec.get("product", "")).strip(),
            str(rec.get("Bank_Name", "")).strip(),
            str(rec.get("Account Number", "")).strip(),
            str(rec.get("Mobile Number", "")).strip()
        ]
        append_url = f"https://sheets.googleapis.com/v4/spreadsheets/{BANK_DETAILS_SHEET_ID}/values/Sheet1!A:F:append?valueInputOption=USER_ENTERED"
        try:
            resp = session.post(append_url, json={"values": [row_data]})
            if resp.status_code == 200:
                rec["_cloud_synced"] = True
                synced_count += 1
                # Try updating order status as well
                update_order_status(rec.get("order_id"), "Return Approved")
            elif resp.status_code == 403:
                error_msg = f"Permission Denied (HTTP 403): Service account {client_email} only has 'Viewer' permission. Please change to 'Editor' in Google Sheets Share settings."
                break
            else:
                error_msg = f"HTTP {resp.status_code}: {resp.text}"
                break
        except Exception as ex:
            error_msg = str(ex)
            break

    # Persist updated flags
    with open(LOCAL_BACKUP_BANK_FILE, "w", encoding="utf-8") as f:
        json.dump(local_records, f, indent=2)

    remaining = len([r for r in local_records if not r.get("_cloud_synced", False)])
    clear_cache()
    return {
        "success": synced_count > 0 or remaining == 0,
        "synced": synced_count,
        "remaining": remaining,
        "error": error_msg
    }

