import streamlit as st
import json, os, random, smtplib, pandas as pd
from email.mime.text import MIMEText
from datetime import datetime

# --- MODERN THEME CONFIGURATION ---
st.set_page_config(page_title="Nagbari Traders", page_icon="🍃", layout="wide")
st.markdown("""<style>
    [data-testid="stAppViewContainer"] > .main { background-color: #f8fafc; }
    [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"] > div > div > div > div {
        border-radius: 12px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.08);
        background-color: white; padding: 20px !important; border: 1px solid #e2e8f0; margin-bottom: 12px;
    }
    h1 { font-size: 2.2rem !important; color: #166534; font-weight: 700; text-align: center; }
    h2 { font-size: 1.4rem !important; color: #1e293b; font-weight: 600; margin: 1rem 0 0.5rem 0 !important;}
    h3 { font-size: 1.3rem !important; font-weight: 700; margin: 0px !important; }
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
        return d
    return {"Assam CTC Tea": {"sale_price": 250.0, "batches": [{"qty": 1000, "cost": 200.0}]}}

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

# --- LOGIN ---
auth_data = load_auth()
if "logged_in" not in st.session_state: st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.markdown("<h1>🍃 NAGBARI TRADERS</h1>", unsafe_allow_html=True)
    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        with st.container(border=True):
            if st.text_input("Admin Password", type="password") == auth_data["password"]:
                if st.button("Login 🔓", use_container_width=True):
                    st.session_state.logged_in = True
                    st.rerun()
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

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Settings")
    with st.expander("🔐 Password"):
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
                    if "batches" not in it_
