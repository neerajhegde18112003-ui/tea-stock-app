import streamlit as st
import json, os, random, glob, pandas as pd
import shutil
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="Nagbari Traders", page_icon="🍃", layout="wide")

st.markdown("""<style>
    [data-testid="stAppViewContainer"] > .main { background-color: #f8fafc; }
    h1 { font-size: 2.5rem !important; color: #166534; text-align: center; margin-bottom: 20px; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
</style>""", unsafe_allow_html=True)

DATA_FILE = "tea_stock_data.json"
LOG_FILE = "transaction_log.json"
BACKUP_DIR = "backups"

# --- CORE FUNCTIONS ---
def run_auto_backup():
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)
    today_str = datetime.now().strftime("%Y-%m-%d")
    for f_name in [DATA_FILE, LOG_FILE]:
        if os.path.exists(f_name):
            shutil.copy(f_name, os.path.join(BACKUP_DIR, f"{f_name.replace('.json', '')}_{today_str}.json"))

def load_inventory():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
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
        except:
            return []
    return []

# --- INITIALIZATION ---
if "inventory_data" not in st.session_state:
    st.session_state.inventory_data = load_inventory()

# --- MAIN UI ---
st.markdown("<h1>🍃 NAGBARI TRADERS</h1>", unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "➕ Add Inventory", "📜 Transaction History"])

with tab1:
    st.header("📦 Live Stock Balance Matrix")
    current_inventory = st.session_state.inventory_data
    
    if current_inventory:
        cols = st.columns(3)
        idx = 0
        for name, data in current_inventory.items():
            tot_stk = sum(b["qty"] for b in data.get("batches", []))
            with cols[idx % 3]:
                with st.container(border=True):
                    st.subheader(name)
                    st.metric("Stock", f"{tot_stk:,} KG")
                    st.metric("Sale Price", f"₹{data.get('sale_price', 0.0)}")
                    if st.button(f"Manage {name}", key=f"btn_{name}"):
                        st.session_state.selected_item = name
            idx += 1
    else:
        st.info("No stock items found.")

with tab2:
    st.header("➕ Add New Inventory Batch")
    with st.form("add_form"):
        item_name = st.text_input("Item Name")
        qty = st.number_input("Quantity (KG)", min_value=1)
        price = st.number_input("Cost Price (₹)", min_value=0.0)
        if st.form_submit_button("Update Inventory"):
            if item_name not in st.session_state.inventory_data:
                st.session_state.inventory_data[item_name] = {"sale_price": price*1.2, "low_stock_limit": 50, "batches": []}
            st.session_state.inventory_data[item_name]["batches"].append({"qty": qty, "cost": price})
            save_inventory(st.session_state.inventory_data)
            st.success("Batch added successfully!")

with tab3:
    st.header("📜 Transaction Logs")
    txs = load_transactions()
    if txs:
        df = pd.DataFrame(txs)
        st.dataframe(df, use_container_width=True)
    else:
        st.write("No transactions recorded yet.")
