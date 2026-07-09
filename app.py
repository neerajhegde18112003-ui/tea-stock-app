import streamlit as st
import json, os, random, smtplib, pandas as pd
from email.mime.text import MIMEText
from datetime import datetime

# --- MODERN THEME & MOBILE RESPONSIVENESS CONFIG ---
st.set_page_config(page_title="Nagbari Traders", page_icon="🍃", layout="wide")

st.markdown("""<style>
    [data-testid="stAppViewContainer"] > .main { background-color: #f8fafc; }
    .login-wrapper { display: flex; justify-content: center; align-items: center; padding-top: 8%; }
    @media (max-width: 768px) {
        [data-testid="stHorizontalBlock"] { flex-direction: row !important; flex-wrap: nowrap !important; overflow-x: auto; }
        [data-testid="stHorizontalBlock"] > div { min-width: 160px !important; flex: 1 1 auto !important; }
        .matrix-grid { display: flex !important; flex-direction: row !important; flex-wrap: wrap !important; gap: 10px !important; }
        .matrix-grid > div { flex: 1 1 calc(50% - 10px) !important; min-width: 150px !important; }
    }
    [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"] > div > div > div > div {
        border-radius: 12px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.08);
        background-color: white; padding: 18px !important; border: 1px solid #e2e8f0; margin-bottom: 12px;
    }
    h1 { font-size: 2.2rem !important; color: #166534; font-weight: 700; text-align: center; }
    h2 { font-size: 1.4rem !important; color: #1e293b; font-weight: 600; margin: 1rem 0 0.5rem 0 !important;}
    h3 { font-size: 1.25rem !important; font-weight: 700; margin: 0px !important; color: #0f172a; }
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
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"), "item_name": item, "type": t_type,
        "quantity": int(qty), "rate (₹)": float(rate) if qty > 0 else 0.0, "total_amount (₹)": amt,
        "net_profit_realized (₹)": float(margin), "cost_used_details": cost_info, "payment_status": status,
        "party": party if party.strip() != "" else "N/A"
    })
    json.dump(txs, open(LOG_FILE, "w"), indent=4)

# --- DIRECT SMOOTH LOGIN EXECUTION ---
auth_data = load_auth()
if "logged_in" not in st.session_state: st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.markdown("<h1>🍃 NAGBARI TRADERS</h1>", unsafe_allow_html=True)
    st.markdown('<div class="login-wrapper">', unsafe_allow_html=True)
    _, col, _ = st.columns([1, 1.3, 1])
    with col:
        with st.container(border=True):
            input_pwd = st.text_input("Admin Password", type="password", key="login_pwd_input")
            login_btn = st.button("Login 🔓", use_container_width=True)
            
            if (input_pwd == auth_data["password"] and input_pwd != "") or (login_btn and input_pwd == auth_data["password"]):
                st.session_state.logged_in = True
                st.rerun()
            elif (input_pwd != "" and input_pwd != auth_data["password"]) or (login_btn and input_pwd != auth_data["password"]):
                st.error("❌ Incorrect Admin Password Entry")
    st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

if "inventory_data" not in st.session_state: st.session_state.inventory_data = load_inventory()
current_inventory = st.session_state.inventory_data
transactions_history = load_transactions()

# --- METRICS CALCULATIONS ---
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
    
    # Restored Logged-in User Email display status label
    st.info(f"👤 **Logged in as:**\n{OWNER_EMAIL}")
    
    with st.expander("🚨 Master System Reset (Clear All Data)", expanded=False):
        st.warning("This completely deletes all sales history logs and sets all stock values back to 0. Perfect for final clean handover!")
        confirm_text = st.text_input("Type 'RESET' to authorize clearing database:")
        if st.button("WIPE LEDGER & STOCKS NOW 💥", use_container_width=True):
            if confirm_text == "RESET":
                if os.path.exists(LOG_FILE): os.remove(LOG_FILE)
                for k in current_inventory:
                    current_inventory[k]["batches"] = []
                save_inventory(current_inventory)
                st.session_state.inventory_data = current_inventory
                st.success("System completely wiped to 0 values!")
                st.rerun()
            else:
                st.error("Incorrect verification text entry.")

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
st.header("📊 Financial Overview")
with st.container():
    t_c1, t_c2, t_c3, t_c4 = st.columns(4)
    tot_stk = sum(sum(b["qty"] for b in item.get("batches", [])) for item in current_inventory.values())
    with t_c1: st.metric("Total Stock Balance", f"{tot_stk:,} KG")
    with t_c2: st.metric("Total Profit 💰", f"₹{round(prof, 2):,}")
    with t_c3: st.metric("Receivables 📈", f"₹{round(receivables, 2):,}")
    with t_c4: st.metric("Payables 📉", f"₹{round(payables, 2):,}")

with st.container():
    f_c1, f_c2 = st.columns(2)
    with f_c1: st.metric("Cash Box Counter 💵", f"₹{round(cash_flow, 2):,}")
    with f_c2: st.metric("Bank Position 🏦", f"₹{round(bank_flow, 2):,}")

st.write("---")
tab1, tab2 = st.tabs(["📝 Log Goods Transaction", "💰 Log Cash Payment"])

with tab1:
    st.subheader("Tea Stock Actions")
    with st.container():
        x_c1, x_c2, x_c3, x_c4 = st.columns([1.5, 1, 1, 1.5])
        with x_c1: sel_item = st.selectbox("Tea Variety", list(current_inventory.keys()))
        with x_c2: tx_type = st.radio("Action", ["PURCHASE (Stock In)", "SALE (Stock Out)"])
        with x_c3: tx_qty = st.number_input("Quantity (KG)", min_value=1, value=100, step=50)
        
        b_list = current_inventory[sel_item].get("batches", [])
        tot_item_stk = sum(b["qty"] for b in b_list)
        lat_cost = b_list[-1]["cost"] if b_list else 0.0
        def_rate = lat_cost if tx_type == "PURCHASE (Stock In)" else current_inventory[sel_item]["sale_price"]
        
        with x_c4:
            tx_rate = st.number_input("Rate (₹/KG)", min_value=0.0, value=float(def_rate), step=5.0)
            p_mode = st.selectbox("Payment Mode", ["CASH", "BANK", "CREDIT"])
            p_info = st.text_input("Party Name")
            
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

with tab2:
    st.subheader("Pure Cash Ledger Adjustments")
    with st.container():
        a_c1, a_c2, a_c3 = st.columns(3)
        with a_c1: c_tx_type = st.radio("Direction", ["CUSTOMER PAYMENT (Money Received)", "SUPPLIER PAYMENT (Money Paid)"])
        with a_c2:
            adj_amt = st.number_input("Amount (₹)", min_value=1.0, value=5000.0)
            adj_mode = st.selectbox("Channel", ["CASH", "BANK"])
        with a_c3:
            adj_party = st.text_input("Party")
            adj_rem = st.text_input("Remarks")
        if st.button("Submit Cash Entry 💰", use_container_width=True):
            add_transaction("N/A (Pure Cash)", c_tx_type, 0, adj_amt, 0.0, adj_rem if adj_rem.strip() else "Cleared", adj_mode, adj_party)
            st.success("Cash Entry Saved!")
            st.rerun()

# --- ADD VARIETY EXPANDER ---
with st.expander("Add New Variety"):
    v_name = st.text_input("Variety Name")
    v_stk = st.number_input("Opening Stock (KG)", min_value=0, value=0)
    v_cost = st.number_input("Cost (₹/KG)", min_value=0.0, value=0.0)
    v_sale = st.number_input("Sale Rate (₹/KG)", min_value=0.0, value=0.0)
    v_alert = st.number_input("Low Stock Warning Alert Level (KG)", min_value=0, value=100)
    if st.button("Add ✨", use_container_width=True) and v_name.strip() and v_name not in current_inventory:
        batches = [{"qty": int(v_stk), "cost": float(v_cost)}] if v_stk > 0 else []
        current_inventory[v_name] = {"sale_price": v_sale, "low_stock_limit": int(v_alert), "batches": batches}
        save_inventory(current_inventory)
        add_transaction(v_name, "INITIAL STOCK", v_stk, v_cost, 0.0, "Opening", "CASH", "Opening")
        st.session_state.inventory_data = current_inventory
        st.rerun()

# --- STOCK TILES DISPLAY MATRIX ---
st.write("---")
st.header("📦 Current Stock & Batch Breakdown Matrix")
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
                st.markdown(f"### {name} <span style='color:red; font-size:0.85rem; font-weight:bold;'>⚠️ LOW STOCK ALERT</span>", unsafe_allow_html=True)
            else:
                st.markdown(f"### {name}")
                
            if not b_list: st.write("*Out of Stock*")
            else:
                for i, b in enumerate(b_list):
                    st.write(f"• **Batch #{i+1}:** {b['qty']:,} KG remaining @ **₹{b['cost']}/KG**")
            st.write("---")
            m1, m2 = st.columns(2)
            with m1: st.metric("Total Stock", f"{tot_stk:,} KG")
            with m2: st.metric("Target Sale Rate", f"₹{dt.get('sale_price', 0.0)}")
            
            e_col1, e_col2 = st.columns(2)
            with e_col1:
                new_s = st.number_input("Edit Price (₹/KG)", min_value=0.0, value=float(dt.get('sale_price', 0.0)), step=5.0, key=f"ed_{name}")
            with e_col2:
                new_l = st.number_input("Low Stock Trigger (KG)", min_value=0, value=int(limit), step=25, key=f"lim_{name}")
                
            if new_s != dt.get('sale_price', 0.0) or new_l != limit:
                current_inventory[name]["sale_price"] = new_s
                current_inventory[name]["low_stock_limit"] = new_l
                save_inventory(current_inventory)
                st.session_state.inventory_data = current_inventory
                st.rerun()

# --- RECENT LEDGER HISTORY LOG ---
st.write("---")
st.header("📜 Recent Transactions History Log")
if transactions_history:
    df = pd.DataFrame(transactions_history).rename(columns={
        "date": "Date & Time", "item_name": "Item Variety", "type": "Transaction Type",
        "quantity": "Quantity (KG)", "rate (₹)": "Rate (₹/KG)", "total_amount (₹)": "Total Value (₹)",
        "net_profit_realized (₹)": "Profit Earned (₹)", "cost_used_details": "Batch / Remarks Info",
        "payment_status": "Mode", "party": "Party Name"
    })
    st.dataframe(df[["Date & Time", "Item Variety", "Transaction Type", "Party Name", "Quantity (KG)", "Rate (₹/KG)", "Total Value (₹)", "Mode", "Profit Earned (₹)", "Batch / Remarks Info"]], use_container_width=True, hide_index=True)
else:
    st.info("No transactions logged yet.")
