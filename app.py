import streamlit as st
import json, os, random, glob, pandas as pd
import shutil
from datetime import datetime

# --- MODERN THEME & MOBILE RESPONSIVENESS CONFIG ---
st.set_page_config(page_title="Nagbari Traders", page_icon="🍃", layout="wide")

# Enhanced UI Styling for Compact Mobile Operations
st.markdown("""<style>
    [data-testid="stAppViewContainer"] > .main { background-color: #f8fafc; }
    
    /* Mobile optimization rules for tight spacing */
    @media (max-width: 768px) {
        [data-testid="stHorizontalBlock"] { flex-direction: row !important; flex-wrap: nowrap !important; overflow-x: auto; }
        [data-testid="stHorizontalBlock"] > div { min-width: 140px !important; flex: 1 1 auto !important; padding: 4px !important; }
        .stMetric { padding: 8px !important; }
    }
    
    /* Clean grid cards for metrics */
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
    """Runs a rolling, daily background backup to prevent data loss."""
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)
        
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

def add_transaction(item, t_type, qty, rate, margin, cost_info, status, party):
    txs = load_transactions()
    amt = float(qty) * float(rate) if qty > 0 else float(rate)
    clean_party = party.strip() if party.strip() != "" else "N/A"
    txs.insert(0, {
        "id": str(random.randint(100000, 999999)),
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"), "item_name": item, "type": t_type,
        "quantity": int(qty), "rate (₹)": float(rate) if qty > 0 else 0.0, "total_amount (₹)": amt,
        "net_profit_realized (₹)": float(margin), "cost_used_details": cost_info, "payment_status": status,
        "party": clean_party
    })
    with open(LOG_FILE, "w", encoding='utf-8') as f:
        json.dump(txs, f, indent=4)
    run_auto_backup()

def rebuild_inventory_and_metrics_from_scratch():
    fresh_inv = load_inventory()
    for k in fresh_inv: fresh_inv[k]["batches"] = []
    txs = load_transactions()
    for t in reversed(txs):
        item = t.get("item_name")
        ttype = t.get("type")
        qty = int(t.get("quantity", 0))
        rate = float(t.get("rate (₹)", 0))
        if item in fresh_inv:
            it_data = fresh_inv[item]
            if ttype == "PURCHASE (Stock In)":
                it_data["batches"].append({"qty": qty, "cost": rate})
                t["net_profit_realized (₹)"] = 0.0
                t["cost_used_details"] = f"Added @ ₹{rate}/KG"
            elif ttype == "SALE (Stock Out)":
                rem, cost_bk, margin = qty, [], 0.0
                tot_avail = sum(b["qty"] for b in it_data["batches"])
                rem = min(rem, tot_avail)
                t["quantity"] = rem
                while rem > 0 and it_data["batches"]:
                    old_b = it_data["batches"][0]
                    qty_t = min(old_b["qty"], rem)
                    margin += (rate - float(old_b["cost"])) * qty_t
                    cost_bk.append(f"{qty_t}KG @ ₹{old_b['cost']}")
                    old_b["qty"] -= qty_t
                    rem -= qty_t
                    if old_b["qty"] == 0: it_data["batches"].pop(0)
                t["net_profit_realized (₹)"] = margin
                t["cost_used_details"] = ", ".join(cost_bk)
                t["total_amount (₹)"] = t["quantity"] * rate
            elif ttype == "INITIAL STOCK":
                if qty > 0: it_data["batches"].append({"qty": qty, "cost": rate})
                t["net_profit_realized (₹)"] = 0.0
                t["cost_used_details"] = "Opening Balance Setup"
    save_inventory(fresh_inv)
    with open(LOG_FILE, "w", encoding='utf-8') as f:
        json.dump(txs, f, indent=4)
    st.session_state.inventory_data = fresh_inv

# --- INITIAL DATA HYDRATION ---
if "inventory_data" not in st.session_state: 
    st.session_state.inventory_data = load_inventory()

# Always match state variables dynamically
current_inventory = st.session_state.inventory_data
transactions_history = load_transactions()
run_auto_backup()

# --- SIDEBAR & RECOVERY UTILITIES ---
with st.sidebar:
    st.header("⚙️ Settings & Recovery")
    
    with st.expander("🚨 Emergency Data Restore Tool", expanded=True):
        st.write("If transactions or names are missing, use this to recover files from the auto-backup history.")
        st_log_files = sorted(glob.glob(os.path.join(BACKUP_DIR, "tx_log_*.json")))
        st_stock_files = sorted(glob.glob(os.path.join(BACKUP_DIR, "stock_*.json")))
        
        if st_log_files:
            latest_log_name = os.path.basename(st_log_files[-1])
            st.info(f"Most Recent Backup Found:\n`{latest_log_name}`")
            if st.button("Restore Most Recent Backup 🔄", use_container_width=True):
                shutil.copy(st_log_files[-1], LOG_FILE)
                if st_stock_files:
                    shutil.copy(st_stock_files[-1], DATA_FILE)
                st.session_state.inventory_data = load_inventory()
                st.success("Data pulled safely from history! Refreshing layout...")
                st.rerun()
        else:
            st.error("No archive backups found in the current project directory folder.")
            
    with st.expander("🚨 Master System Reset", expanded=False):
        st.warning("This completely deletes all history and resets stock to 0.")
        confirm_text = st.text_input("Type 'RESET' to authorize:")
        if st.button("WIPE LEDGER NOW 💥", use_container_width=True):
            if confirm_text == "RESET":
                if os.path.exists(LOG_FILE): os.remove(LOG_FILE)
                if os.path.exists(DATA_FILE): os.remove(DATA_FILE)
                st.session_state.clear()
                st.success("System completely wiped!")
                st.rerun()
            else: st.error("Incorrect text entry.")

# --- ACCOUNT BALANCE CALCULATIONS ---
customer_credit_map = {}
supplier_credit_map = {}

for tx in reversed(transactions_history):
    pty = tx.get("party", "N/A")
    if pty == "N/A" or pty == "Opening Setup": continue
    ttype = tx.get("type", "")
    tamt = float(tx.get("total_amount (₹)", 0.0))
    pstatus = tx.get("payment_status", "")
    
    if ttype == "SALE (Stock Out)" and pstatus == "CREDIT":
        customer_credit_map[pty] = customer_credit_map.get(pty, 0.0) + tamt
    elif ttype == "CUSTOMER PAYMENT (Money Received)":
        customer_credit_map[pty] = customer_credit_map.get(pty, 0.0) - tamt
        
    if ttype == "PURCHASE (Stock In)" and pstatus == "CREDIT":
        supplier_credit_map[pty] = supplier_credit_map.get(pty, 0.0) + tamt
    elif ttype == "SUPPLIER PAYMENT (Money Paid)":
        supplier_credit_map[pty] = supplier_credit_map.get(pty, 0.0) - tamt

active_debtors = {k: v for k, v in customer_credit_map.items() if v > 0.01}
active_creditors = {k: v for k, v in supplier_credit_map.items() if v > 0.01}

# --- METRICS CALCULATOR ENGINE ---
prof = sum(float(x.get("net_profit_realized (₹)", 0)) for x in transactions_history if x.get("type") == "SALE (Stock Out)")
total_expenses = sum(float(x.get("total_amount (₹)", 0)) for x in transactions_history if x.get("type") == "BUSINESS EXPENSE")
net_operating_profit = prof - total_expenses

receivables = sum(active_debtors.values())
payables = sum(active_creditors.values())

c_in = sum(float(x.get("total_amount (₹)", 0)) for x in transactions_history if x.get("type") in ["SALE (Stock Out)", "CUSTOMER PAYMENT (Money Received)"] and x.get("payment_status") == "CASH")
c_out = sum(float(x.get("total_amount (₹)", 0)) for x in transactions_history if x.get("type") in ["PURCHASE (Stock In)", "SUPPLIER PAYMENT (Money Paid)", "BUSINESS EXPENSE"] and x.get("payment_status") == "CASH")
cash_flow = c_in - c_out

b_in = sum(float(x.get("total_amount (₹)", 0)) for x in transactions_history if x.get("type") in ["SALE (Stock Out)", "CUSTOMER PAYMENT (Money Received)"] and x.get("payment_status") == "BANK")
b_out = sum(float(x.get("total_amount (₹)", 0)) for x in transactions_history if x.get("type") in ["PURCHASE (Stock In)", "SUPPLIER PAYMENT (Money Paid)", "BUSINESS EXPENSE"] and x.get("payment_status") == "BANK")
bank_flow = b_in - b_out

# --- MAIN DASHBOARD INTERFACE ---
st.markdown("<h1>🍃 NAGBARI TRADERS</h1>", unsafe_allow_html=True)

tot_stk = sum(sum(b["qty"] for b in item.get("batches", [])) for item in current_inventory.values())

st.markdown(f"""
<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; margin-bottom: 15px;">
    <div style="background: white; padding: 12px; border-radius: 10px; border: 1px solid #e2e8f0; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
        <div style="font-size: 0.8rem; color: #64748b; font-weight: 500;">Stock Balance</div>
        <div style="font-size: 1.25rem; font-weight: 700; color: #0f172a; margin-top: 2px;">{tot_stk:,} KG</div>
    </div>
    <div style="background: white; padding: 12px; border-radius: 10px; border: 1px solid #e2e8f0; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
        <div style="font-size: 0.8rem; color: #64748b; font-weight: 500;">Trading Profit 💰</div>
        <div style="font-size: 1.25rem; font-weight: 700; color: #16a34a; margin-top: 2px;">₹{round(prof, 2):,}</div>
    </div>
    <div style="background: white; padding: 12px; border-radius: 10px; border: 1px solid #e2e8f0; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
        <div style="font-size: 0.8rem; color: #64748b; font-weight: 500;">Net Profit ✨</div>
        <div style="font-size: 1.25rem; font-weight: 700; color: #0d9488; margin-top: 2px;">₹{round(net_operating_profit, 2):,}</div>
    </div>
    <div style="background: white; padding: 12px; border-radius: 10px; border: 1px solid #e2e8f0; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
        <div style="font-size: 0.8rem; color: #64748b; font-weight: 500;">Receivables 📈</div>
        <div style="font-size: 1.25rem; font-weight: 700; color: #2563eb; margin-top: 2px;">₹{round(receivables, 2):,}</div>
    </div>
    <div style="background: white; padding: 12px; border-radius: 10px; border: 1px solid #e2e8f0; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
        <div style="font-size: 0.8rem; color: #64748b; font-weight: 500;">Payables 📉</div>
        <div style="font-size: 1.25rem; font-weight: 700; color: #dc2626; margin-top: 2px;">₹{round(payables, 2):,}</div>
    </div>
    <div style="background: white; padding: 12px; border-radius: 10px; border: 1px solid #e2e8f0; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
        <div style="font-size: 0.8rem; color: #64748b; font-weight: 500;">Cash Box 💵</div>
        <div style="font-size: 1.25rem; font-weight: 700; color: #0f172a; margin-top: 2px;">₹{round(cash_flow, 2):,}</div>
    </div>
    <div style="background: white; padding: 12px; border-radius: 10px; border: 1px solid #e2e8f0; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
        <div style="font-size: 0.8rem; color: #64748b; font-weight: 500;">Bank Position 🏦</div>
        <div style="font-size: 1.25rem; font-weight: 700; color: #0f172a; margin-top: 2px;">₹{round(bank_flow, 2):,}</div>
    </div>
</div>
""", unsafe_allow_html=True)

st.write("---")

# Drawers (Expanders) for Fast Smartphone Operations
with st.expander("📝 **Drawer: Log New Goods Transaction (Stock In/Out)**", expanded=False):
    if list(current_inventory.keys()):
        x_c1, x_c2, x_c3 = st.columns(3)
        with x_c1: 
            sel_item = st.selectbox("Tea Variety", list(current_inventory.keys()))
            tx_type = st.radio("Action Type", ["PURCHASE (Stock In)", "SALE (Stock Out)"], horizontal=True)
        with x_c2:
            tx_qty = st.number_input("Quantity (KG)", min_value=1, value=100, step=50)
            b_list = current_inventory[sel_item].get("batches", [])
            tot_item_stk = sum(b["qty"] for b in b_list)
            lat_cost = b_list[-1]["cost"] if b_list else 0.0
            def_rate = lat_cost if tx_type == "PURCHASE (Stock In)" else current_inventory[sel_item]["sale_price"]
            tx_rate = st.number_input("Rate (₹/KG)", min_value=0.0, value=float(def_rate), step=5.0)
        with x_c3:
            p_mode = st.selectbox("Payment Mode Options", ["CASH", "BANK", "CREDIT"])
            p_info = st.text_input("Party Business Name")
            
        if st.button("Submit Stock Entry ⚡", use_container_width=True):
            if p_info.strip() == "":
                st.error("❌ Party Business Name cannot be empty.")
            else:
                it_data = current_inventory[sel_item]
                margin, details = 0.0, ""
                if tx_type == "SALE (Stock Out)" and tx_qty > tot_item_stk:
                    st.error(f"❌ Low Stock! Only {tot_item_stk} KG left.")
                else:
                    if tx_type == "PURCHASE (Stock In)":
                        if "batches" not in it_data: it_data["batches"] = []
                        it_data["batches"].append({"qty": int(tx_qty), "cost": float(tx_rate)})
                        details = f"Added @ ₹{tx_rate}/KG"
                    else:
                        rem, cost_bk = int(tx_qty), []
                        while rem > 0 and it_data["batches"]:
                            old_b = it_data["batches"][0]
                            qty_t = min(old_b["qty"], rem)
                            margin += (float(tx_rate) - float(old_b["cost"])) * qty_t
                            cost_bk.append(f"{qty_t}KG @ ₹{old_b['cost']}")
                            old_b["qty"] -= qty_t
                            rem -= qty_t
                            if old_b["qty"] == 0: it_data["batches"].pop(0)
                        details = ", ".join(cost_bk)
                    save_inventory(current_inventory)
                    add_transaction(sel_item, tx_type, tx_qty, tx_rate, margin, details, p_mode, p_info)
                    st.session_state.inventory_data = current_inventory
                    st.success("Logged successfully!")
                    st.rerun()
    else: st.info("Please add a tea variety first.")

with st.expander("💰 **Drawer: Log Direct Cash/Bank Adjustment (Clear Dues)**", expanded=False):
    a_c1, a_c2 = st.columns(2)
    with a_c1: 
        c_tx_type = st.radio("Direction Mode", ["CUSTOMER PAYMENT (Money Received)", "SUPPLIER PAYMENT (Money Paid)"])
        adj_amt = st.number_input("Amount Paid/Received (₹)", min_value=1.0, value=5000.0, step=1000.0)
    with a_c2:
        adj_mode = st.selectbox("Account Channel", ["CASH", "BANK"])
        
        if c_tx_type == "CUSTOMER PAYMENT (Money Received)":
            party_options = list(active_debtors.keys())
            if party_options:
                format_func = lambda x: f"👤 {x} (Owes: ₹{active_debtors[x]:,})"
                selected_party = st.selectbox("Select Customer to Clear Dues", options=party_options, format_func=format_func)
            else: selected_party = st.text_input("Type Customer Name")
        else:
            party_options = list(active_creditors.keys())
            if party_options:
                format_func = lambda x: f"🏢 {x} (You Owe: ₹{active_creditors[x]:,})"
                selected_party = st.selectbox("Select Supplier to Pay", options=party_options, format_func=format_func)
            else: selected_party = st.text_input("Type Supplier Name")
                
        adj_rem = st.text_input("Remarks Summary", placeholder="e.g., Partial payment / Settlement")
        
    if st.button("Submit Ledger Entry 💰", use_container_width=True):
        if not selected_party or selected_party.strip() == "":
            st.error("❌ Please provide or select a valid Party Name.")
        else:
            add_transaction("N/A (Pure Cash)", c_tx_type, 0, adj_amt, 0.0, adj_rem if adj_rem.strip() else "Cleared via Ledger Entry", adj_mode, selected_party)
            st.success(f"Payment entry parsed!")
            st.rerun()

with st.expander("💸 **Drawer: Log Business Expenses (Rent, Labor, Freight)**", expanded=False):
    ex_c1, ex_c2 = st.columns(2)
    with ex_c1:
        ex_cat = st.selectbox("Expense Category", ["Warehouse Rent", "Labor Wages", "Freight / Transport", "Brokerage Commission", "Office Supplies & Miscellaneous"])
        ex_amt = st.number_input("Expense Amount (₹)", min_value=1.0, value=1000.0, step=500.0)
    with ex_c2:
        ex_mode = st.selectbox("Paid From Channel", ["CASH", "BANK"])
        ex_notes = st.text_input("Additional Notes")
        
    if st.button("Log Expense Record 💥", use_container_width=True):
        add_transaction(
            item="Business Operation Cost", t_type="BUSINESS EXPENSE", qty=0, rate=ex_amt,
            margin=0.0, cost_info=ex_cat, status=ex_mode, party=ex_notes if ex_notes.strip() else "General Operational Cost"
        )
        st.success(f"Successfully logged expense!")
        st.rerun()

with st.expander("✨ **Drawer: Add New Tea Catalog Variety**", expanded=False):
    v_name = st.text_input("Variety Label Name")
    v_stk = st.number_input("Opening Stock (KG Value)", min_value=0, value=0)
    v_cost = st.number_input("Cost (₹/KG Base)", min_value=0.0, value=0.0)
    v_sale = st.number_input("Target Sale Rate (₹/KG)", min_value=0.0, value=0.0)
    v_alert = st.number_input("Low Stock Warning Alert Trigger (KG)", min_value=0, value=100)
    if st.button("Add New Product to Catalog", use_container_width=True) and v_name.strip() and v_name not in current_inventory:
        batches = [{"qty": int(v_stk), "cost": float(v_cost)}] if v_stk > 0 else []
        current_inventory[v_name] = {"sale_price": v_sale, "low_stock_limit": int(v_alert), "batches": batches}
        374:                with st.expander("⚙️ Edit Settings", expanded=False):
                    new_s = st.number_input("Adjust Price (₹/KG)", min_value=0.0, value=float(dt.get('sale_price', 0.0)), key=f"ed_{name}")
                    new_l = st.number_input("Low Stock Warning Line (KG)", min_value=0, value=int(limit), step=25, key=f"lim_{name}")
                    if new_s != dt.get('sale_price', 0.0) or new_l != limit:
                    # --- PASTE THIS HERE ---
                    if st.button(f"🗑️ Delete {name} Permanently", key=f"del_{name}"):
                        if name in current_inventory:
                            del current_inventory[name]
                            save_inventory(current_inventory)
                            st.session_state.inventory_data = current_inventory
                            st.warning(f"{name} has been removed from catalog.")
                            st.rerun()
                    # -----------------------    
        save_inventory(current_inventory)
        add_transaction(v_name, "INITIAL STOCK", v_stk, v_cost, 0.0, "Opening Balance Setup", "CASH", "Opening Setup")
        st.session_state.inventory_data = current_inventory
        st.rerun()

# --- PARTY CREDIT ARRAYS ---
st.write("---")
st.header("👥 Outstanding Credit Directory")
c_debt, c_cred = st.columns(2)
with c_debt:
    with st.container(border=True):
        st.markdown("### 📈 Customer Balance (Receivables)")
        if active_debtors:
            for name, amt in active_debtors.items():
                st.write(f"• **{name}:** <span style='color:#2563eb; font-weight:600;'>₹{amt:,}</span>", unsafe_allow_html=True)
        else: st.write("*No outstanding customer credit lines active!*")
with c_cred:
    with st.container(border=True):
        st.markdown("### 📉 Supplier Balance (Payables)")
        if active_creditors:
            for name, amt in active_creditors.items():
                st.write(f"• **{name}:** <span style='color:#dc2626; font-weight:600;'>₹{amt:,}</span>", unsafe_allow_html=True)
        else: st.write("*No supplier credit lines outstanding!*")

# --- STOCK LIVE MATRIX GRAPHICS ---
st.write("---")
st.header("📦 Live Stock Balance Matrix")
if current_inventory:
    g_col1, g_col2 = st.columns(2)
    idx = 0
    for name in list(current_inventory.keys()):
        dt = current_inventory[name]
        b_list = dt.get("batches", [])
        tot_stk = sum(b["qty"] for b in b_list)
        limit = dt.get("low_stock_limit", 100)
        
        with (g_col1 if idx % 2 == 0 else g_col2):
            idx += 1
            with st.container(border=True):
                if tot_stk <= limit:
                    st.markdown(f"### {name} <span style='color:#ef4444; font-size:0.8rem; font-weight:bold; border:1px solid #fca5a5; padding:2px 6px; border-radius:4px; background-color:#fef2f2;'>⚠️ LOW STOCK</span>", unsafe_allow_html=True)
                else: st.markdown(f"### {name}")
                    
                if not b_list: st.write("*Out of Stock*")
                else:
                    for i, b in enumerate(b_list):
                        st.write(f"• **Batch #{i+1}:** {b['qty']:,} KG remaining @ **₹{b['cost']}/KG**")
                st.write("---")
                m1, m2 = st.columns(2)
                st.metric("Available Stock", f"{tot_stk:,} KG")
                st.metric("Active Price", f"₹{dt.get('sale_price', 0.0)}")
                
                with st.expander("⚙️ Edit Settings", expanded=False):
                    new_s = st.number_input("Adjust Price (₹/KG)", min_value=0.0, value=float(dt.get('sale_price', 0.0)), key=f"ed_{name}")
                    new_l = st.number_input("Low Stock Warning Line (KG)", min_value=0, value=int(limit), step=25, key=f"lim_{name}")
                    if new_s != dt.get('sale_price', 0.0) or new_l != limit:
                        current_inventory[name]["sale_price"] = new_s
                        current_inventory[name]["low_stock_limit"] = new_l
                        save_inventory(current_inventory)
                        st.session_state.inventory_data = current_inventory
                        st.rerun()
else: st.info("No stock items parsed.")

# --- DYNAMIC RECENT TRANSACTION HISTORY PANELS ---
st.write("---")
st.header("📜 Recent Transactions Log")
if transactions_history:
    fl_c1, fl_c2 = st.columns(2)
    with fl_c1: search_party = st.text_input("🔎 Search by Party Name:", value="")
    with fl_c2: search_item = st.selectbox("🎯 Filter by Tea Variety:", ["ALL", "BUSINESS EXPENSE"] + list(current_inventory.keys()))

    filtered_txs = transactions_history
    if search_party.strip():
        filtered_txs = [t for t in filtered_txs if search_party.lower() in t.get("party", "").lower() or search_party.lower() in t.get("cost_used_details", "").lower()]
    if search_item != "ALL":
        if search_item == "BUSINESS EXPENSE":
            filtered_txs = [t for t in filtered_txs if t.get("type") == "BUSINESS EXPENSE"]
        else:
            filtered_txs = [t for t in filtered_txs if t.get("item_name") == search_item]

    if filtered_txs:
        download_data = []
        for t in filtered_txs:
            download_data.append({
                "Date & Time": t.get("date"), "Transaction Type": t.get("type"), "Product/Item": t.get("item_name"),
                "Party/Details": t.get("party"), "Quantity (KG)": t.get("quantity", 0), "Rate (₹/KG)": t.get("rate (₹)", 0.0),
                "Total Amount (₹)": t.get("total_amount (₹)", 0.0), "Payment Mode": t.get("payment_status"), "Profit Realized (₹)": t.get("net_profit_realized (₹)", 0.0)
            })
        df_download = pd.DataFrame(download_data)
        st.download_button(
            label="📥 Download Filtered Ledger Table (CSV)", data=df_download.to_csv(index=False).encode('utf-8'),
            file_name=f"Nagbari_Ledger_{datetime.now().strftime('%Y%m%d_%H%M')}.csv", mime="text/csv", use_container_width=True
        )
        
        # DISPLAY VISUAL LOG LIST
        for t in filtered_txs:
            t_type = t.get("type")
            t_date = t.get("date")
            t_party = t.get("party")
            t_amt = t.get("total_amount (₹)", 0.0)
            t_mode = t.get("payment_status", "CASH")
            
            if t_type == "BUSINESS EXPENSE":
                badge = f"<span style='background-color:#fee2e2; color:#991b1b; padding:3px 8px; border-radius:6px; font-weight:600; font-size:0.8rem;'>💸 EXPENSE</span>"
                desc = f"**{t.get('cost_used_details')}** | Notes: *{t_party}*"
            elif "PAYMENT" in t_type:
                badge = f"<span style='background-color:#dbeafe; color:#1d4ed8; padding:3px 8px; border-radius:6px; font-weight:600; font-size:0.8rem;'>💰 BAL CLEAR</span>"
                desc = f"**{t_type}** | Party: **{t_party}** | *{t.get('cost_used_details')}*"
            else:
                b_color = "#dcfce7" if "SALE" in t_type else "#fef3c7"
                f_color = "#15803d" if "SALE" in t_type else "#b45309"
                badge = f"<span style='background-color:{b_color}; color:{f_color}; padding:3px 8px; border-radius:6px; font-weight:600; font-size:0.8rem;'>{t_type}</span>"
                desc = f"**{t.get('item_name')}** ({t.get('quantity')} KG @ ₹{t.get('rate (₹)')}/KG) | Party: **{t_party}**"
                
            st.markdown(f"""
            <div style="background:white; padding:10px 14px; border-radius:8px; border:1px solid #e2e8f0; margin-bottom:6px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
                <div>[{t_date}] {badge} &nbsp;&nbsp; {desc}</div>
                <div style="font-weight:700; color:#0f172a;">₹{t_amt:,} <span style="font-size:0.75rem; color:#64748b; font-weight:400;">({t_mode})</span></div>
            </div>
            """, unsafe_allow_html=True)
            
        # MODIFICATION EDITOR EXPANDER
        tx_options = []
        for t in filtered_txs:
            t_id = t.get("id", "legacy")
            lbl = f"[{t.get('date')}] {t.get('type')} - {t.get('item_name') or t.get('cost_used_details')} - Party: {t.get('party')}"
            tx_options.append((t_id, lbl))
            
        with st.expander("🔧 **Tap to Open Live Transaction Editor Panel**", expanded=False):
            sel_tx_id = st.selectbox("Pick an entry to modify or delete:", options=[x[0] for x in tx_options], format_func=lambda x: next(y[1] for y in tx_options if y[0] == x))
            target_tx = next(x for x in transactions_history if x.get("id", "legacy") == sel_tx_id)
            
            st.markdown(f"#### 📝 Modifying Transaction ID `#{target_tx.get('id')}`")
            ed_col1, ed_col2 = st.columns(2)
            if target_tx.get("type") == "BUSINESS EXPENSE":
                with ed_col1:
                    new_party = st.text_input("Edit Expense Notes", value=target_tx.get("party"))
                    new_pmode = st.selectbox("Edit Account Channel", ["CASH", "BANK"], index=["CASH", "BANK"].index(target_tx.get("payment_status", "CASH")))
                with ed_col2:
                    new_rate = st.number_input("Modify Expense Amount (₹)", min_value=0.0, value=float(target_tx.get("rate (₹)", 0.0)))
                    new_qty = 0
            else:
                with ed_col1:
                    new_party = st.text_input("Edit Party Name", value=target_tx.get("party"))
                    new_pmode = st.selectbox("Edit Payment Mode", ["CASH", "BANK", "CREDIT"], index=["CASH", "BANK", "CREDIT"].index(target_tx.get("payment_status", "CASH")))
                with ed_col2:
                    new_qty = st.number_input("Modify Quantity (KG)", min_value=0, value=int(target_tx.get("quantity", 0)))
                    new_rate = st.number_input("Modify Rate (₹/KG)", min_value=0.0, value=float(target_tx.get("rate (₹)", 0.0)))
                
            btn_save, btn_void = st.columns(2)
            with btn_save:
                if st.button("Save & Recalculate Ledger ✅", use_container_width=True):
                    target_tx["party"] = new_party
                    target_tx["payment_status"] = new_pmode
                    target_tx["quantity"] = int(new_qty)
                    target_tx["rate (₹)"] = float(new_rate)
                    target_tx["total_amount (₹)"] = float(int(new_qty) * float(new_rate) if int(new_qty) > 0 else float(new_rate))
                    
                    with open(LOG_FILE, "w", encoding='utf-8') as f:
                        json.dump(transactions_history, f, indent=4)
                    rebuild_inventory_and_metrics_from_scratch()
                    st.success("Changes saved!")
                    st.rerun()
            with btn_void:
                if st.button("Void / Delete Entry Completely 🗑️", use_container_width=True):
                    updated_txs = [x for x in transactions_history if x.get("id", "legacy") != sel_tx_id]
                    with open(LOG_FILE, "w", encoding='utf-8') as f:
                        json.dump(updated_txs, f, indent=4)
                    rebuild_inventory_and_metrics_from_scratch()
                    st.warning("Transaction deleted completely.")
                    st.rerun()
else:
    st.info("No transaction histories have been saved or discovered yet. Log a transaction above to generate data logs.")
