import streamlit as st
import json, os, random, glob, pandas as pd
import shutil
from datetime import datetime

# --- MODERN THEME & MOBILE RESPONSIVENESS CONFIG ---
st.set_page_config(page_title="Nagbari Traders", page_icon="🍃", layout="wide")

st.markdown("""<style>
    [data-testid="stAppViewContainer"] > .main { background-color: #f8fafc; }
    @media (max-width: 768px) {
        [data-testid="stHorizontalBlock"] { flex-direction: row !important; flex-wrap: nowrap !important; overflow-x: auto; }
        [data-testid="stHorizontalBlock"] > div { min-width: 140px !important; flex: 1 1 auto !important; padding: 4px !important; }
        .stMetric { padding: 8px !important; }
    }
    [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"] > div > div > div > div {
        border-radius: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.04);
        background-color: white; padding: 14px !important; border: 1px solid #e2e8f0; margin-bottom: 8px;
    }
    h1 { font-size: 1.8rem !important; color: #166534; font-weight: 700; text-align: center; margin-bottom: 0.5rem !important; }
    h2 { font-size: 1.2rem !important; color: #1e293b; font-weight: 600; margin: 0.8rem 0 0.4rem 0 !important;}
    h3 { font-size: 1.1rem !important; font-weight: 700; margin: 0px !important; color: #0f172a; }
</style>""", unsafe_allow_html=True)

DATA_FILE, LOG_FILE = "tea_stock_data.json", "transaction_log.json"
BACKUP_DIR = "backups"

# --- AUTOMATED BACKUP ENGINE ---
def run_auto_backup():
    if not os.path.exists(BACKUP_DIR): os.makedirs(BACKUP_DIR)
    today_str = datetime.now().strftime("%Y-%m-%d")
    if os.path.exists(LOG_FILE):
        log_backup_path = os.path.join(BACKUP_DIR, f"tx_log_{today_str}.json")
        if not os.path.exists(log_backup_path):
            with open(LOG_FILE, 'r', encoding='utf-8') as src, open(log_backup_path, 'w', encoding='utf-8') as dest:
                dest.write(src.read())
    if os.path.exists(DATA_FILE):
        stock_backup_path = os.path.join(BACKUP_DIR, f"stock_{today_str}.json")
        if not os.path.exists(stock_backup_path):
            with open(DATA_FILE, 'r', encoding='utf-8') as src, open(stock_backup_path, 'w', encoding='utf-8') as dest:
                dest.write(src.read())
    for prefix in ["tx_log_", "stock_"]:
        files = sorted(glob.glob(os.path.join(BACKUP_DIR, f"{prefix}*.json")))
        if len(files) > 5:
            for old_file in files[:-5]:
                try: os.remove(old_file)
                except: pass

def load_inventory():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding='utf-8') as f:
                d = json.load(f)
            for k in d:
                if "batches" not in d[k]:
                    stk, prc = d[k].get("stock", 0), d[k].get("purchase_price", 200.0)
                    d[k]["batches"] = [{"qty": stk, "cost": prc}] if stk > 0 else []
                if "sale_price" not in d[k]: d[k]["sale_price"] = d[k].get("price", 250.0)
                if "low_stock_limit" not in d[k]: d[k]["low_stock_limit"] = 100
            return d
        except: pass
    return {"Assam CTC Tea": {"sale_price": 250.0, "low_stock_limit": 100, "batches": [{"qty": 1000, "cost": 200.0}]}}

def save_inventory(inv):
    with open(DATA_FILE, "w", encoding='utf-8') as f:
        json.dump(inv, f, indent=4)
    run_auto_backup()

def load_transactions():
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, "r", encoding='utf-8') as f:
                return json.load(f)
        except: return []
    return []

def add_transaction(item, t_type, qty, rate, margin, cost_info, status, party):
    txs = load_transactions()
    amt = float(qty) * float(rate) if qty > 0 else float(rate)
    txs.insert(0, {
        "id": str(random.randint(100000, 999999)),
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"), "item_name": item, "type": t_type,
        "quantity": int(qty), "rate (₹)": float(rate) if qty > 0 else 0.0, "total_amount (₹)": amt,
        "net_profit_realized (₹)": float(margin), "cost_used_details": cost_info, "payment_status": status,
        "party": party.strip() if party.strip() != "" else "N/A"
    })
    with open(LOG_FILE, "w", encoding='utf-8') as f:
        json.dump(txs, f, indent=4)
    run_auto_backup()

def rebuild_inventory_and_metrics_from_scratch():
    fresh_inv = load_inventory()
    for k in fresh_inv: fresh_inv[k]["batches"] = []
    txs = load_transactions()
    for t in reversed(txs):
        item, ttype, qty, rate = t.get("item_name"), t.get("type"), int(t.get("quantity", 0)), float(t.get("rate (₹)", 0))
        if item in fresh_inv:
            it_data = fresh_inv[item]
            if ttype == "PURCHASE (Stock In)":
                it_data["batches"].append({"qty": qty, "cost": rate})
            elif ttype == "SALE (Stock Out)":
                rem, cost_bk, margin = qty, [], 0.0
                while rem > 0 and it_data["batches"]:
                    old_b = it_data["batches"][0]
                    qty_t = min(old_b["qty"], rem)
                    margin += (rate - float(old_b["cost"])) * qty_t
                    old_b["qty"] -= qty_t
                    rem -= qty_t
                    if old_b["qty"] == 0: it_data["batches"].pop(0)
                t["net_profit_realized (₹)"] = margin
            elif ttype == "INITIAL STOCK":
                if qty > 0: it_data["batches"].append({"qty": qty, "cost": rate})
    save_inventory(fresh_inv)
    st.session_state.inventory_data = fresh_inv

# --- INITIAL DATA HYDRATION ---
if "inventory_data" not in st.session_state: st.session_state.inventory_data = load_inventory()
current_inventory = st.session_state.inventory_data
transactions_history = load_transactions()
run_auto_backup()

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Settings & Recovery")
    if st.button("Restore Most Recent Backup 🔄"):
        st.session_state.inventory_data = load_inventory()
        st.rerun()
    if st.button("WIPE LEDGER NOW 💥"):
        if os.path.exists(LOG_FILE): os.remove(LOG_FILE)
        if os.path.exists(DATA_FILE): os.remove(DATA_FILE)
        st.session_state.clear()
        st.rerun()

# --- METRICS ---
prof = sum(float(x.get("net_profit_realized (₹)", 0)) for x in transactions_history if x.get("type") == "SALE (Stock Out)")
net_operating_profit = prof - sum(float(x.get("total_amount (₹)", 0)) for x in transactions_history if x.get("type") == "BUSINESS EXPENSE")
tot_stk = sum(sum(b["qty"] for b in item.get("batches", [])) for item in current_inventory.values())

st.markdown("<h1>🍃 NAGBARI TRADERS</h1>", unsafe_allow_html=True)
cols = st.columns(7)
cols[0].metric("Stock", f"{tot_stk:,} KG")
cols[1].metric("Trading Profit", f"₹{round(prof, 2):,}")
cols[2].metric("Net Profit", f"₹{round(net_operating_profit, 2):,}")
# (Additional metrics simplified for copy-paste length)

st.write("---")

# --- DRAWERS ---
with st.expander("📝 Log New Goods Transaction"):
    sel_item = st.selectbox("Tea Variety", list(current_inventory.keys()))
    tx_type = st.radio("Action", ["PURCHASE (Stock In)", "SALE (Stock Out)"], horizontal=True)
    tx_qty = st.number_input("Quantity (KG)", min_value=1, value=100)
    tx_rate = st.number_input("Rate (₹/KG)", min_value=0.0, value=250.0)
    p_info = st.text_input("Party Name")
    if st.button("Submit Stock Entry"):
        it_data = current_inventory[sel_item]
        margin, details = 0.0, ""
        if tx_type == "PURCHASE (Stock In)":
            it_data["batches"].append({"qty": int(tx_qty), "cost": float(tx_rate)})
        else:
            rem, cost_bk = int(tx_qty), []
            while rem > 0 and it_data["batches"]:
                old_b = it_data["batches"][0]
                qty_t = min(old_b["qty"], rem)
                margin += (float(tx_rate) - float(old_b["cost"])) * qty_t
                old_b["qty"] -= qty_t
                rem -= qty_t
                if old_b["qty"] == 0: it_data["batches"].pop(0)
        save_inventory(current_inventory)
        add_transaction(sel_item, tx_type, tx_qty, tx_rate, margin, "Manual Entry", "CASH", p_info)
        st.rerun()

# --- STOCK LIVE MATRIX GRAPHICS ---
st.header("📦 Live Stock Balance Matrix")
if current_inventory:
    g_col1, g_col2 = st.columns(2)
    idx = 0
    for name in list(current_inventory.keys()):
        dt = current_inventory[name]
        tot_stk = sum(b["qty"] for b in dt.get("batches", []))
        with (g_col1 if idx % 2 == 0 else g_col2):
            idx += 1
            with st.container(border=True):
                col_a, col_b = st.columns([4, 1])
                with col_a: st.markdown(f"### {name}")
                with col_b:
                    confirm = st.checkbox("Delete?", key=f"conf_{name}", label_visibility="collapsed")
                    if confirm and st.button("🗑️", key=f"del_{name}"):
                        del current_inventory[name]
                        save_inventory(current_inventory)
                        st.rerun()
                st.metric("Available", f"{tot_stk:,} KG")
else: st.info("No stock items.")
