import streamlit as st
import json, os, random, smtplib, pandas as pd
from email.mime.text import MIMEText
from datetime import datetime

# --- MODERN THEME & MOBILE RESPONSIVENESS CONFIG ---
st.set_page_config(page_title="Nagbari Traders", page_icon="🍃", layout="wide")

# Enhanced UI Styling for Compact Mobile Operations
st.markdown("""<style>
    [data-testid="stAppViewContainer"] > .main { background-color: #f8fafc; }
    
    .clean-login-card {
        background-color: white !important;
        padding: 28px !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 12px !important;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05), 0 2px 4px -1px rgba(0,0,0,0.03) !important;
        margin-top: 22vh !important;
        width: 100% !important;
    }
    
    /* Mobile optimization rules for tight spacing */
    @media (max-width: 768px) {
        .clean-login-card { margin-top: 15vh !important; }
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
    
    /* Color Badges for Fast Scanning */
    .badge-cash { background-color: #dcfce7; color: #15803d; padding: 4px 8px; border-radius: 6px; font-weight: 600; font-size: 0.8rem; }
    .badge-bank { background-color: #dbeafe; color: #1d4ed8; padding: 4px 8px; border-radius: 6px; font-weight: 600; font-size: 0.8rem; }
    .badge-credit { background-color: #fef3c7; color: #b45309; padding: 4px 8px; border-radius: 6px; font-weight: 600; font-size: 0.8rem; }
</style>""", unsafe_allow_html=True)

DATA_FILE, LOG_FILE, AUTH_FILE = "tea_stock_data.json", "transaction_log.json", "auth_config.json"
OWNER_EMAIL = "your-email@gmail.com" 

def load_auth():
    return json.load(open(AUTH_FILE, "r")) if os.path.exists(AUTH_FILE) else {"password": "admin"}

def save_auth(pwd):
    json.dump({"password": pwd}, open(AUTH_FILE, "w"))

def send_otp_email(to_email, otp_code):
    try:
        u, p = st.secrets["email"]["gmail_user"], st.secrets["email"]["gmail_password"]
        msg = MIMEText(f"Your 4-Digit OTP for changing Admin Password is: {otp_code}")
        msg['Subject'], msg['From'], msg['To'] = "🔒 Security OTP", u, to_email
        s = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        s.login(u, p)
        s.sendmail(u, to_email, msg.as_string())
        s.close()
        return True
    except Exception as e:
        st.error(f"Email failed: {e}")
        return False

def load_inventory():
    if os.path.exists(DATA_FILE):
        d = json.load(open(DATA_FILE, "r"))
        for k in d:
            if "batches" not in d[k]:
                stk, prc = d[k].get("stock", 0), d[k].get("purchase_price", 200.0)
                d[k]["batches"] = [{"qty": stk, "cost": prc}] if stk > 0 else []
            if "sale_price" not in d[k]: d[k]["sale_price"] = d[k].get("price", 250.0)
            if "low_stock_limit" not in d[k]: d[k]["low_stock_limit"] = 100
        return d
    return {"Assam CTC Tea": {"sale_price": 250.0, "low_stock_limit": 100, "batches": [{"qty": 1000, "cost": 200.0}]}}

def save_inventory(inv):
    json.dump(inv, open(DATA_FILE, "w"), indent=4)

def load_transactions():
    return json.load(open(LOG_FILE, "r")) if os.path.exists(LOG_FILE) else []

def add_transaction(item, t_type, qty, rate, margin, cost_info, status, party):
    txs = load_transactions()
    amt = int(qty) * float(rate) if qty > 0 else float(rate)
    txs.insert(0, {
        "id": str(random.randint(100000, 999999)),
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"), "item_name": item, "type": t_type,
        "quantity": int(qty), "rate (₹)": float(rate) if qty > 0 else 0.0, "total_amount (₹)": amt,
        "net_profit_realized (₹)": float(margin), "cost_used_details": cost_info, "payment_status": status,
        "party": party if party.strip() != "" else "N/A"
    })
    json.dump(txs, open(LOG_FILE, "w"), indent=4)

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
    save_inventory(fresh_inv)
    json.dump(txs, open(LOG_FILE, "w"), indent=4)
    st.session_state.inventory_data = fresh_inv

# --- SECURITY ENGINE ---
auth_data = load_auth()
if "logged_in" not in st.session_state: 
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    _, center_col, _ = st.columns([1, 1.4, 1])
    with center_col:
        st.markdown('<div class="clean-login-card">', unsafe_allow_html=True)
        st.markdown("<h1>🍃 NAGBARI TRADERS</h1>", unsafe_allow_html=True)
        input_pwd = st.text_input("Admin Password", type="password", key="login_pwd_input")
        login_btn = st.button("Login 🔓", use_container_width=True)
        
        if login_btn or (input_pwd != "" and input_pwd == auth_data["password"]):
            if input_pwd == auth_data["password"]:
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("❌ Incorrect Password Entry")
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

if "inventory_data" not in st.session_state: st.session_state.inventory_data = load_inventory()
current_inventory = st.session_state.inventory_data
transactions_history = load_transactions()

# --- LIVE METRICS INTERPRETER ---
prof = sum(float(x.get("net_profit_realized (₹)", 0)) for x in transactions_history if x.get("type") == "SALE (Stock Out)")
recv = sum(float(x.get("total_amount (₹)", 0)) for x in transactions_history if x.get("type") == "SALE (Stock Out)" and x.get("payment_status") == "CREDIT")
coll = sum(float(x.get("total_amount (₹)", 0)) for x in transactions_history if x.get("type") == "CUSTOMER PAYMENT (Money Received)")
receivables = max(0.0, recv - coll)

payb = sum(float(x.get("total_amount (₹)", 0)) for x in transactions_history if x.get("type") == "PURCHASE (Stock In)" and x.get("payment_status") == "CREDIT")
sett = sum(float(x.get("total_amount (₹)", 0)) for x in transactions_history if x.get("type") == "SUPPLIER PAYMENT (Money Paid)")
payables = max(0.0, payb - sett)

c_in = sum(float(x.get("total_amount (₹)", 0)) for x in transactions_history if x.get("type") in ["SALE (Stock Out)", "CUSTOMER PAYMENT (Money Received)"] and x.get("payment_status") == "CASH")
c_out = sum(float(x.get("total_amount (₹)", 0)) for x in transactions_history if x.get("type") in ["PURCHASE (Stock In)", "SUPPLIER PAYMENT (Money Paid)"] and x.get("payment_status") == "CASH")
cash_flow = c_in - c_out

b_in = sum(float(x.get("total_amount (₹)", 0)) for x in transactions_history if x.get("type") in ["SALE (Stock Out)", "CUSTOMER PAYMENT (Money Received)"] and x.get("payment_status") == "BANK")
b_out = sum(float(x.get("total_amount (₹)", 0)) for x in transactions_history if x.get("type") in ["PURCHASE (Stock In)", "SUPPLIER PAYMENT (Money Paid)"] and x.get("payment_status") == "BANK")
bank_flow = b_in - b_out

# --- SIDEBAR CONFIGURATION ---
with st.sidebar:
    st.header("⚙️ Settings")
    st.info(f"👤 **Logged in as:**\n{OWNER_EMAIL}")
    
    with st.expander("🚨 Master System Reset", expanded=False):
        st.warning("This completely deletes all history and resets stock to 0.")
        confirm_text = st.text_input("Type 'RESET' to authorize:")
        if st.button("WIPE LEDGER NOW 💥", use_container_width=True):
            if confirm_text == "RESET":
                if os.path.exists(LOG_FILE): os.remove(LOG_FILE)
                for k in current_inventory: current_inventory[k]["batches"] = []
                save_inventory(current_inventory)
                st.session_state.inventory_data = current_inventory
                st.success("System completely wiped!")
                st.rerun()
            else: st.error("Incorrect text entry.")

    with st.expander("🔐 Password Configuration"):
        if "otp_sent" not in st.session_state: st.session_state.otp_sent = False
        if not st.session_state.otp_sent:
            if st.button("Send OTP 📧", use_container_width=True):
                otp = str(random.randint(1000, 9999))
                if send_otp_email(OWNER_EMAIL, otp):
                    st.session_state.generated_otp, st.session_state.otp_sent = otp, True
                    st.rerun()
        else:
            otp_in = st.text_input("4-Digit OTP", max_chars=4)
            pwd_in = st.text_input("New Password", type="password")
            if st.button("Save ✅", use_container_width=True) and otp_in == st.session_state.generated_otp and pwd_in.strip():
                save_auth(pwd_in.strip())
                st.session_state.otp_sent = False
                st.success("Saved!")
    if st.button("Logout 🔒", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()

# --- MAIN DASHBOARD INTERFACE ---
st.markdown("<h1>🍃 NAGBARI TRADERS</h1>", unsafe_allow_html=True)

# Compact Summary Row (Scrolls horizontally natively on narrow phones)
with st.container():
    t_c1, t_c2, t_c3, t_c4, t_c5, t_c6 = st.columns(6)
    tot_stk = sum(sum(b["qty"] for b in item.get("batches", [])) for item in current_inventory.values())
    with t_c1: st.metric("Stock Balance", f"{tot_stk:,} KG")
    with t_c2: st.metric("Profit 💰", f"₹{round(prof, 2):,}")
    with t_c3: st.metric("Receivables 📈", f"₹{round(receivables, 2):,}")
    with t_c4: st.metric("Payables 📉", f"₹{round(payables, 2):,}")
    with t_c5: st.metric("Cash Box 💵", f"₹{round(cash_flow, 2):,}")
    with t_c6: st.metric("Bank Position 🏦", f"₹{round(bank_flow, 2):,}")

st.write("---")

# UPGRADE: Drawers (Expanders) to clear up vertical height on smartphones
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

with st.expander("💰 **Drawer: Log Direct Cash/Bank Adjustment**", expanded=False):
    a_c1, a_c2 = st.columns(2)
    with a_c1: 
        c_tx_type = st.radio("Direction Mode", ["CUSTOMER PAYMENT (Money Received)", "SUPPLIER PAYMENT (Money Paid)"])
        adj_amt = st.number_input("Amount Balance (₹)", min_value=1.0, value=5000.0)
    with a_c2:
        adj_mode = st.selectbox("Account Channel", ["CASH", "BANK"])
        adj_party = st.text_input("Party Context Name")
        adj_rem = st.text_input("Remarks Summary")
    if st.button("Submit Cash Entry 💰", use_container_width=True):
        add_transaction("N/A (Pure Cash)", c_tx_type, 0, adj_amt, 0.0, adj_rem if adj_rem.strip() else "Cleared", adj_mode, adj_party)
        st.success("Cash Entry Saved!")
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
        save_inventory(current_inventory)
        add_transaction(v_name, "INITIAL STOCK", v_stk, v_cost, 0.0, "Opening", "CASH", "Opening")
        st.session_state.inventory_data = current_inventory
        st.rerun()

# --- STOCK TILES DISPLAY MATRIX ---
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
                with m1: st.metric("Available Stock", f"{tot_stk:,} KG")
                with m2: st.metric("Active Price", f"₹{dt.get('sale_price', 0.0)}")
                
                with st.expander("⚙️ Edit Settings", expanded=False):
                    new_s = st.number_input("Adjust Price (₹/KG)", min_value=0.0, value=float(dt.get('sale_price', 0.0)), step=5.0, key=f"ed_{name}")
                    new_l = st.number_input("Low Stock Warning Line (KG)", min_value=0, value=int(limit), step=25, key=f"lim_{name}")
                    if new_s != dt.get('sale_price', 0.0) or new_l != limit:
                        current_inventory[name]["sale_price"] = new_s
                        current_inventory[name]["low_stock_limit"] = new_l
                        save_inventory(current_inventory)
                        st.session_state.inventory_data = current_inventory
                        st.rerun()
else: st.info("No stock tiles to show.")

# --- TRANSACTION HISTORY LOG + DYNAMIC IN-LINE EDITING ENGINE ---
st.write("---")
st.header("📜 Recent Transactions Log")
if transactions_history:
    fl_c1, fl_c2 = st.columns(2)
    with fl_c1: search_party = st.text_input("🔎 Search by Party Name:", value="")
    with fl_c2: search_item = st.selectbox("🎯 Filter by Tea Variety:", ["ALL"] + list(current_inventory.keys()))

    filtered_txs = transactions_history
    if search_party.strip():
        filtered_txs = [t for t in filtered_txs if search_party.lower() in t.get("party", "").lower()]
    if search_item != "ALL":
        filtered_txs = [t for t in filtered_txs if t.get("item_name") == search_item]

    if filtered_txs:
        tx_options = []
        for t in filtered_txs:
            t_id = t.get("id", "legacy")
            lbl = f"[{t.get('date')}] {t.get('type')} - {t.get('item_name')} ({t.get('quantity')} KG) - Party: {t.get('party')}"
            tx_options.append((t_id, lbl))
            
        with st.expander("🔧 **Tap to Open Live Transaction Editor Panel**", expanded=False):
            sel_tx_id = st.selectbox("Pick an entry to modify or delete:", options=[x[0] for x in tx_options], format_func=lambda x: next(y[1] for y in tx_options if y[0] == x))
            target_tx = next(x for x in transactions_history if x.get("id", "legacy") == sel_tx_id)
            
            st.markdown(f"#### 📝 Modifying Transaction ID `#{target_tx.get('id')}`")
            ed_col1, ed_col2 = st.columns(2)
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
                    target_tx["total_amount (₹)"] = int(new_qty) * float(new_rate) if int(new_qty) > 0 else float(new_rate)
                    
                    json.dump(transactions_history, open(LOG_FILE, "w"), indent=4)
                    rebuild_inventory_and_metrics_from_scratch()
                    st.success("Changes saved! Live financial metrics updated.")
                    st.rerun()
            with btn_void:
                if st.button("Void / Erase Record ❌", use_container_width=True):
                    transactions_history = [x for x in transactions_history if x.get("id", "legacy") != sel_tx_id]
                    json.dump(transactions_history, open(LOG_FILE, "w"), indent=4)
                    rebuild_inventory_and_metrics_from_scratch()
                    st.success("Record voided cleanly!")
                    st.rerun()
                    
    # UPGRADE: UI List-style rendering with color-coded HTML badges for mobile viewing
    st.write("### 📱 Mobile-Scannable Ledger List")
    display_list = filtered_txs if filtered_txs else transactions_history
    
    for tx in display_list[:25]: # Show recent 25 items for loading speed
        mode = tx.get("payment_status", "CASH")
        if mode == "CASH": badge = '<span class="badge-cash">💵 CASH</span>'
        elif mode == "BANK": badge = '<span class="badge-bank">🏦 BANK</span>'
        else: badge = '<span class="badge-credit">⏳ CREDIT</span>'
        
        type_str = tx.get("type", "")
        amt_formatted = f"₹{tx.get('total_amount (₹)', 0.0):,}"
        
        # Determine green/red highlight text based on transaction direction
        if "SALE" in type_str or "RECEIVED" in type_str:
            amt_display = f"<span style='color:#16a34a; font-weight:bold; font-size:1.1rem;'>+{amt_formatted}</span>"
        else:
            amt_display = f"<span style='color:#dc2626; font-weight:bold; font-size:1.1rem;'>-{amt_formatted}</span>"
            
        qty_info = f" • {tx.get('quantity')} KG" if tx.get('quantity', 0) > 0 else ""
        
        st.markdown(f"""
        <div style="background-color: white; padding: 12px; border-radius: 8px; border: 1px solid #e2e8f0; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center;">
            <div>
                <div style="font-weight: 600; color: #1e293b; font-size:0.95rem;">{tx.get('party')}</div>
                <div style="font-size: 0.8rem; color: #64748b;">{tx.get('date')} • {tx.get('item_name')}{qty_info}</div>
                <div style="margin-top: 4px;">{badge} <span style="font-size: 0.8rem; color: #475569; margin-left: 6px;">{type_str}</span></div>
            </div>
            <div style="text-align: right;">
                {amt_display}
                <div style="font-size: 0.75rem; color: #94a3b8;">ID: #{tx.get('id')}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
else:
    st.info("No transactions logged yet.")
