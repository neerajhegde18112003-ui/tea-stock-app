import streamlit as st
import json
import os
import random
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
import pandas as pd

# --- MODERN THEME CONFIGURATION ---
st.set_page_config(page_title="Nagbari Traders", page_icon="🍃", layout="wide")

st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] > .main { background-color: #f8fafc; }
    [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"] > div > div > div > div {
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.08);
        background-color: white;
        padding: 20px !important;
        border: 1px solid #e2e8f0;
        margin-bottom: 12px;
    }
    h1 { font-size: 2.2rem !important; color: #166534; font-weight: 700; text-align: center; margin-bottom: 0px; }
    h2 { font-size: 1.4rem !important; color: #1e293b; font-weight: 600; margin-top: 1rem !important; margin-bottom: 0.5rem !important;}
    h3 { font-size: 1.3rem !important; font-weight: 700; margin: 0px !important; }
    </style>
""", unsafe_allow_html=True)

# File paths
DATA_FILE = "tea_stock_data.json"
LOG_FILE = "transaction_log.json"
AUTH_FILE = "auth_config.json"

# --- OWNER CONFIGURATION ---
OWNER_EMAIL = "neerajhegde547@gmail.com" 

# --- SECURITY FUNCTIONS ---
def load_auth():
    if os.path.exists(AUTH_FILE):
        with open(AUTH_FILE, "r") as f: return json.load(f)
    return {"password": "admin"}

def save_auth(password):
    with open(AUTH_FILE, "w") as f: json.dump({"password": password}, f)

def send_otp_email(to_email, otp_code):
    try:
        gmail_user = st.secrets["email"]["gmail_user"]
        gmail_password = st.secrets["email"]["gmail_password"]
        msg = MIMEText(f"Your 4-Digit OTP for changing Nagbari Traders Admin Password is: {otp_code}")
        msg['Subject'] = "🔒 Nagbari Traders Security OTP"
        msg['From'] = gmail_user
        msg['To'] = to_email
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(gmail_user, gmail_password)
        server.sendmail(gmail_user, to_email, msg.as_string())
        server.close()
        return True
    except Exception as e:
        st.error(f"Failed to send email. Error: {e}")
        return False

# --- DATA FUNCTIONS ---
def load_inventory():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f: 
            data = json.load(f)
            for item in data:
                if "batches" not in data[item]:
                    stock = data[item].get("stock", 0)
                    price = data[item].get("purchase_price", 200.0)
                    data[item]["batches"] = [{"qty": stock, "cost": price}] if stock > 0 else []
                if "sale_price" not in data[item]:
                    data[item]["sale_price"] = data[item].get("price", 250.0)
            return data
    return {"Assam CTC Tea": {"sale_price": 250.0, "color": "#bef264", "batches": [{"qty": 1000, "cost": 200.0}]}}

def save_inventory(updated_inventory):
    with open(DATA_FILE, "w") as f: json.dump(updated_inventory, f, indent=4)

def load_transactions():
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f: return json.load(f)
    return []

def add_transaction(item_name, action_type, quantity, rate, margin_earned, cost_details, payment_status, party_details):
    transactions = load_transactions()
    total_amount = int(quantity) * float(rate) if quantity > 0 else float(rate)
    new_log = {
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "item_name": item_name,
        "type": action_type,
        "quantity": int(quantity),
        "rate (₹)": float(rate) if quantity > 0 else 0.0,
        "total_amount (₹)": total_amount,
        "net_profit_realized (₹)": float(margin_earned),
        "cost_used_details": cost_details,
        "payment_status": payment_status,
        "party": party_details if party_details.strip() != "" else "N/A"
    }
    transactions.insert(0, new_log)
    with open(LOG_FILE, "w") as f: json.dump(transactions, f, indent=4)

# --- LOGIN PROTECTION ---
auth_data = load_auth()
if "logged_in" not in st.session_state: st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.markdown("<h1 style='text-align: center; color: #166534; font-weight: 700; margin-top: 5rem;'>🍃 NAGBARI TRADERS</h1>", unsafe_allow_html=True)
    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        with st.container(border=True):
            user_pass = st.text_input("Enter Admin Password", type="password")
            if st.button("Login 🔓", use_container_width=True):
                if user_pass == auth_data["password"]: st.session_state.logged_in = True; st.rerun()
                else: st.error("❌ Incorrect Password.")
    st.stop()

# --- INITIALIZE DATA ---
if "inventory_data" not in st.session_state: st.session_state.inventory_data = load_inventory()
current_inventory = st.session_state.inventory_data
transactions_history = load_transactions()

# --- FINANCIAL ADVANCED LEDGER MATHS ---
realized_net_profit = sum(float(tx.get("net_profit_realized (₹)", 0)) for tx in transactions_history if tx["type"] == "SALE (Stock Out)")

# Accounts Receivable calculations (Sales Credit minus Collections received later)
base_receivable = sum(float(tx["total_amount (₹)"]) for tx in transactions_history if tx["type"] == "SALE (Stock Out)" and tx.get("payment_status") == "CREDIT")
collections_received = sum(float(tx["total_amount (₹)"]) for tx in transactions_history if tx["type"] == "CUSTOMER PAYMENT (Money Received)")
accounts_receivable = max(0.0, base_receivable - collections_received)

# Accounts Payable calculations (Purchases Credit minus Payouts settled later)
base_payable = sum(float(tx["total_amount (₹)"]) for tx in transactions_history if tx["type"] == "PURCHASE (Stock In)" and tx.get("payment_status") == "CREDIT")
payouts_settled = sum(float(tx["total_amount (₹)"]) for tx in transactions_history if tx["type"] == "SUPPLIER PAYMENT (Money Paid)")
accounts_payable = max(0.0, base_payable - payouts_settled)

# Cash box position entries tracking
cash_in = sum(float(tx["total_amount (₹)"]) for tx in transactions_history if (tx["type"] == "SALE (Stock Out)" or tx["type"] == "CUSTOMER PAYMENT (Money Received)") and tx.get("payment_status") == "CASH")
cash_out = sum(float(tx["total_amount (₹)"]) for tx in transactions_history if (tx["type"] == "PURCHASE (Stock In)" or tx["type"] == "SUPPLIER PAYMENT (Money Paid)") and tx.get("payment_status") == "CASH")
net_cash_flow = cash_in - cash_out

# Bank balance position entries tracking
bank_in = sum(float(tx["total_amount (₹)"]) for tx in transactions_history if (tx["type"] == "SALE (Stock Out)" or tx["type"] == "CUSTOMER PAYMENT (Money Received)") and tx.get("payment_status") == "BANK")
bank_out = sum(float(tx["total_amount (₹)"]) for tx in transactions_history if (tx["type"] == "PURCHASE (Stock In)" or tx["type"] == "SUPPLIER PAYMENT (Money Paid)") and tx.get("payment_status") == "BANK")
net_bank_flow = bank_in - bank_out

# --- SIDEBAR PANEL ---
with st.sidebar:
    st.header("⚙️ Admin Settings")
    st.write(f"Owner: `{OWNER_EMAIL}`")
    with st.expander("🔐 Change Admin Password"):
        if "otp_sent" not in st.session_state: st.session_state.otp_sent = False
        if not st.session_state.otp_sent:
            if st.button("Request OTP to Email 📧", use_container_width=True):
                otp = str(random.randint(1000, 9999))
                if send_otp_email(OWNER_EMAIL, otp): st.session_state.generated_otp = otp; st.session_state.otp_sent = True; st.rerun()
        else:
            entered_otp = st.text_input("Enter 4-Digit OTP", max_chars=4)
            new_password_input = st.text_input("Enter New Password", type="password")
            if st.button("Verify & Save ✅", use_container_width=True):
                if entered_otp == st.session_state.generated_otp and new_password_input.strip() != "":
                    save_auth(new_password_input.strip()); st.session_state.otp_sent = False; st.success("Changed successfully!")
    if st.button("Logout 🔒", use_container_width=True): st.session_state.logged_in = False; st.rerun()

# --- HEADER APP UI ---
st.markdown("<h1>🍃 NAGBARI TRADERS</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #64748b; font-size: 1rem; margin-bottom: 1.5rem;'>Wholesale Stock Management Dashboard</p>", unsafe_allow_html=True)

# --- OVERVIEW METRICS WITH CREDIT BALANCES ---
st.header("📊 Financial Ledger Overview")
with st.container():
    top_col1, top_col2, top_col3, top_col4 = st.columns(4)
    total_stock_kg = sum(sum(b["qty"] for b in item.get("batches", [])) for item in current_inventory.values())
    
    with top_col1: st.metric(label="Total Stock Balance", value=f"{total_stock_kg:,} KG")
    with top_col2: st.metric(label="Total Accumulated Profit 💰", value=f"₹{round(realized_net_profit, 2):,}")
    with top_col3: st.metric(label="Accounts Receivable (From Customers) 📈", value=f"₹{round(accounts_receivable, 2):,}")
    with top_col4: st.metric(label="Accounts Payable (To Suppliers) 📉", value=f"₹{round(accounts_payable, 2):,}")

with st.container():
    flow_col1, flow_col2 = st.columns(2)
    with flow_col1: st.metric(label="Net Cash Box Counter 💵", value=f"₹{round(net_cash_flow, 2):,}", delta="Physical Cash On Hand")
    with flow_col2: st.metric(label="Net Bank Balance Position 🏦", value=f"₹{round(net_bank_flow, 2):,}", delta="Digital Funds (UPI/NEFT)")

# --- MAIN FORM MANAGEMENT TABS ---
st.write("---")
tab1, tab2 = st.tabs(["📝 Log Stock Transaction (Goods)", "💰 Log Pure Cash Payment (No Goods)"])

with tab1:
    st.subheader("Record Purchases & Sales of Tea")
    with st.container():
        tx_col1, tx_col2, tx_col3, tx_col4 = st.columns([1.5, 1, 1, 1.5])
        with tx_col1: selected_item = st.selectbox("Select Tea Variety", list(current_inventory.keys()))
        with tx_col2: transaction_type = st.radio("Action Type", ["PURCHASE (Stock In)", "SALE (Stock Out)"])
        with tx_col3: tx_quantity = st.number_input("Quantity (KG)", min_value=1, value=100, step=50)
        
        batches_list = current_inventory[selected_item].get("batches", [])
        current_total_stock = sum(b["qty"] for b in batches_list)
        latest_cost = batches_list[-1]["cost"] if len(batches_list) > 0 else 0.0
        default_rate = latest_cost if transaction_type == "PURCHASE (Stock In)" else current_inventory[selected_item]["sale_price"]
        
        with tx_col4: 
            tx_rate = st.number_input("Transaction Rate (₹/KG)", min_value=0.0, value=float(default_rate), step=5.0, key=f"tx_rate_{selected_item}_{transaction_type}")
            pay_status = st.selectbox("Payment Mode", ["CASH (Hand-to-Hand Cash)", "BANK (UPI/NEFT/Cheque)", "CREDIT (Outstanding Balance)"], key="goods_pay_mode")
            party_info = st.text_input("Party / Supplier Name", placeholder="e.g., Balaji Traders", key="goods_party")
            
        if st.button("Submit Transaction ⚡", use_container_width=True):
            item_data = current_inventory[selected_item]
            margin_earned = 0.0; cost_details_str = ""
            status_clean = "CASH" if "CASH" in pay_status else "BANK" if "BANK" in pay_status else "CREDIT"
            
            if transaction_type == "SALE (Stock Out)" and tx_quantity > current_total_stock:
                st.error(f"❌ Low Stock Alert! You only have {current_total_stock} KG left.")
            else:
                if transaction_type == "PURCHASE (Stock In)":
                    if "batches" not in item_data: item_data["batches"] = []
                    item_data["batches"].append({"qty": int(tx_quantity), "cost": float(tx_rate)})
                    cost_details_str = f"Added new batch @ ₹{tx_