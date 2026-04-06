
#created with love by Sidhant Chaku

import streamlit as st
import pandas as pd
import plotly.express as px
import google.generativeai as genai
import json
from datetime import datetime
from statistics import NormalDist
from urllib import request, error
from prophet import Prophet
from prophet.plot import plot_plotly
import plotly.io as pio
from streamlit_option_menu import option_menu

from integrations import (
    fetch_erp_api_inventory,
    fetch_erp_csv_inventory,
    fetch_google_sheets_inventory,
    fetch_shopify_inventory,
    fetch_woocommerce_inventory,
)
from persistence import (
    authenticate_user,
    create_user,
    get_engine,
    init_db,
    list_workspaces,
    load_latest_dataset,
    load_latest_mapping,
    save_column_mapping,
    save_dataset_snapshot,
    save_feedback,
    save_plan,
    seed_default_users,
)


# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="StockPilot AI",
    page_icon="🛰️",
    layout="wide"
)

# --- GLOBAL CSS & BRANDING ---
pio.templates.default = "plotly_dark"

st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;500;700;900&family=Space+Grotesk:wght@400;600;700&display=swap');
  :root {
    --bg: #070b1a;
    --bg2: #0f1430;
    --fg: #f6fbff;
    --card-bg: rgba(16, 28, 68, 0.74);
    --stroke: rgba(145, 202, 255, 0.28);
    --primary: #00e5ff;
    --accent: #ff5ea8;
    --lime: #9dff5f;
  }
  .stApp {
    font-family: 'Outfit', sans-serif;
    color: var(--fg);
    background:
      radial-gradient(1100px 620px at 8% -12%, rgba(0,229,255,0.22), transparent 60%),
      radial-gradient(900px 520px at 95% -15%, rgba(255,94,168,0.21), transparent 58%),
      linear-gradient(145deg, var(--bg) 0%, var(--bg2) 100%);
  }
  .main .block-container { padding-top: 1.0rem; }
  [data-testid="stSidebar"] {
    background: linear-gradient(190deg, rgba(12,24,62,0.93), rgba(10,17,46,0.92));
    border-right: 1px solid rgba(124,162,255,0.23);
  }
  [data-testid="stSidebar"] * { font-family: 'Space Grotesk', sans-serif; }

  .stockpilot-hero {
    position: relative;
    overflow: hidden;
    border: 1px solid var(--stroke);
    border-radius: 22px;
    padding: 1rem 1.3rem 1.2rem;
    background: linear-gradient(115deg, rgba(8,26,64,0.78), rgba(53,14,70,0.62));
    box-shadow: 0 20px 50px rgba(0, 0, 0, 0.36), inset 0 0 0 1px rgba(255,255,255,0.03);
    margin-bottom: 1rem;
  }
  .stockpilot-hero:before {
    content: "";
    position: absolute;
    width: 220px;
    height: 220px;
    right: -70px;
    top: -80px;
    background: radial-gradient(circle, rgba(0,229,255,0.42), rgba(0,229,255,0.02) 64%);
    filter: blur(2px);
  }
  .stockpilot-title {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 2rem;
    font-weight: 700;
    line-height: 1.1;
    letter-spacing: 0.25px;
    margin: 0 0 0.35rem;
    color: #ecf9ff;
  }
  .stockpilot-chip {
    display: inline-flex;
    gap: 0.45rem;
    align-items: center;
    border: 1px solid rgba(0,229,255,0.4);
    padding: 0.16rem 0.62rem;
    border-radius: 999px;
    font-size: 0.74rem;
    font-weight: 600;
    color: #b0f5ff;
    background: rgba(0,229,255,0.08);
    margin-right: 0.45rem;
  }
  .stockpilot-sub { margin: 0.35rem 0 0; opacity: 0.88; font-size: 0.93rem; }

  .metric-card {
    position: relative;
    background: linear-gradient(145deg, rgba(19, 35, 82, 0.72), rgba(14, 25, 61, 0.72));
    border: 1px solid rgba(149, 196, 255, 0.25);
    padding: 1rem;
    border-radius: 16px;
    margin-bottom: 1rem;
    box-shadow: inset 0 0 0 1px rgba(255,255,255,0.02), 0 14px 34px rgba(4, 8, 24, 0.42);
  }
  .metric-card h4 { margin:0; font-size:0.8rem; color:#8ec9ff; text-transform: uppercase; letter-spacing:0.05em; }
  .metric-card p  { margin:.28rem 0 0; font-size:1.58rem; color:var(--fg); font-weight:700; }

  div[data-baseweb="select"] > div,
  .stTextInput > div > div,
  .stNumberInput > div > div,
  .stTextArea textarea {
    background: rgba(12, 22, 55, 0.68) !important;
    border: 1px solid rgba(122, 180, 255, 0.35) !important;
    border-radius: 12px !important;
  }
  .stButton > button {
    border: none !important;
    color: #041323 !important;
    background: linear-gradient(95deg, var(--primary), #7dfce4) !important;
    border-radius: 999px !important;
    font-weight: 700 !important;
    letter-spacing: 0.02em !important;
    box-shadow: 0 8px 20px rgba(0,229,255,0.26) !important;
  }
  .stDownloadButton > button {
    border-radius: 12px !important;
    border: 1px solid rgba(157, 255, 95, 0.32) !important;
    background: linear-gradient(95deg, rgba(157,255,95,0.15), rgba(0,229,255,0.15)) !important;
    color: #d9ffe3 !important;
  }
  .stAlert {
    border-radius: 12px !important;
    border: 1px solid rgba(144, 186, 255, 0.24) !important;
  }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="stockpilot-hero">
  <div class="stockpilot-title">StockPilot AI</div>
  <span class="stockpilot-chip">Realtime Ops Intelligence</span>
  <span class="stockpilot-chip">Demand + Last-Mile + Alerts</span>
  <p class="stockpilot-sub">Modern inventory command center for deadstock control, demand planning, and transfer optimization.</p>
</div>
""", unsafe_allow_html=True)

# --- SIDEBAR: SETUP + NAVIGATION ---
def show_metric_card(col, title, val, suffix=""):
  col.markdown(f"""
    <div class="metric-card">
      <h4>{title}</h4>
      <p>{val}{suffix}</p>
    </div>
  """, unsafe_allow_html=True)

ROLE_PAGE_ACCESS = {
    "ops": {"Dashboard", "Area Charts", "Forecast", "Last-Mile", "Deadstock", "Restock", "Alerts"},
    "manager": {"Dashboard", "Area Charts", "Forecast", "Last-Mile", "Deadstock", "Restock", "Alerts"},
    "admin": {"Dashboard", "Area Charts", "Forecast", "Last-Mile", "Deadstock", "Restock", "Alerts", "Admin"},
}
ROLE_INTEGRATIONS = {"manager", "admin"}

engine = get_engine()
try:
    init_db(engine)
except Exception:
    # Streamlit Cloud can fail on non-writable paths or invalid DB URLs.
    engine = get_engine("sqlite:////tmp/stockpilot.db")
    init_db(engine)
    st.warning(
        "Primary database unavailable. Running on temporary local storage. "
        "Set a valid DATABASE_URL in Streamlit secrets for persistent data."
    )
seed_default_users(engine)

st.session_state.setdefault("auth_user", None)
st.session_state.setdefault("active_workspace", "global")
st.session_state.setdefault("loaded_df", None)
st.session_state.setdefault("loaded_dataset_id", None)
st.session_state.setdefault("loaded_source_type", "")
st.session_state.setdefault("loaded_source_name", "")
st.session_state.setdefault("gemini_ready", False)

@st.cache_data
def load_data(uploaded_file):
    name = uploaded_file.name.lower()
    if name.endswith(".csv"):
        return pd.read_csv(uploaded_file)
    elif name.endswith((".xls","xlsx")):
        return pd.read_excel(uploaded_file)
    else:
        return None


if not st.session_state["auth_user"]:
    st.markdown("""
    <div class="stockpilot-hero">
      <div class="stockpilot-title">Welcome to StockPilot AI</div>
      <span class="stockpilot-chip">Role-Based Access</span>
      <span class="stockpilot-chip">Workspace Aware</span>
      <p class="stockpilot-sub">Sign in to access your team's inventory workspace.</p>
    </div>
    """, unsafe_allow_html=True)
    with st.form("login_form", clear_on_submit=False):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        login_submit = st.form_submit_button("Login")
        if login_submit:
            user = authenticate_user(engine, username.strip(), password)
            if user:
                st.session_state["auth_user"] = user
                st.session_state["active_workspace"] = user["workspace"]
                st.rerun()
            else:
                st.error("Invalid credentials.")
    st.info("Demo users: admin/admin123, manager/manager123, ops/ops123")
    st.stop()

current_user = st.session_state["auth_user"]
current_role = current_user["role"]
current_username = current_user["username"]
page = "Dashboard"

with st.sidebar:
    st.markdown("## 🛰️ Mission Control")
    st.caption(f"User: `{current_username}` ({current_role})")

    if current_role in {"manager", "admin"}:
        workspaces = list_workspaces(engine)
        if st.session_state["active_workspace"] not in workspaces:
            workspaces.append(st.session_state["active_workspace"])
        st.session_state["active_workspace"] = st.selectbox(
            "Workspace",
            sorted(set(workspaces)),
            index=sorted(set(workspaces)).index(st.session_state["active_workspace"]),
        )
    else:
        st.session_state["active_workspace"] = current_user["workspace"]
        st.caption(f"Workspace: `{st.session_state['active_workspace']}`")

    if st.button("Logout", use_container_width=True):
        st.session_state["auth_user"] = None
        st.session_state["loaded_df"] = None
        st.session_state["loaded_dataset_id"] = None
        st.rerun()

    if current_role == "admin":
        st.markdown("### 👥 User Admin")
        with st.form("create_user_form", clear_on_submit=True):
            new_user = st.text_input("New Username")
            new_pass = st.text_input("New Password", type="password")
            new_role = st.selectbox("Role", ["ops", "manager", "admin"])
            new_workspace = st.text_input("Workspace", value=st.session_state["active_workspace"])
            create_submit = st.form_submit_button("Create User", use_container_width=True)
        if create_submit:
            ok, msg = create_user(engine, new_user, new_pass, new_role, new_workspace)
            if ok:
                st.success(msg)
            else:
                st.error(msg)

    st.markdown("---")
    api_key = st.text_input("🔑 Gemini API Key", type="password")
    if api_key:
        try:
            genai.configure(api_key=api_key)
            st.session_state["gemini_ready"] = True
        except Exception as e:
            st.session_state["gemini_ready"] = False
            st.error(f"Gemini setup failed: {e}")
    else:
        st.session_state["gemini_ready"] = False

    st.markdown("### 📡 Data Source")
    source_options = ["Upload File", "Saved Snapshot"]
    if current_role in ROLE_INTEGRATIONS:
        source_options += ["Shopify", "WooCommerce", "Google Sheets", "ERP API", "ERP CSV URL"]
    source_type = st.selectbox("Source", source_options)

    if source_type == "Upload File":
        upload = st.file_uploader("Inventory File", type=["csv", "xlsx", "xls"], key="upload_source_file")
        if upload is not None:
            uploaded_df = load_data(upload)
            if uploaded_df is not None:
                st.session_state["loaded_df"] = uploaded_df
                st.session_state["loaded_dataset_id"] = None
                st.session_state["loaded_source_type"] = "upload"
                st.session_state["loaded_source_name"] = upload.name
            else:
                st.error("Unsupported file format.")
    elif source_type == "Saved Snapshot":
        if st.button("Load Latest Workspace Snapshot", use_container_width=True):
            data, meta = load_latest_dataset(engine, st.session_state["active_workspace"])
            if data is not None:
                st.session_state["loaded_df"] = data
                st.session_state["loaded_dataset_id"] = meta["id"]
                st.session_state["loaded_source_type"] = meta["source_type"]
                st.session_state["loaded_source_name"] = meta["source_name"]
                st.success(f"Loaded snapshot: {meta['source_name']}")
            else:
                st.info("No saved dataset found for this workspace.")
    elif source_type == "Shopify":
        shop_domain = st.text_input("Store Domain", placeholder="your-store.myshopify.com")
        shop_token = st.text_input("Access Token", type="password")
        if st.button("Fetch Shopify Data", use_container_width=True):
            try:
                data = fetch_shopify_inventory(shop_domain, shop_token)
                st.session_state["loaded_df"] = data
                st.session_state["loaded_dataset_id"] = None
                st.session_state["loaded_source_type"] = "shopify"
                st.session_state["loaded_source_name"] = shop_domain
                st.success(f"Fetched {len(data)} rows from Shopify.")
            except Exception as e:
                st.error(f"Shopify fetch failed: {e}")
    elif source_type == "WooCommerce":
        woo_url = st.text_input("Store URL", placeholder="https://yourstore.com")
        woo_key = st.text_input("Consumer Key")
        woo_secret = st.text_input("Consumer Secret", type="password")
        if st.button("Fetch WooCommerce Data", use_container_width=True):
            try:
                data = fetch_woocommerce_inventory(woo_url, woo_key, woo_secret)
                st.session_state["loaded_df"] = data
                st.session_state["loaded_dataset_id"] = None
                st.session_state["loaded_source_type"] = "woocommerce"
                st.session_state["loaded_source_name"] = woo_url
                st.success(f"Fetched {len(data)} rows from WooCommerce.")
            except Exception as e:
                st.error(f"WooCommerce fetch failed: {e}")
    elif source_type == "Google Sheets":
        sheet_input = st.text_input("Google Sheet URL or CSV Link")
        if st.button("Fetch Sheet Data", use_container_width=True):
            try:
                data = fetch_google_sheets_inventory(sheet_input)
                st.session_state["loaded_df"] = data
                st.session_state["loaded_dataset_id"] = None
                st.session_state["loaded_source_type"] = "google_sheets"
                st.session_state["loaded_source_name"] = "Google Sheets"
                st.success(f"Fetched {len(data)} rows from Google Sheets.")
            except Exception as e:
                st.error(f"Google Sheets fetch failed: {e}")
    elif source_type == "ERP API":
        erp_api_url = st.text_input("ERP API URL")
        erp_bearer = st.text_input("Bearer Token (optional)", type="password")
        if st.button("Fetch ERP API Data", use_container_width=True):
            try:
                data = fetch_erp_api_inventory(erp_api_url, erp_bearer)
                st.session_state["loaded_df"] = data
                st.session_state["loaded_dataset_id"] = None
                st.session_state["loaded_source_type"] = "erp_api"
                st.session_state["loaded_source_name"] = erp_api_url
                st.success(f"Fetched {len(data)} rows from ERP API.")
            except Exception as e:
                st.error(f"ERP API fetch failed: {e}")
    elif source_type == "ERP CSV URL":
        erp_csv_url = st.text_input("ERP CSV URL")
        if st.button("Fetch ERP CSV Data", use_container_width=True):
            try:
                data = fetch_erp_csv_inventory(erp_csv_url)
                st.session_state["loaded_df"] = data
                st.session_state["loaded_dataset_id"] = None
                st.session_state["loaded_source_type"] = "erp_csv"
                st.session_state["loaded_source_name"] = erp_csv_url
                st.success(f"Fetched {len(data)} rows from ERP CSV.")
            except Exception as e:
                st.error(f"ERP CSV fetch failed: {e}")

    if st.session_state["loaded_df"] is not None:
        st.caption(
            f"Active Dataset: {st.session_state.get('loaded_source_name', 'untitled')} "
            f"({len(st.session_state['loaded_df'])} rows)"
        )
        if st.button("💾 Save Dataset Snapshot", use_container_width=True):
            dataset_id = save_dataset_snapshot(
                engine=engine,
                workspace=st.session_state["active_workspace"],
                source_type=st.session_state.get("loaded_source_type", "unknown"),
                source_name=st.session_state.get("loaded_source_name", "dataset"),
                dataframe=st.session_state["loaded_df"],
                created_by=current_username,
            )
            st.session_state["loaded_dataset_id"] = dataset_id
            st.success(f"Saved snapshot #{dataset_id}.")


# Load active DataFrame
df = st.session_state.get("loaded_df")
if df is None:
    st.info("Load a dataset from the sidebar to continue.")
    st.stop()
raw_df = df.copy()

def build_sample_template():
    today = datetime.now().date().isoformat()
    return pd.DataFrame([
        {
            "Product": "SKU-1001",
            "Quantity": 120,
            "Unit Price": 19.99,
            "Area/Location": "Mumbai West Hub",
            "Last Sale Date": today,
            "Latitude": 19.0760,
            "Longitude": 72.8777,
        },
        {
            "Product": "SKU-1002",
            "Quantity": 75,
            "Unit Price": 34.50,
            "Area/Location": "Bengaluru South Hub",
            "Last Sale Date": today,
            "Latitude": 12.9716,
            "Longitude": 77.5946,
        },
    ])

def count_iqr_outliers(series: pd.Series) -> int:
    clean = pd.to_numeric(series, errors="coerce").dropna()
    if clean.empty:
        return 0
    q1 = clean.quantile(0.25)
    q3 = clean.quantile(0.75)
    iqr = q3 - q1
    if iqr == 0:
        return 0
    low = q1 - 1.5 * iqr
    high = q3 + 1.5 * iqr
    return int(((clean < low) | (clean > high)).sum())

def build_data_quality_report(
    raw_df: pd.DataFrame,
    prod_col: str,
    qty_col: str,
    price_col: str,
    area_col: str,
    date_col: str,
    lat_col: str,
    lon_col: str,
) -> pd.DataFrame:
    report = []

    def add_issue(check_name, severity, affected_rows, detail):
        if affected_rows > 0:
            report.append(
                {
                    "Check": check_name,
                    "Severity": severity,
                    "AffectedRows": int(affected_rows),
                    "Detail": detail,
                }
            )

    check_cols = [prod_col, qty_col, price_col, area_col]
    optional_cols = [date_col, lat_col, lon_col]
    for col in optional_cols:
        if col != "–":
            check_cols.append(col)

    for col in check_cols:
        missing = raw_df[col].isna().sum()
        add_issue("Missing Values", "Medium", missing, f"Column '{col}' has blank/null rows.")

    invalid_qty = pd.to_numeric(raw_df[qty_col], errors="coerce").isna().sum()
    invalid_price = pd.to_numeric(raw_df[price_col], errors="coerce").isna().sum()
    add_issue("Invalid Quantity", "High", invalid_qty, f"Column '{qty_col}' has non-numeric values.")
    add_issue("Invalid Unit Price", "High", invalid_price, f"Column '{price_col}' has non-numeric values.")

    dup_keys = [prod_col, area_col]
    if date_col != "–":
        dup_keys.append(date_col)
    duplicate_rows = raw_df.duplicated(subset=dup_keys).sum()
    add_issue("Duplicate Rows", "Medium", duplicate_rows, f"Duplicates found on keys: {', '.join(dup_keys)}.")

    qty_outliers = count_iqr_outliers(raw_df[qty_col])
    price_outliers = count_iqr_outliers(raw_df[price_col])
    add_issue("Quantity Outliers", "Low", qty_outliers, f"Potential IQR outliers in '{qty_col}'.")
    add_issue("Price Outliers", "Low", price_outliers, f"Potential IQR outliers in '{price_col}'.")

    if date_col != "–":
        parsed_dates = pd.to_datetime(raw_df[date_col], errors="coerce")
        invalid_dates = parsed_dates.isna().sum()
        future_dates = (parsed_dates > pd.Timestamp.now()).sum()
        add_issue("Invalid Dates", "High", invalid_dates, f"Column '{date_col}' has unparseable values.")
        add_issue("Future Dates", "Low", future_dates, f"Column '{date_col}' contains future timestamps.")

    if lat_col != "–":
        invalid_lat = pd.to_numeric(raw_df[lat_col], errors="coerce").isna().sum()
        add_issue("Invalid Latitude", "Medium", invalid_lat, f"Column '{lat_col}' has non-numeric values.")
    if lon_col != "–":
        invalid_lon = pd.to_numeric(raw_df[lon_col], errors="coerce").isna().sum()
        add_issue("Invalid Longitude", "Medium", invalid_lon, f"Column '{lon_col}' has non-numeric values.")

    return pd.DataFrame(report)

def pick_default_index(options, keywords, fallback, preferred=None):
    """Pick a safe default selectbox index from column keywords."""
    if preferred in options:
        return options.index(preferred)
    lowered = [str(opt).strip().lower() for opt in options]
    for idx, opt in enumerate(lowered):
        if idx == 0:
            continue
        if any(keyword in opt for keyword in keywords):
            return idx
    return min(fallback, len(options) - 1)


saved_mapping = {}
saved_mapping_payload = load_latest_mapping(engine, st.session_state["active_workspace"])
if saved_mapping_payload:
    try:
        saved_mapping = json.loads(saved_mapping_payload)
    except Exception:
        saved_mapping = {}

# --- COLUMN MAPPING ---
with st.expander("✏️ Map Columns", expanded=False):
    cols = ["–"] + list(df.columns)
    prod_col  = st.selectbox(
        "Product ▶", cols,
        index=pick_default_index(
            cols,
            ["product", "sku", "item", "name"],
            fallback=1,
            preferred=saved_mapping.get("prod_col"),
        ),
    )
    qty_col   = st.selectbox(
        "Quantity ▶", cols,
        index=pick_default_index(
            cols,
            ["qty", "quantity", "stock", "units"],
            fallback=2,
            preferred=saved_mapping.get("qty_col"),
        ),
    )
    price_col = st.selectbox(
        "Unit Price ▶", cols,
        index=pick_default_index(
            cols,
            ["unit price", "price", "rate", "cost"],
            fallback=3,
            preferred=saved_mapping.get("price_col"),
        ),
    )
    area_col  = st.selectbox(
        "Area/Location ▶", cols,
        index=pick_default_index(
            cols,
            ["area", "location", "city", "warehouse", "zone"],
            fallback=4,
            preferred=saved_mapping.get("area_col"),
        ),
    )
    date_col  = st.selectbox(
        "Last Sale Date ▶", cols,
        index=pick_default_index(
            cols,
            ["last sale", "sale date", "date", "sold"],
            fallback=5,
            preferred=saved_mapping.get("date_col"),
        ),
    )
    lat_col = st.selectbox(
        "Latitude (optional)", cols,
        index=pick_default_index(
            cols,
            ["latitude", "lat"],
            fallback=0,
            preferred=saved_mapping.get("lat_col"),
        ),
        help="If you have geo-coordinates"
    )
    lon_col = st.selectbox(
        "Longitude (optional)", cols,
        index=pick_default_index(
            cols,
            ["longitude", "lng", "lon"],
            fallback=0,
            preferred=saved_mapping.get("lon_col"),
        ),
        help="If you have geo-coordinates"
    )
    mapping_payload = {
        "prod_col": prod_col,
        "qty_col": qty_col,
        "price_col": price_col,
        "area_col": area_col,
        "date_col": date_col,
        "lat_col": lat_col,
        "lon_col": lon_col,
    }
    if st.button("💾 Save Column Mapping", key="save_mapping_btn"):
        mapping_id = save_column_mapping(
            engine=engine,
            workspace=st.session_state["active_workspace"],
            dataset_id=st.session_state.get("loaded_dataset_id"),
            mapping_json=json.dumps(mapping_payload),
            created_by=current_username,
        )
        st.success(f"Column mapping saved (#{mapping_id}).")

# --- NAVIGATION PILL MENU ---
if df is not None:
    available_options = [p for p in ["Dashboard", "Area Charts", "Forecast", "Last-Mile", "Deadstock", "Restock", "Alerts", "Admin"] if p in ROLE_PAGE_ACCESS.get(current_role, set())]
    available_icons = {
        "Dashboard": "bar-chart",
        "Area Charts": "geo-alt",
        "Forecast": "graph-up",
        "Last-Mile": "truck",
        "Deadstock": "file-earmark-excel",
        "Restock": "lightbulb",
        "Alerts": "bell",
        "Admin": "shield-lock",
    }
    page = option_menu(
        menu_title=None,
        options=available_options,
        icons=[available_icons[p] for p in available_options],
        default_index=0,
        orientation="horizontal",
        styles={
            "container": {"padding": "0!important", "background": "var(--card-bg)"},
            "nav-link": {
                "font-size": "0.98rem",
                "color": "var(--fg)",
                "padding": "0.58rem 1.05rem",
                "margin": "0 0.22rem",
                "border-radius": "10px",
            },
            "nav-link-selected": {"background-color": "var(--primary)", "color": "#041323"},
        },
    )
    
required = [prod_col, qty_col, price_col, area_col]
if "–" in required:
    st.error("🔴 Please map all required columns.")
    st.stop()

# --- DATA QUALITY GUARDRAIL ---
quality_df = build_data_quality_report(
    raw_df=raw_df,
    prod_col=prod_col,
    qty_col=qty_col,
    price_col=price_col,
    area_col=area_col,
    date_col=date_col,
    lat_col=lat_col,
    lon_col=lon_col,
)
with st.expander("🧪 Data Quality Guardrail", expanded=False):
    st.caption("Run quality checks before planning and forecasting.")
    template_csv = build_sample_template().to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇️ Download Sample CSV Template",
        data=template_csv,
        file_name="inventory_sample_template.csv",
        mime="text/csv",
    )

    if quality_df.empty:
        st.success("No major data-quality issues detected.")
    else:
        high_count = (quality_df["Severity"] == "High").sum()
        med_count = (quality_df["Severity"] == "Medium").sum()
        st.warning(f"Detected {len(quality_df)} issue type(s): {high_count} high, {med_count} medium.")
        st.dataframe(quality_df, use_container_width=True, hide_index=True)

# --- PREPROCESSING ---
df[qty_col]   = pd.to_numeric(df[qty_col], errors="coerce").fillna(0)
df[price_col] = pd.to_numeric(df[price_col], errors="coerce").fillna(0)
df["TotalValue"] = df[qty_col] * df[price_col]
if date_col != "–":
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    dropped_invalid_dates = int(df[date_col].isna().sum())
    df = df.dropna(subset=[date_col])
    df["DaysSinceSale"] = (datetime.now() - df[date_col]).dt.days
    if dropped_invalid_dates > 0:
        st.info(f"Dropped {dropped_invalid_dates} row(s) with invalid '{date_col}' values during preprocessing.")

# --- UTIL: Gemini Prompt Wrapper ---
def get_gemini(text_prompt: str) -> str:
    if not st.session_state.get("gemini_ready"):
        return "Gemini API key is not configured. Add it in the sidebar to enable AI analysis."
    try:
        model = genai.GenerativeModel("gemini-2.0-flash")
        return model.generate_content(text_prompt).text
    except Exception as e:
        return f"💥 Gemini API Error: {e}"
    
@st.cache_data
def forecast_prophet(
    df,
    ds_col,
    y_col,
    periods=30,
    daily_seasonality=True,
    weekly_seasonality=True,
    yearly_seasonality=True,
):
    ts = df[[ds_col, y_col]].rename(columns={ds_col: "ds", y_col: "y"}).copy()
    ts["ds"] = pd.to_datetime(ts["ds"], errors="coerce")
    ts["y"] = pd.to_numeric(ts["y"], errors="coerce")
    ts = ts.dropna(subset=["ds", "y"]).sort_values("ds")
    if ts["ds"].nunique() < 2:
        raise ValueError("Need at least two time points for forecasting.")

    m = Prophet(
        daily_seasonality=daily_seasonality,
        weekly_seasonality=weekly_seasonality,
        yearly_seasonality=yearly_seasonality,
    )
    m.fit(ts)
    future = m.make_future_dataframe(periods=periods)
    fc = m.predict(future)
    return m, fc

from geopy.geocoders import Nominatim
import math

@st.cache_data
def geocode_areas(area_list):
    """Resolve area names into lat/lon via Nominatim (OpenStreetMap)."""
    geolocator = Nominatim(user_agent="last-mile-app", timeout=10)
    records = []
    for area in area_list:
        try:
            loc = geolocator.geocode(area)
            if loc:
                records.append({
                    "area": area,
                    "lat": loc.latitude,
                    "lon": loc.longitude
                })
        except Exception:
            continue
    return pd.DataFrame(records)

def haversine(lat1, lon1, lat2, lon2):
    """Compute distance (miles) between two lat/lon points."""
    R = 3958.8  # Earth radius in miles
    φ1, φ2 = math.radians(lat1), math.radians(lat2)
    Δφ = math.radians(lat2 - lat1)
    Δλ = math.radians(lon2 - lon1)
    a = math.sin(Δφ/2)**2 + math.cos(φ1)*math.cos(φ2)*math.sin(Δλ/2)**2
    c = 2*math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

def optimize_transfer_plan(
    geo_df: pd.DataFrame,
    area_col: str,
    mode_profiles: dict,
    mode_strategy: str,
    weight_cost: float,
    weight_co2: float,
    weight_risk: float,
    max_total_cost: float | None,
    max_total_co2: float | None,
    max_qty_per_route: int,
    min_fill_ratio: float,
):
    modes = list(mode_profiles.keys()) if mode_strategy == "Auto (Best Mix)" else [mode_strategy]

    surplus_df = geo_df[geo_df["SurplusDeficit"] > 0].copy()
    deficit_df = geo_df[geo_df["SurplusDeficit"] < 0].copy()
    if surplus_df.empty or deficit_df.empty:
        return pd.DataFrame(), pd.DataFrame(), {"cost": 0.0, "co2": 0.0, "qty": 0}

    deficit_df["NeedQty"] = deficit_df["SurplusDeficit"].abs()
    demand_scale = deficit_df["EstDemand7d"].replace(0, 1)
    need_norm = deficit_df["NeedQty"] / max(float(deficit_df["NeedQty"].max()), 1.0)
    risk_norm = (deficit_df["NeedQty"] / demand_scale) / max(float((deficit_df["NeedQty"] / demand_scale).max()), 1.0)
    deficit_df["Priority"] = (weight_risk * risk_norm) + ((1 - weight_risk) * need_norm)
    deficit_df = deficit_df.sort_values("Priority", ascending=False)

    surplus_state = [
        {
            "area": row[area_col],
            "lat": float(row["lat"]),
            "lon": float(row["lon"]),
            "available": float(row["SurplusDeficit"]),
        }
        for _, row in surplus_df.iterrows()
    ]
    deficit_state = [
        {
            "area": row[area_col],
            "lat": float(row["lat"]),
            "lon": float(row["lon"]),
            "need_total": float(row["NeedQty"]),
            "need_remaining": float(row["NeedQty"]),
            "target_remaining": float(row["NeedQty"] * min_fill_ratio),
            "priority": float(row["Priority"]),
        }
        for _, row in deficit_df.iterrows()
    ]

    total_cost = 0.0
    total_co2 = 0.0
    total_qty = 0
    routes = []

    for phase in ["target", "full"]:
        for deficit in deficit_state:
            remaining = deficit["target_remaining"] if phase == "target" else deficit["need_remaining"]
            while remaining > 0:
                candidates = []
                for s_idx, surplus in enumerate(surplus_state):
                    if surplus["available"] <= 0:
                        continue
                    qty = min(surplus["available"], remaining, max_qty_per_route)
                    if qty <= 0:
                        continue
                    distance = haversine(surplus["lat"], surplus["lon"], deficit["lat"], deficit["lon"])
                    for mode in modes:
                        route_cost = distance * mode_profiles[mode]["cost"]
                        route_co2 = distance * mode_profiles[mode]["co2"]
                        if max_total_cost is not None and (total_cost + route_cost) > max_total_cost:
                            continue
                        if max_total_co2 is not None and (total_co2 + route_co2) > max_total_co2:
                            continue
                        candidates.append(
                            {
                                "surplus_idx": s_idx,
                                "mode": mode,
                                "qty": int(qty),
                                "distance": distance,
                                "cost": route_cost,
                                "co2": route_co2,
                            }
                        )

                if not candidates:
                    break

                min_cost = min(c["cost"] for c in candidates)
                max_cost = max(c["cost"] for c in candidates)
                min_co2 = min(c["co2"] for c in candidates)
                max_co2 = max(c["co2"] for c in candidates)
                cost_span = (max_cost - min_cost) or 1.0
                co2_span = (max_co2 - min_co2) or 1.0

                def candidate_score(candidate):
                    cost_norm = (candidate["cost"] - min_cost) / cost_span
                    co2_norm = (candidate["co2"] - min_co2) / co2_span
                    return (weight_cost * cost_norm) + (weight_co2 * co2_norm)

                best = min(candidates, key=candidate_score)
                source = surplus_state[best["surplus_idx"]]

                source["available"] -= best["qty"]
                deficit["need_remaining"] -= best["qty"]
                deficit["target_remaining"] = max(deficit["target_remaining"] - best["qty"], 0)
                remaining = deficit["target_remaining"] if phase == "target" else deficit["need_remaining"]

                total_cost += best["cost"]
                total_co2 += best["co2"]
                total_qty += best["qty"]
                routes.append(
                    {
                        "From": source["area"],
                        "To": deficit["area"],
                        "Qty": int(best["qty"]),
                        "Mode": best["mode"],
                        "Dist(mi)": round(best["distance"], 1),
                        "Cost($)": round(best["cost"], 2),
                        "CO2(lb)": round(best["co2"], 2),
                        "Priority": round(deficit["priority"], 3),
                    }
                )

    coverage = []
    for deficit in deficit_state:
        moved = deficit["need_total"] - deficit["need_remaining"]
        coverage_pct = 0 if deficit["need_total"] == 0 else (moved / deficit["need_total"]) * 100
        coverage.append(
            {
                "DeficitArea": deficit["area"],
                "NeedQty": int(deficit["need_total"]),
                "MovedQty": int(moved),
                "Coverage(%)": round(coverage_pct, 1),
                "Priority": round(deficit["priority"], 3),
            }
        )

    return (
        pd.DataFrame(routes),
        pd.DataFrame(coverage).sort_values(["Priority", "Coverage(%)"], ascending=[False, True]),
        {"cost": total_cost, "co2": total_co2, "qty": int(total_qty)},
    )

def build_alerts_table(
    source_df: pd.DataFrame,
    prod_col: str,
    qty_col: str,
    area_col: str,
    date_col: str,
    low_stock_cover_days: int,
    low_stock_units: int,
    deadstock_days: int,
) -> pd.DataFrame:
    alerts = []
    stock_by_sku = (
        source_df.groupby(prod_col)[qty_col]
        .sum()
        .reset_index(name="CurrentStock")
    )

    cover_by_sku = pd.DataFrame(columns=[prod_col, "AvgDailyDemand", "DaysCover"])
    if date_col != "–":
        sku_daily = (
            source_df.groupby([prod_col, date_col])[qty_col]
            .sum()
            .reset_index()
        )
        cover_by_sku = (
            sku_daily.groupby(prod_col)[qty_col]
            .mean()
            .reset_index(name="AvgDailyDemand")
        )

    stock_with_cover = stock_by_sku.merge(cover_by_sku, on=prod_col, how="left")
    if "AvgDailyDemand" not in stock_with_cover.columns:
        stock_with_cover["AvgDailyDemand"] = 0.0
    stock_with_cover["AvgDailyDemand"] = pd.to_numeric(stock_with_cover["AvgDailyDemand"], errors="coerce").fillna(0.0)

    if date_col != "–":
        stock_with_cover["DaysCover"] = stock_with_cover.apply(
            lambda r: float("inf") if r["AvgDailyDemand"] <= 0 else r["CurrentStock"] / r["AvgDailyDemand"],
            axis=1,
        )
    else:
        stock_with_cover["DaysCover"] = float("inf")

    low_stock_rows = stock_with_cover[
        (stock_with_cover["CurrentStock"] <= low_stock_units) |
        (stock_with_cover["DaysCover"] < low_stock_cover_days)
    ]
    for _, row in low_stock_rows.iterrows():
        days_cover = row["DaysCover"]
        severity = "High" if row["CurrentStock"] <= max(1, low_stock_units // 2) or days_cover < (low_stock_cover_days / 2) else "Medium"
        alerts.append(
            {
                "AlertType": "Low Stock",
                "Severity": severity,
                "SKU": row[prod_col],
                "Area": "All",
                "CurrentStock": int(row["CurrentStock"]),
                "Metric": f"{days_cover:.1f} days cover" if days_cover != float("inf") else "No demand history",
                "Recommendation": "Reorder or rebalance immediately.",
            }
        )

    if date_col != "–" and "DaysSinceSale" in source_df.columns:
        dead_rows = (
            source_df[source_df["DaysSinceSale"] >= deadstock_days]
            .groupby([prod_col, area_col])["DaysSinceSale"]
            .max()
            .reset_index()
        )
        for _, row in dead_rows.iterrows():
            severity = "High" if row["DaysSinceSale"] >= int(deadstock_days * 1.5) else "Medium"
            alerts.append(
                {
                    "AlertType": "Deadstock",
                    "Severity": severity,
                    "SKU": row[prod_col],
                    "Area": row[area_col],
                    "CurrentStock": "",
                    "Metric": f"{int(row['DaysSinceSale'])} days since sale",
                    "Recommendation": "Run markdowns/promotions or transfer out.",
                }
            )

    alert_df = pd.DataFrame(alerts)
    if alert_df.empty:
        return alert_df
    order = {"High": 0, "Medium": 1, "Low": 2}
    alert_df["sort_key"] = alert_df["Severity"].map(order).fillna(3)
    alert_df = alert_df.sort_values(["sort_key", "AlertType", "SKU"]).drop(columns=["sort_key"])
    return alert_df

def post_webhook(url: str, payload: dict):
    try:
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(
            url=url,
            data=body,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with request.urlopen(req, timeout=10) as resp:
            return True, f"Webhook sent (HTTP {resp.getcode()})."
    except error.HTTPError as e:
        return False, f"Webhook failed with HTTP {e.code}."
    except Exception as e:
        return False, f"Webhook failed: {e}"

def build_weekly_report_markdown(
    source_df: pd.DataFrame,
    alerts_df: pd.DataFrame,
    prod_col: str,
    qty_col: str,
    area_col: str,
) -> str:
    total_units = int(source_df[qty_col].sum())
    total_value = float(source_df["TotalValue"].sum())
    sku_count = int(source_df[prod_col].nunique())
    area_count = int(source_df[area_col].nunique())
    low_count = 0 if alerts_df.empty else int((alerts_df["AlertType"] == "Low Stock").sum())
    dead_count = 0 if alerts_df.empty else int((alerts_df["AlertType"] == "Deadstock").sum())

    top_value = (
        source_df.groupby(prod_col)["TotalValue"]
        .sum()
        .sort_values(ascending=False)
        .head(5)
    )
    top_value_lines = "\n".join([f"- {sku}: ${val:,.2f}" for sku, val in top_value.items()])
    if not top_value_lines:
        top_value_lines = "- No SKU value data available"

    lines = [
        "# Weekly Inventory Report",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## Snapshot",
        f"- Total units: {total_units:,}",
        f"- Inventory value: ${total_value:,.2f}",
        f"- SKU count: {sku_count}",
        f"- Area count: {area_count}",
        "",
        "## Alerts",
        f"- Low-stock alerts: {low_count}",
        f"- Deadstock alerts: {dead_count}",
        "",
        "## Top SKUs by Value",
        top_value_lines,
    ]
    return "\n".join(lines)

# --- PAGE FUNCTIONS ---


def page_dashboard():
    with st.container():
        st.header("📊 Dashboard: Inventory Overview")

        # Compute KPIs
        total_units = int(df[qty_col].sum())
        total_val   = df["TotalValue"].sum()
        sku_count   = df[prod_col].nunique()
        area_count  = df[area_col].nunique()

        # Display metric cards
        c1, c2, c3, c4 = st.columns(4, gap="small")
        show_metric_card(c1, "Total Units", f"{total_units:,}")
        show_metric_card(c2, "Inventory Value", f"${total_val:,.2f}")
        show_metric_card(c3, "Unique SKUs", sku_count)
        show_metric_card(c4, "Number of Areas", area_count)
        st.divider()
        st.subheader("🔍 AI-Powered Insight")
        prompt = (
            f"Inventory status: SKUs={sku_count}, Units={total_units}, Value=${total_val:,.2f}. "
            "Provide 3 concise bullet points on health, risks, and opportunities."
        )
        with st.spinner("Analyzing with Gemini…"):
            insight = get_gemini(prompt)
        st.markdown(insight)

        st.divider()
        st.subheader("🗒️ Data Preview")
        st.dataframe(df.head(15), use_container_width=True)

# Stub out other pages for now
# def page_area_charts(): st.header("🗺️ Area Charts (Coming Soon)")
def page_forecast():     st.header("📈 Forecast (Coming Soon)")
def page_last_mile():    st.header("🚚 Last-Mile (Coming Soon)")
def page_deadstock():    st.header("📉 Deadstock (Coming Soon)")
def page_restock():      st.header("💡 Restock (Coming Soon)")

def page_area_charts():
    with st.container():
        st.header("🗺️ Inventory Distribution by Area")
        st.markdown("Visualize how your inventory is spread across your locations.")

        # 1) Aggregate data
        value_agg = df.groupby(area_col)["TotalValue"].sum().reset_index()
        units_agg = df.groupby(area_col)[qty_col].sum().reset_index()

        # 2) User selects metric & chart style
        metric = st.selectbox("Metric", ["Total Value ($)", "Total Units"])
        style  = st.radio("Chart Type", ["Bar Chart", "Pie Chart"], horizontal=True)

        if metric == "Total Value ($)":
            data = value_agg.sort_values("TotalValue", ascending=False)
            y_col = "TotalValue"
            y_label = "Value ($)"
            colorscale = px.colors.sequential.Blues
        else:
            data = units_agg.rename(columns={qty_col: "TotalUnits"}).sort_values("TotalUnits", ascending=False)
            y_col = "TotalUnits"
            y_label = "Units"
            colorscale = px.colors.sequential.Teal

        # 3) Render chart
        if style == "Bar Chart":
            fig = px.bar(
                data,
                x=area_col,
                y=y_col,
                text=y_col,
                color=y_col,
                color_continuous_scale=colorscale,
                labels={area_col: "Area", y_col: y_label},
                title=f"{metric} by Area"
            )
        else:
            fig = px.pie(
                data,
                names=area_col,
                values=y_col,
                hole=0.4,
                color_discrete_sequence=colorscale,
                title=f"{metric} Distribution"
            )

        st.plotly_chart(fig, use_container_width=True)

        # 4) Optional AI Insight
        st.subheader("🔍 AI Insights")
        insight_prompt = (
            f"Inventory distribution by area for metric '{metric}':\n\n"
            f"{data.to_string(index=False)}\n\n"
            "Provide 3 bullet-point observations and 2 actionable recommendations."
        )
        if st.button("Generate AI Analysis"):
            with st.spinner("🧠 Working with Gemini…"):
                analysis = get_gemini(insight_prompt)
                st.markdown(analysis)

def page_forecast():
    with st.container():
        st.header("📈 Demand Forecasting")
        st.markdown("Use historical sales data to predict future demand and plan inventory accordingly.")

        # Guard if no date column mapped
        if date_col == "–":
            st.warning("⚠️ Please map a **Last Sale Date** column to enable forecasting.")
            return

        # 1) Forecast parameters
        with st.expander("⚙️ Forecast Settings", expanded=True):
            periods = st.slider("Forecast horizon (days)", min_value=7, max_value=90, value=30, step=7)
            daily_sea  = st.checkbox("Daily seasonality", value=True)
            weekly_sea = st.checkbox("Weekly seasonality", value=True)
            yearly_sea = st.checkbox("Yearly seasonality", value=True)

        # 2) Aggregate historical daily sales
        daily = df.groupby(date_col)[qty_col].sum().reset_index()
        daily = daily.rename(columns={date_col: "ds", qty_col: "y"})
        st.info(f"Using {len(daily)} days of history to forecast the next {periods} days.")

        # 3) Run Prophet (cached)
        try:
            m, fc = forecast_prophet(
                daily,
                ds_col="ds",
                y_col="y",
                periods=periods,
                daily_seasonality=daily_sea,
                weekly_seasonality=weekly_sea,
                yearly_seasonality=yearly_sea,
            )
        except Exception as e:
            st.error(f"Forecast could not be generated: {e}")
            return

        # 4) Plot interactive forecast
        fig = plot_plotly(m, fc)
        st.plotly_chart(fig, use_container_width=True, height=500)

        # 5) Key forecast metrics
        future = fc.tail(periods)[["ds", "yhat"]].rename(columns={"ds": "Date", "yhat": "Forecast"})
        avg_forecast = future["Forecast"].mean()
        peak_row     = future.loc[future["Forecast"].idxmax()]
        peak_val     = int(peak_row["Forecast"])
        peak_date    = peak_row["Date"].date()

        c1, c2 = st.columns(2)
        c1.metric("Avg. Daily Demand", f"{avg_forecast:,.0f} units")
        c2.metric("Peak Demand", f"{peak_val:,} units on {peak_date}")

        # 6) Table of next 7 days
        st.subheader("Next 7 Days Forecast")
        st.dataframe(future.head(7), use_container_width=True)

        # 7) AI-Powered Demand Insight
        with st.expander("🤖 Generate AI Demand Analysis"):
            prompt = (
                f"Here are the last 30 days of daily sales:\n"
                f"{daily.tail(30).to_string(index=False)}\n\n"
                f"Here is the forecast for the next {periods} days (showing first 7):\n"
                f"{future.head(7).to_string(index=False)}\n\n"
                "Please provide:\n"
                "- Three observations on upcoming demand trends\n"
                "- Two actionable recommendations for inventory adjustments\n"
            )
            if st.button("🧠 Analyze with Gemini"):
                with st.spinner("Contacting Gemini…"):
                    insight = get_gemini(prompt)
                    st.markdown(insight)
            # ── AFTER your existing plots & metrics in page_forecast() ──
        st.divider()
        with st.expander("⚠️ Per-SKU/Area Risk Flags", expanded=False):
            grp_dim = st.radio("Group by", ["Product (SKU)", "Area"], horizontal=True)
            top_n   = st.number_input("Top N groups to analyze", min_value=3, max_value=20, value=5, step=1)
            horizon = st.slider("Horizon (days) for risk calc", 7, 30, 14, step=7)

            # 1) Build historical series per group
            if grp_dim == "Product (SKU)":
                col = prod_col 
            else:
                col = area_col

            # 2) pick top N by current stock
            top_groups = (
                df.groupby(col)[qty_col].sum()
                .sort_values(ascending=False)
                .head(top_n)
                .index
                .tolist()
            )

            risks = []
            for g in top_groups:
                sub = df[df[col] == g].groupby(date_col)[qty_col].sum().reset_index()
                sub = sub.rename(columns={date_col: "ds", qty_col: "y"})
                try:
                    m, fcast = forecast_prophet(
                        sub,
                        ds_col="ds",
                        y_col="y",
                        periods=horizon,
                        daily_seasonality=daily_sea,
                        weekly_seasonality=weekly_sea,
                        yearly_seasonality=yearly_sea,
                    )
                    future_sum = fcast.tail(horizon)["yhat"].sum()
                except Exception:
                    # fallback: use mean*days
                    future_sum = sub["y"].mean() * horizon

                current_stock = df[df[col] == g][qty_col].sum()
                if future_sum > current_stock:
                    status = "🔴 Understock"
                elif future_sum < current_stock * 0.5:
                    status = "🟢 Overstock"
                else:
                    status = "🟡 Balanced"
                risks.append({
                    col: g,
                    "CurrentStock": int(current_stock),
                    f"Forecast{horizon}d": int(future_sum),
                    "Status": status
                })

            risk_df = pd.DataFrame(risks)
            st.table(risk_df)


def page_last_mile():
    with st.container():
            st.header("🚚 Last-Mile Transfers & Sustainability")
            st.markdown("Plan transfers & compare transport modes, with or without geo-data.")

            if date_col == "–":
                st.warning("Map a **Last Sale Date** column to estimate demand.")
                return

            # 1) Surplus/Deficit calc (7-day forecast)
            area_stock = (
                df.groupby(area_col)[qty_col]
                .sum()
                .reset_index(name="Stock")
            )
            total_stock = area_stock["Stock"].sum()
            if total_stock <= 0:
                st.info("Total stock is zero, so no transfers can be planned yet.")
                return

            daily = (
                df.groupby(date_col)[qty_col]
                .sum()
                .reset_index()
                .rename(columns={date_col: "ds", qty_col: "y"})
            )
            try:
                _, fc7 = forecast_prophet(daily, ds_col="ds", y_col="y", periods=7)
                avg7 = fc7.tail(7)["yhat"].mean()
            except Exception:
                avg7 = daily["y"].tail(30).mean()
                if pd.isna(avg7):
                    avg7 = 0

            area_stock["EstDemand7d"] = area_stock["Stock"] / total_stock * (avg7 * 7)
            area_stock["SurplusDeficit"] = area_stock["Stock"] - area_stock["EstDemand7d"]
            if "transfers" not in st.session_state:
                st.session_state["transfers"] = []

            # 2) Auto-geocode fallback
            coords_available = (lat_col != "–" and lon_col != "–")
            has_cached_geo = "geo_df" in st.session_state

            if not coords_available and not has_cached_geo:
                st.info("No geo-columns provided. You can auto-geocode your area names.")
                if st.button("📍 Auto-geocode Areas"):
                    areas = area_stock[area_col].unique().tolist()
                    geo_df = geocode_areas(areas)
                    if geo_df.empty:
                        st.error("Geocoding failed. Showing fallback chart.")
                    else:
                        st.success("Coordinates resolved! Rerun this page to see the map.")
                        st.session_state.geo_df = geo_df

                # Fallback: bar chart of surplus/deficit
                st.subheader("Surplus/Deficit by Area (Fallback)")
                st.bar_chart(
                    area_stock.set_index(area_col)["SurplusDeficit"],
                    height=300
                )
                return  # skip full map & planner UI

            # 3) Merge geo-data for map
            if has_cached_geo:
                geo = (
                    st.session_state.geo_df
                    .rename(columns={"area": area_col})
                    .merge(area_stock, on=area_col, how="inner")
                )
            else:
                geo = (
                    df[[area_col, lat_col, lon_col]]
                    .drop_duplicates(subset=[area_col])
                    .merge(area_stock, on=area_col, how="inner")
                    .rename(columns={lat_col: "lat", lon_col: "lon"})
                )
            geo["lat"] = pd.to_numeric(geo["lat"], errors="coerce")
            geo["lon"] = pd.to_numeric(geo["lon"], errors="coerce")
            geo = geo.dropna(subset=["lat", "lon"])
            if geo.empty:
                st.error("No valid coordinates available for transfer planning.")
                return

            # 4) Display map
            st.subheader("Map: Surplus/Deficit by Area")
            import plotly.express as px
            fig = px.scatter_mapbox(
                geo, lat="lat", lon="lon",
                color="SurplusDeficit", size="Stock",
                color_continuous_midpoint=0,
                color_continuous_scale=["red","white","green"],
                size_max=20, zoom=4,
                mapbox_style="open-street-map",
                hover_name=area_col,
                hover_data=["Stock","EstDemand7d","SurplusDeficit"],
            )
            st.plotly_chart(fig, use_container_width=True, height=400)

            mode_profiles = {
                "🚚 Truck": {"co2": 3.0, "cost": 1.8},
                "🚛 Van": {"co2": 2.0, "cost": 1.2},
                "🚁 Drone": {"co2": 0.5, "cost": 0.8},
            }

            st.divider()
            with st.expander("🧠 Optimized Transfer Planner (Cost + CO2 + Risk)", expanded=False):
                mode_strategy = st.selectbox(
                    "Mode Strategy",
                    ["Auto (Best Mix)", "🚚 Truck", "🚛 Van", "🚁 Drone"],
                )
                c1, c2, c3 = st.columns(3)
                with c1:
                    weight_cost = st.slider("Weight: Cost", 0.0, 1.0, 0.45, 0.05)
                with c2:
                    weight_co2 = st.slider("Weight: CO2", 0.0, 1.0, 0.35, 0.05)
                with c3:
                    weight_risk = st.slider("Weight: Stockout Risk", 0.0, 1.0, 0.20, 0.05)

                max_qty_per_route = st.slider("Max Qty Per Route", 1, 500, 120, 1)
                min_fill_ratio = st.slider("Min Coverage Target (%)", 10, 100, 70, 5) / 100.0

                use_constraints = st.checkbox("Apply Budget/CO2 Constraints", value=False)
                max_total_cost = None
                max_total_co2 = None
                if use_constraints:
                    d1, d2 = st.columns(2)
                    with d1:
                        max_total_cost = st.number_input("Max Total Cost ($)", min_value=1.0, value=500.0, step=25.0)
                    with d2:
                        max_total_co2 = st.number_input("Max Total CO2 (lb)", min_value=1.0, value=800.0, step=25.0)

                if st.button("⚙️ Run Optimizer"):
                    total_weights = weight_cost + weight_co2 + weight_risk
                    if total_weights <= 0:
                        st.error("Set at least one non-zero weight.")
                    else:
                        cost_w = weight_cost / total_weights
                        co2_w = weight_co2 / total_weights
                        risk_w = weight_risk / total_weights
                        plan_df, coverage_df, totals = optimize_transfer_plan(
                            geo_df=geo,
                            area_col=area_col,
                            mode_profiles=mode_profiles,
                            mode_strategy=mode_strategy,
                            weight_cost=cost_w,
                            weight_co2=co2_w,
                            weight_risk=risk_w,
                            max_total_cost=max_total_cost,
                            max_total_co2=max_total_co2,
                            max_qty_per_route=max_qty_per_route,
                            min_fill_ratio=min_fill_ratio,
                        )
                        st.session_state["optimized_batch"] = plan_df
                        st.session_state["optimized_coverage"] = coverage_df
                        st.session_state["optimized_totals"] = totals
                        save_plan(
                            engine=engine,
                            workspace=st.session_state["active_workspace"],
                            plan_type="optimized_transfer_plan",
                            payload_json=plan_df.to_json(orient="records"),
                            created_by=current_username,
                        )
                        st.success("Optimization completed.")

                if "optimized_batch" in st.session_state:
                    plan_df = st.session_state["optimized_batch"]
                    coverage_df = st.session_state.get("optimized_coverage", pd.DataFrame())
                    totals = st.session_state.get("optimized_totals", {"cost": 0.0, "co2": 0.0, "qty": 0})

                    if plan_df.empty:
                        st.info("No feasible optimized routes found for current constraints.")
                    else:
                        m1, m2, m3, m4 = st.columns(4)
                        m1.metric("Routes", len(plan_df))
                        m2.metric("Total Qty", int(totals["qty"]))
                        m3.metric("Total Cost", f"${totals['cost']:.2f}")
                        m4.metric("Total CO2", f"{totals['co2']:.2f} lb")

                        st.dataframe(plan_df, use_container_width=True, hide_index=True)
                        if not coverage_df.empty:
                            st.caption("Deficit Coverage")
                            st.dataframe(coverage_df, use_container_width=True, hide_index=True)

                        if st.button("➕ Add Optimized Plan to Manual Batch"):
                            for _, r in plan_df.iterrows():
                                st.session_state["transfers"].append({
                                    "From": r["From"],
                                    "To": r["To"],
                                    "Qty": int(r["Qty"]),
                                    "Mode": r["Mode"],
                                    "Dist(mi)": f"{r['Dist(mi)']:.1f}",
                                    "CO₂(lb)": f"{r['CO2(lb)']:.1f}",
                                    "Cost($)": f"{r['Cost($)']:.2f}",
                                })
                            st.success("Optimized routes added to manual batch.")

            # 5) Transfer Planner Controls
            st.subheader("📝 Plan a Transfer")
            col1, col2 = st.columns([2,1])
            surplus_areas = geo.query("SurplusDeficit>0")[area_col].tolist()
            deficit_areas = geo.query("SurplusDeficit<0")[area_col].tolist()
            if not surplus_areas or not deficit_areas:
                st.info("No transfer opportunities found (need both surplus and deficit areas).")
                return

            with col1:
                from_area = st.selectbox("From (Surplus)", surplus_areas)
                to_area   = st.selectbox("To (Deficit)", deficit_areas)
                max_qty = int(min(
                    geo.query(f"{area_col}==@from_area")["SurplusDeficit"].iloc[0],
                    abs(geo.query(f"{area_col}==@to_area")["SurplusDeficit"].iloc[0])
                ))
                if max_qty < 1:
                    st.info("No transferable quantity for the selected pair.")
                    return
                qty_move = st.slider("Quantity to Move", 1, max_qty, 1)

            with col2:
                st.markdown("**Transport Mode**")
                mode = st.radio("", ["🚚 Truck","🚛 Van","🚁 Drone"], index=1)
                prof = mode_profiles[mode]
                st.write(f"- **CO₂/mi:** {prof['co2']} lb")
                st.write(f"- **Cost/mi:** ${prof['cost']}")

            # 6) Route preview & impact
            st.subheader("🔄 Preview & Impact")
            src = geo.query(f"{area_col}==@from_area").iloc[0]
            dst = geo.query(f"{area_col}==@to_area").iloc[0]
            dist = haversine(src["lat"], src["lon"], dst["lat"], dst["lon"])
            co2  = dist * prof["co2"]
            cost = dist * prof["cost"]

            m1, m2, m3 = st.columns(3)
            m1.metric("Distance (mi)", f"{dist:.1f}")
            m2.metric("Est. CO₂ (lb)", f"{co2:.1f}")
            m3.metric("Est. Cost ($)", f"{cost:.2f}")

            # draw line
            import plotly.graph_objects as go
            lf = go.Figure(go.Scattermapbox(
                lat=[src["lat"], dst["lat"]],
                lon=[src["lon"], dst["lon"]],
                mode="lines+markers",
                marker=dict(size=[8,8], color="blue"),
                line=dict(width=3, color="blue"),
            ))
            lf.update_layout(
                mapbox_style="open-street-map",
                mapbox_zoom=4,
                mapbox_center={"lat": (src["lat"]+dst["lat"])/2, "lon": (src["lon"]+dst["lon"])/2},
                margin=dict(l=0,r=0,t=0,b=0)
            )
            st.plotly_chart(lf, use_container_width=True, height=300)

            # 7) Batch Planner
            st.subheader("📋 Batch Transfer Plan")
            if st.button("➕ Add to Batch"):
                st.session_state["transfers"].append({
                    "From": from_area, "To": to_area, "Qty": qty_move,
                    "Mode": mode, "Dist(mi)": f"{dist:.1f}",
                    "CO₂(lb)": f"{co2:.1f}", "Cost($)": f"{cost:.2f}"
                })
            st.table(pd.DataFrame(st.session_state["transfers"]))

            # 8) Scenario Simulation
            st.subheader("⚡ Scenario Simulation")
            scenario = st.selectbox("Pick a scenario", [
                "Local Festival ➜ spike demand",
                "Snowstorm ➜ route block",
                "Flash Sale ➜ surge orders"
            ])
            if st.button("🔮 Simulate & Advise"):
                batch = pd.DataFrame(st.session_state["transfers"])
                prompt = (
                    f"Scenario: {scenario}.\n"
                    f"Planned transfers:\n{batch.to_string(index=False)}\n\n"
                    "Recommend additional adjustments with rationale (cost/co2)."
                )
                with st.spinner("Asking Gemini…"):
                    advice = get_gemini(prompt)
                st.markdown(advice)

def page_deadstock():
    with st.container():
        st.header("📉 Deadstock Analysis")
        st.markdown(
            "Identify slow-moving inventory items and visualize deadstock across areas."
        )

        if date_col == "–":
            st.warning("Map a **Last Sale Date** column to use deadstock analysis.")
            return

        # 1) Let user define 'dead' threshold
        days_thresh = st.slider(
            "Days since last sale ≥",
            min_value=30, max_value=730, value=180, step=15
        )

        # 2) Filter deadstock
        dead_df = df[df["DaysSinceSale"] >= days_thresh].copy()
        if dead_df.empty:
            st.success(f"No items unsold in the last {days_thresh} days!")
            return

        # 3) Summary metrics
        total_skus   = dead_df[prod_col].nunique()
        total_units  = int(dead_df[qty_col].sum())
        total_value  = dead_df["TotalValue"].sum()
        st.info(f"🔎 Found {total_skus} SKUs, {total_units} units, totaling ${total_value:,.2f}.")

        # 4) Bar chart: deadstock value by area
        st.subheader("Deadstock Value by Area")
        area_dead = (
            dead_df.groupby(area_col)["TotalValue"]
                .sum()
                .reset_index()
                .sort_values("TotalValue", ascending=False)
        )
        fig = px.bar(
            area_dead,
            x=area_col, y="TotalValue",
            labels={"TotalValue":"Value ($)"},
            color="TotalValue",
            color_continuous_scale=px.colors.sequential.Oranges,
            text="TotalValue"
        )
        st.plotly_chart(fig, use_container_width=True, height=350)

        # 5) Detailed table (with search & download)
        st.subheader("Deadstock Items Detail")
        st.dataframe(
            dead_df[[prod_col, qty_col, "TotalValue", "DaysSinceSale", area_col]]
                .sort_values("DaysSinceSale", ascending=False),
            use_container_width=True
        )
        # CSV download
        csv = dead_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️ Download Deadstock CSV",
            data=csv,
            file_name="deadstock_items.csv",
            mime="text/csv"
        )

        # 6) Optional AI Insight
        with st.expander("🤖 AI-Powered Deadstock Insights"):
            prompt = (
                f"Here are {total_skus} deadstock SKUs (>= {days_thresh} days since last sale):\n\n"
                f"{dead_df[[prod_col, qty_col, 'TotalValue', 'DaysSinceSale']].head(20).to_string(index=False)}\n\n"
                "Please provide:\n"
                "1. Three key observations about this deadstock.\n"
                "2. Top 3 prioritized actions to reduce deadstock.\n"
                "3. Suggestions to prevent deadstock in the future."
            )
            if st.button("🧠 Generate Deadstock Analysis"):
                with st.spinner("Thinking…"):
                    result = get_gemini(prompt)
                    st.markdown(result)
                        # ── Paste this block after each Gemini response ──
                    feedback_key = f"feedback_{page}"  # unique per page (page can be "deadstock", "restock", "scenario")
                    st.markdown("**Your Feedback**")
                    fb_option = st.radio(
                        "Did you find this helpful?",
                        ["👍 Approve", "👎 Reject"],
                        key=feedback_key + "_radio",
                        horizontal=True
                    )
                    fb_comment = st.text_area(
                        "Any comments or tweaks?",
                        key=feedback_key + "_text",
                        placeholder="Type your feedback here..."
                    )
                    if st.button("Submit Feedback", key=feedback_key+"_btn"):
                        entry = {
                            "page": page,
                            "choice": fb_option,
                            "comment": fb_comment,
                            "timestamp": datetime.now().isoformat()
                        }
                        st.session_state.setdefault("feedback_log", []).append(entry)
                        save_feedback(
                            engine=engine,
                            workspace=st.session_state["active_workspace"],
                            page=page,
                            choice=fb_option,
                            comment=fb_comment or "",
                            created_by=current_username,
                        )
                        st.success("Thanks for your feedback!")
                        
        st.session_state["deadstock_df"] = dead_df

def page_restock():
    with st.container():
        st.header("💡 Restock & Revive Strategies")
        st.markdown(
            "Turn deadstock into sales with AI-driven action plans and reorder suggestions."
        )

        # Require that deadstock was computed
        dead = st.session_state.get("deadstock_df", None)
        if dead is None or dead.empty:
            st.info("Run **Deadstock Analysis** first to generate a restock plan.")
            return

        # Show summary
        total_skus  = dead[prod_col].nunique()
        total_value = dead["TotalValue"].sum()
        st.write(f"🔢 **Items to address:** {total_skus} SKUs (total value ${total_value:,.2f})")

        # 1) AI-driven Restock Plan
        if st.button("🧠 Generate Restock Action Plan"):
            with st.spinner("Consulting Gemini…"):
                sample = dead[[prod_col, qty_col, "TotalValue", "DaysSinceSale"]].head(20)
                prompt = (
                    f"As an inventory strategist, create a **Restock & Revive** plan "
                    f"for these deadstock SKUs:\n\n{sample.to_string(index=False)}\n\n"
                    f"Total deadstock value: ${total_value:,.2f}\n\n"
                    "Structure your response in Markdown under these headings:\n"
                    "1. Triage & Prioritization (which SKUs first and why)\n"
                    "2. Four actionable marketing/sales strategies (with concrete examples)\n"
                    "3. Operational improvements to avoid future deadstock\n"
                    "4. Final summary recommendation"
                )
                plan = get_gemini(prompt)
                st.markdown(plan)

        # 2) Reorder Point Planner (Forecast + Lead Time + Safety Stock)
        st.subheader("Reorder Point Planner")
        st.markdown(
            "Formula: **Reorder Point = (Forecast Daily Demand x Lead Time) + Safety Stock**"
        )
        if date_col == "–":
            st.warning("Map a **Last Sale Date** column to calculate reorder points.")
        else:
            scope = st.radio(
                "SKU Scope",
                ["All SKUs", "Deadstock SKUs only"],
                horizontal=True
            )

            stock_by_sku = (
                df.groupby(prod_col)[qty_col]
                .sum()
                .reset_index(name="CurrentStock")
                .sort_values("CurrentStock", ascending=False)
            )
            if scope == "Deadstock SKUs only":
                stock_by_sku = stock_by_sku[stock_by_sku[prod_col].isin(dead[prod_col].unique())]

            if stock_by_sku.empty:
                st.info("No SKUs available for reorder-point planning in this scope.")
            else:
                max_skus = min(25, len(stock_by_sku))
                sku_count = st.slider(
                    "SKUs to evaluate",
                    min_value=1,
                    max_value=max_skus,
                    value=min(10, max_skus),
                    step=1,
                )
                selected = stock_by_sku.head(sku_count)

                demand_daily = (
                    df.groupby([prod_col, date_col])[qty_col]
                    .sum()
                    .reset_index()
                )

                base_rows = []
                for sku in selected[prod_col].tolist():
                    sku_daily = (
                        demand_daily[demand_daily[prod_col] == sku][[date_col, qty_col]]
                        .rename(columns={date_col: "ds", qty_col: "y"})
                        .copy()
                    )
                    avg_daily = float(pd.to_numeric(sku_daily["y"], errors="coerce").fillna(0).mean())
                    demand_std = float(pd.to_numeric(sku_daily["y"], errors="coerce").fillna(0).std(ddof=0))
                    if pd.isna(demand_std):
                        demand_std = 0.0

                    # Forecast next 14 days per SKU; fallback to historical average when needed.
                    forecast_daily = max(avg_daily, 0.0)
                    try:
                        _, sku_fc = forecast_prophet(sku_daily, ds_col="ds", y_col="y", periods=14)
                        forecast_daily = max(float(sku_fc.tail(14)["yhat"].mean()), 0.0)
                    except Exception:
                        pass

                    current_stock = float(selected.loc[selected[prod_col] == sku, "CurrentStock"].iloc[0])
                    base_rows.append(
                        {
                            prod_col: sku,
                            "CurrentStock": current_stock,
                            "ForecastDailyDemand": forecast_daily,
                            "DemandStdDev": demand_std,
                        }
                    )

                base_plan = pd.DataFrame(base_rows)
                params = base_plan[[prod_col]].copy()
                params["LeadTimeDays"] = 7
                params["ServiceLevel"] = 0.95

                params = st.data_editor(
                    params,
                    use_container_width=True,
                    hide_index=True,
                    key="reorder_params_editor",
                    column_config={
                        "LeadTimeDays": st.column_config.NumberColumn(
                            "Lead Time (Days)", min_value=1, max_value=180, step=1
                        ),
                        "ServiceLevel": st.column_config.NumberColumn(
                            "Service Level", min_value=0.50, max_value=0.999, step=0.01, format="%.3f"
                        ),
                    },
                )

                rp = base_plan.merge(params, on=prod_col, how="left")
                rp["LeadTimeDays"] = pd.to_numeric(rp["LeadTimeDays"], errors="coerce").fillna(7).clip(lower=1)
                rp["ServiceLevel"] = pd.to_numeric(rp["ServiceLevel"], errors="coerce").fillna(0.95).clip(lower=0.50, upper=0.999)
                rp["ZScore"] = rp["ServiceLevel"].apply(lambda x: float(NormalDist().inv_cdf(x)))
                rp["LeadTimeDemand"] = rp["ForecastDailyDemand"] * rp["LeadTimeDays"]
                rp["SafetyStock"] = rp["ZScore"] * rp["DemandStdDev"] * (rp["LeadTimeDays"] ** 0.5)
                rp["ReorderPoint"] = (rp["LeadTimeDemand"] + rp["SafetyStock"]).clip(lower=0).round().astype(int)
                rp["RecommendedOrderQty"] = (rp["ReorderPoint"] - rp["CurrentStock"]).clip(lower=0).round().astype(int)
                rp["Status"] = rp.apply(
                    lambda r: "Reorder Now" if r["CurrentStock"] <= r["ReorderPoint"] else "Sufficient",
                    axis=1,
                )
                rp["StockCoverageDays"] = rp.apply(
                    lambda r: "∞" if r["ForecastDailyDemand"] <= 0 else f"{(r['CurrentStock'] / r['ForecastDailyDemand']):.1f}",
                    axis=1,
                )

                m1, m2, m3 = st.columns(3)
                m1.metric("SKUs Needing Reorder", int((rp["Status"] == "Reorder Now").sum()))
                m2.metric("Total Suggested Order Qty", int(rp["RecommendedOrderQty"].sum()))
                m3.metric("Avg Service Level", f"{rp['ServiceLevel'].mean():.2%}")

                st.dataframe(
                    rp[
                        [
                            prod_col,
                            "CurrentStock",
                            "ForecastDailyDemand",
                            "LeadTimeDays",
                            "ServiceLevel",
                            "SafetyStock",
                            "ReorderPoint",
                            "RecommendedOrderQty",
                            "StockCoverageDays",
                            "Status",
                        ]
                    ].sort_values("RecommendedOrderQty", ascending=False),
                    use_container_width=True,
                    hide_index=True,
                )

                rp_csv = rp.to_csv(index=False).encode("utf-8")
                st.download_button(
                    "⬇️ Download Reorder Plan CSV",
                    data=rp_csv,
                    file_name="reorder_plan.csv",
                    mime="text/csv",
                )
                if st.button("💾 Save Reorder Plan to Workspace", key="save_reorder_plan_btn"):
                    save_plan(
                        engine=engine,
                        workspace=st.session_state["active_workspace"],
                        plan_type="reorder_plan",
                        payload_json=rp.to_json(orient="records"),
                        created_by=current_username,
                    )
                    st.success("Reorder plan saved.")

        # 3) Export Plan
        export_md = plan if "plan" in locals() else ""
        if export_md:
            st.download_button(
                "⬇️ Download Restock Plan (Markdown)",
                data=export_md,
                file_name="restock_plan.md",
                mime="text/markdown"
            )

def page_alerts():
    with st.container():
        st.header("🔔 Alerts & Weekly Automation")
        st.markdown("Track low-stock and deadstock alerts, notify external tools, and generate weekly reports.")

        a1, a2, a3 = st.columns(3)
        with a1:
            low_stock_cover_days = st.slider("Low-Stock Cover Threshold (days)", 1, 30, 7, 1)
        with a2:
            low_stock_units = st.number_input("Low-Stock Units Threshold", min_value=1, max_value=10000, value=25, step=1)
        with a3:
            deadstock_days = st.slider("Deadstock Threshold (days)", 30, 730, 180, 15)

        alerts_df = build_alerts_table(
            source_df=df,
            prod_col=prod_col,
            qty_col=qty_col,
            area_col=area_col,
            date_col=date_col,
            low_stock_cover_days=int(low_stock_cover_days),
            low_stock_units=int(low_stock_units),
            deadstock_days=int(deadstock_days),
        )
        st.session_state["latest_alerts_df"] = alerts_df

        if alerts_df.empty:
            st.success("No active alerts for the selected thresholds.")
        else:
            high_alerts = int((alerts_df["Severity"] == "High").sum())
            low_stock_count = int((alerts_df["AlertType"] == "Low Stock").sum())
            deadstock_count = int((alerts_df["AlertType"] == "Deadstock").sum())

            m1, m2, m3 = st.columns(3)
            m1.metric("Total Alerts", len(alerts_df))
            m2.metric("High Severity", high_alerts)
            m3.metric("Low-Stock / Deadstock", f"{low_stock_count} / {deadstock_count}")

            st.dataframe(alerts_df, use_container_width=True, hide_index=True)
            alerts_csv = alerts_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                "⬇️ Download Alerts CSV",
                data=alerts_csv,
                file_name="inventory_alerts.csv",
                mime="text/csv",
            )

        st.divider()
        with st.expander("📣 Send Alerts to Webhook", expanded=False):
            if current_role not in {"manager", "admin"}:
                st.warning("Only manager/admin roles can push webhook alerts.")
            else:
                webhook_url = st.text_input("Webhook URL", placeholder="https://hooks.slack.com/services/...")
                provider = st.selectbox("Provider", ["Slack", "Generic JSON"])
                high_only = st.checkbox("Send high-severity alerts only", value=True)

                if st.button("Send Alerts"):
                    if not webhook_url.strip():
                        st.warning("Enter a webhook URL first.")
                    elif alerts_df.empty:
                        st.info("No alerts to send.")
                    else:
                        payload_df = alerts_df.copy()
                        if high_only:
                            payload_df = payload_df[payload_df["Severity"] == "High"]

                        if payload_df.empty:
                            st.info("No matching alerts after filters.")
                        else:
                            payload = {
                                "provider": provider,
                                "generated_at": datetime.now().isoformat(),
                                "alert_count": len(payload_df),
                                "alerts": payload_df.head(20).to_dict(orient="records"),
                            }
                            ok, msg = post_webhook(webhook_url.strip(), payload)
                            if ok:
                                st.success(msg)
                            else:
                                st.error(msg)

        st.divider()
        with st.expander("🗓️ Weekly Report Automation", expanded=True):
            weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            weekday = st.selectbox("Run Day", weekdays, index=0)
            run_hour = st.slider("Run Hour (24h)", 0, 23, 9, 1)
            include_ai = st.checkbox("Include AI Summary", value=True)

            if st.button("Generate Weekly Report Now"):
                report_md = build_weekly_report_markdown(
                    source_df=df,
                    alerts_df=alerts_df,
                    prod_col=prod_col,
                    qty_col=qty_col,
                    area_col=area_col,
                )
                if include_ai:
                    ai_prompt = (
                        "Create a concise weekly inventory operations summary with top priorities.\n\n"
                        f"Alert snapshot:\n{alerts_df.head(15).to_string(index=False) if not alerts_df.empty else 'No active alerts'}\n"
                    )
                    ai_summary = get_gemini(ai_prompt)
                    report_md += f"\n\n## AI Summary\n{ai_summary}"

                st.session_state["weekly_report_md"] = report_md
                st.session_state["weekly_report_generated_at"] = datetime.now().isoformat()
                save_plan(
                    engine=engine,
                    workspace=st.session_state["active_workspace"],
                    plan_type="weekly_report",
                    payload_json=json.dumps({"report_markdown": report_md}),
                    created_by=current_username,
                )
                st.success("Weekly report generated.")

            if "weekly_report_md" in st.session_state:
                st.caption(f"Generated at: {st.session_state.get('weekly_report_generated_at', '')}")
                st.download_button(
                    "⬇️ Download Weekly Report (Markdown)",
                    data=st.session_state["weekly_report_md"],
                    file_name="weekly_inventory_report.md",
                    mime="text/markdown",
                )

            dow_map = {
                "Sunday": 0, "Monday": 1, "Tuesday": 2, "Wednesday": 3,
                "Thursday": 4, "Friday": 5, "Saturday": 6
            }
            cron_expr = f"0 {run_hour} * * {dow_map[weekday]}"
            st.caption("Automation Hint")
            st.code(f"# Weekly schedule example (cron)\n{cron_expr}  <your-report-job-command>", language="bash")


def page_admin():
    with st.container():
        st.header("🛡️ Admin Console")
        if current_role != "admin":
            st.warning("Admin access required.")
            return
        st.markdown("Manage users, workspaces, and governance controls for StockPilot AI.")
        st.write(f"Active workspace: **{st.session_state['active_workspace']}**")
        workspace_values = list_workspaces(engine)
        st.dataframe(pd.DataFrame({"Workspaces": workspace_values}), use_container_width=True, hide_index=True)
        st.info("User creation is available in the sidebar under **User Admin**.")

# --- PAGE ROUTER ---
pages = {
  "Dashboard":       page_dashboard,
  "Area Charts":     page_area_charts,
  "Forecast":        page_forecast,
  "Last-Mile":       page_last_mile,
  "Deadstock":       page_deadstock,
  "Restock":         page_restock,
  "Alerts":          page_alerts,
  "Admin":           page_admin,
}
pages[page]()
