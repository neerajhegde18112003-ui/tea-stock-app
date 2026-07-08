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

DATA_FILE, LOG_FILE, AUTH_FILE = "tea_stock_data.json", "transaction_log.json", "auth_config.json"
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
        msg['From'], msg['To'] = gmail_user, to_email
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
    return {"Assam CTC Tea": {"sale_price": 250.0, "batches": [{"qty": 1000, "cost": 200.0}]}}

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
                if user_pass == auth_data["password"]: 
                    st.session_state.logged_in = True
                    st.rerun()
                else: st.error("❌ Incorrect Password.")
    st.stop()

if "inventory_data" not in st.session_state: st.session_state.inventory_data = load_inventory()
current_inventory = st.session_state.inventory_data
transactions_history = load_transactions()

# --- FINANCIAL METRICS LOGIC ---
realized_net_profit = sum(float(tx.get("net_profit_realized (₹)", 0)) for tx in transactions_history if tx.get("type") == "SALE (Stock Out)")
base_receivable = sum(float(tx.get("total_amount (₹)", 0)) for tx in transactions_history if tx.get("type") == "SALE (Stock Out)" and tx.get("payment_status") == "CREDIT")
collections_received = sum(float(tx.get("total_amount (₹)", 0)) for tx in transactions_history if tx.get("type") == "CUSTOMER PAYMENT (Money Received)")
accounts_receivable = max(0.0, base_receivable - collections_received)

base_payable = sum(float(tx.get("total_amount (₹)", 0)) for tx in transactions_history if tx.get("type") == "PURCHASE (Stock In)" and tx.get("payment_status") == "CREDIT")
payouts_settled = sum(float(tx.get("total_amount (₹)", 0)) for tx in transactions_history if tx.get("type") == "SUPPLIER PAYMENT (Money Paid)")
accounts_payable = max(0.0, base_payable - payouts_settled)

cash_in = sum(float(tx.get("total_amount (₹)", 0)) for tx in transactions_history if (tx.get("type") == "SALE (Stock Out)" or tx.get("type") == "CUSTOMER PAYMENT (Money Received)") and tx.get("payment_status") == "CASH")
cash_out = sum(float(tx.get("total_amount (₹)", 0)) for tx in transactions_history if (tx.get("type") == "PURCHASE (Stock In)" or tx.get("type") == "SUPPLIER PAYMENT (Money Paid)") and tx.get("payment_status") == "CASH")
net_cash_flow = cash_in - cash_out

bank_in = sum(float(tx.get("total_amount (₹)", 0)) for tx in transactions_history if (tx.get("type") == "SALE (Stock Out)" or tx.get("type") == "CUSTOMER PAYMENT (Money Received)") and tx.get("payment_status") == "BANK")
bank_out = sum(float(tx.get("total_amount (₹)", 0)) for tx in transactions_history if (tx.get("type") == "PURCHASE (Stock In)" or tx.get("type") == "SUPPLIER PAYMENT (Money Paid)") and tx.get("payment_status") == "BANK")
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
                if send_otp_email(OWNER_EMAIL, otp): 
                    st.session_state.generated_otp, st.session_state.otp_sent = otp, True
                    st.rerun()
        else:
            entered_otp = st.text_input("Enter 4-Digit OTP", max_chars=4)
            new_password_input = st.text_input("Enter New Password", type="password")
            if st.button("Verify & Save ✅", use_