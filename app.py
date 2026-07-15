import streamlit as st
import json, os, random, smtplib, glob, pandas as pd
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
        margin-top: 15vh !important;
        width: 100% !important;
    }
    
    /* Mobile optimization rules for tight spacing */
    @media (max-width: 768px) {
        .clean-login-card { margin-top: 10vh !important; }
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
    .badge-expense { background-color: #fee2e2; color: #991b1b; padding: 4px 8px; border-radius: 6px; font-weight: 600; font-size: 0.8rem; }
</style>""", unsafe_allow_html=True)

DATA_FILE, LOG_FILE, AUTH_FILE = "tea_stock_data.json", "transaction_log.json", "auth_config.json"
BACKUP_DIR = "backups"
OWNER_EMAIL = "your-email@gmail.com" 

# --- AUTOMATED BACKUP ENGINE ---
def run_auto_backup():
    """Runs a rolling, daily background backup to prevent data loss."""
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)
        
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    if os.path.exists(LOG_FILE):
        log_backup_path = os.path.join(BACKUP_DIR, f"tx_log_{today_str}.json")
        if not os.path.exists(log_backup_path):
            with open(LOG_FILE, 'r') as src, open(log_backup_path, 'w') as dest:
                dest.write(src.read())
                
    if os.path.exists(DATA_FILE):
        stock_backup_path = os.path.join(BACKUP_DIR, f"stock_{today_str}.json")
        if not os.path.exists(stock_backup_path):
            with open(DATA_FILE, 'r') as src, open(stock_backup_path, 'w') as dest:
                dest.write(src.read())

    for prefix in ["tx_log_", "stock_"]:
        files = sorted(glob.glob(os.path.join(BACKUP_DIR, f"{prefix}*.json")))
        if len(files) > 5:
            for old_file in files[:-5]:
                try: os.remove(old_file)
                except: pass

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
    run_auto_backup()

def load_transactions():
    return json.load(open(LOG_FILE, "r")) if os.path.exists(LOG_FILE) else []

def add_transaction(item, t_type, qty, rate, margin, cost_info, status, party):
    txs = load_transactions()
    amt = int(qty) * float(rate) if qty > 0 else float(rate)
    clean_party = party.strip() if party.strip() != "" else "N/A"
    txs.insert(0, {
        "id": str(random.randint(100000, 999999)),
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"), "item_name": item, "type": t_type,
        "quantity": int(qty), "rate (₹)": float(rate) if qty > 0 else 0.0, "total_amount (₹)": amt,
        "net_profit_realized (₹)": float(margin), "cost_used_details": cost_info, "payment_status": status,
        "party": clean_party
    })
    json.dump(txs, open(LOG_FILE, "w"), indent=4)
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
        
        # --- NEW EMERGENCY EMERGENCY BYPASS RESET BUTTON ---
        st.write("---")
        if st.button("🔄 Reset Password to 'admin'", use_container_width=True, help="Click if your current password isn't working."):
            save_auth("admin")
            st.success("Password successfully reset back to 'admin'! Please clear the field above and log in.")
            st.rerun()
            
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

if "inventory_data" not in st.session_state: st.session_state.inventory_data = load_inventory()
current_inventory = st.session_state.inventory_data
transactions_history = load_transactions()

run_auto_backup()

# --- PARTY-WISE LEDGER BALANCE CALCULATOR ---
customer_credit_map = {}
supplier_credit_map = {}

for tx in reversed(transactions_history):
    pty = tx.get("party", "N/A")
    if pty == "N/A" or pty == "Opening": continue
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

# --- LIVE METRICS INTERPRETER ---
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

# --- SIDEBAR CONFIGURATION ---
with st.sidebar:
    st.header("⚙️ Settings")
    st.info(f"👤 **Logged in as:**\n{OWNER_EMAIL}")
    
    with st.expander("💾 System Backup Manager", expanded=False):
        st.write("📁 **Storage Location:** `/backups`")
        found_backups = sorted(glob.glob(os.path.join(BACKUP_DIR, "tx_log_*.json")))
        if found_backups:
            st.success(f"Active Rolling Backups: **{len(found_backups)} Days Saved**")
            for f_path in reversed(found_backups):
                st.write(f"• {os.path.basename(f_path).replace('tx_log_', '').replace('.json', '')}")
        else:
            st.write("*No archive files found yet.*")
    
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

tot_stk = sum(sum(b["qty"] for b in item.get("batches", [])) for item in current_inventory.values())

st.markdown(f"""
<div style="
    display: grid; 
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); 
    gap: 12px; 
    margin-bottom: 15px;
">
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

# Drawers (Expanders) to clear up vertical height on smartphones
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

# Account Ledger Matching Engine
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
            else:
                selected_party = st.text_input("Type Customer Name (No active credit records found)")
        else:
            party_options = list(active_creditors.keys())
            if party_options:
                format_func = lambda x: f"🏢 {x} (You Owe: ₹{active_creditors[x]:,})"
                selected_party = st.selectbox("Select Supplier to Pay", options=party_options, format_func=format_func)
            else:
                selected_party = st.text_input("Type Supplier Name (No active balance records found)")
                
        adj_rem = st.text_input("Remarks Summary", placeholder="e.g., Partial payment / Final settlement")
        
    if st.button("Submit Ledger Entry 💰", use_container_width=True):
        if not selected_party or selected_party.strip() == "":
            st.error("❌ Please provide or select a valid Party Name.")
        else:
            add_transaction("N/A (Pure Cash)", c_tx_type, 0, adj_amt, 0.0, adj_rem if adj_rem.strip() else "Cleared via Ledger Entry", adj_mode, selected_party)
            st.success(f"Payment entry parsed! Outstanding dues for {selected_party} automatically scaled down.")
            st.rerun()

with st.expander("💸 **Drawer: Log Business Expenses (Rent, Labor, Freight)**", expanded=False):
    ex_c1, ex_c2 = st.columns(2)
    with ex_c1:
        ex_cat = st.selectbox("Expense Category", ["Warehouse Rent", "Labor Wages", "Freight / Transport", "Brokerage Commission", "Office Supplies & Miscellaneous"])
        ex_amt = st.number_input("Expense Amount (₹)", min_value=1.0, value=1000.0, step=500.0)
    with ex_c2:
        ex_mode = st.selectbox("Paid From Channel", ["CASH", "BANK"])
        ex_notes = st.text_input("Additional Notes (e.g. Truck Number, Month)")
        
    if st.button("Log Expense Record 💥", use_container_width=True):
        add_transaction(
            item="Business Operation Cost", t_type="BUSINESS EXPENSE", qty=0, rate=ex_amt,
            margin=0.0, cost_info=ex_cat, status=ex_mode, party=ex_notes if ex_notes.strip() else "General Operational Cost"
        )
        st.success(f"Successfully logged ₹{ex_amt:,} under {ex_cat}!")
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

# --- PARTY OUTSTANDING BALANCES VIEW ---
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
    with fl_c1: search_party = st.text_input("🔎 Search by Party/Notes Name:", value="")
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
                "Date & Time": t.get("date"),
                "Transaction Type": t.get("type"),
                "Product/Item": t.get("item_name"),
                "Party/Details": t.get("party"),
                "Quantity (KG)": t.get("quantity", 0),
                "Rate (₹/KG)": t.get("rate (₹)", 0.0),
                "Total Amount (₹)": t.get("total_amount (₹)", 0.0),
                "Payment Mode": t.get("payment_status"),
                "Profit Realized (₹)": t.get("net_profit_realized (₹)", 0.0)
            })
        df_download = pd.DataFrame(download_data)
        csv_buffer = df_download.to_csv(index=False).encode('utf-8')
        
        st.download_button(
            label="📥 Download Filtered Ledger Table (CSV File)",
            data=csv_buffer,
            file_name=f"Nagbari_Ledger_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
            use_container_width=True
        )
        
        tx_options = []
        for t in filtered_txs:
            t_id = t.get("id", "legacy")
            if t.get("type") == "BUSINESS EXPENSE":
                lbl = f"[{t.get('date')}] 💸 EXPENSE: {t.get('cost_used_details')} - ₹{t.get('total_amount (₹)')} ({t.get('party')})"
            else:
                lbl = f"[{t.get('date')}] {t.get('type')} - {t.get('item_name')} ({t.get('quantity')} KG) - Party: {t.get('party')}"
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
                    target_tx["total_amount (₹)"] = int(new_qty) * float(new_rate) if int(new_qty) > 0 else float(new_rate)
                    
                    json.dump(transactions_history, open(LOG_FILE, "w"), indent=4)
                    rebuild_inventory_and_metrics_from_scratch()
                    st.success("Changes saved! Live financial metrics updated.")
                    st.rerun()
            
            with btn_void:
                if st.button("Delete / Void Entry 🗑️", use_container_width=True):
                    updated_txs = [t for t in transactions_history if t.get("id", "legacy") != sel_tx_id]
                    json.dump(updated_txs, open(LOG_FILE, "w"), indent=4)
                    rebuild_inventory_and_metrics_from_scratch()
                    st.warning("Transaction removed! Catalog state recalculating...")
                    st.rerun()
else:
    st.info("No transaction tiles to show.")
