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
    .field-label { font-size: 0.75rem; color: #64748b; font-weight: 600; margin-bottom: 2px; }
    </style>
""", unsafe_allow_html=True)

# File paths
DATA_FILE = "tea_stock_data.json"
LOG_FILE = "transaction_log.json"
AUTH_FILE = "auth_config.json"

# --- OWNER CONFIGURATION (CHANGE THIS TO YOUR EMAIL) ---
OWNER_EMAIL = "neerajhegde18112003@gmail.com" 

# --- SECURITY FUNCTIONS ---
def load_auth():
    if os.path.exists(AUTH_FILE):
        with open(AUTH_FILE, "r") as f:
            return json.load(f)
    return {"password": "admin"}  # Default starting password if not set

def save_auth(password):
    with open(AUTH_FILE, "w") as f:
        json.dump({"password": password}, f)

def send_otp_email(to_email, otp_code):
    try:
        # Streamlit cloud secrets system keeps these private credentials secure
        gmail_user = st.secrets["email"]["gmail_user"]
        gmail_password = st.secrets["email"]["gmail_password"]
        
        msg = MIMEText(f"Your 4-Digit OTP for changing Nagbari Traders Admin Password is: {otp_code}\n\nThis OTP will expire shortly.")
        msg['Subject'] = "🔒 Nagbari Traders Security OTP"
        msg['From'] = gmail_user
        msg['To'] = to_email
        
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(gmail_user, gmail_password)
        server.sendmail(gmail_user, to_email, msg.as_string())
        server.close()
        return True
    except Exception as e:
        st.error(f"Failed to send email. Check Streamlit secrets settings. Error: {e}")
        return False

# --- LOAD DATA FUNCTIONS ---
def load_inventory():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {"Assam CTC Tea": {"stock": 1250, "price": 240, "color": "#bef264"}}

def save_inventory(updated_inventory):
    with open(DATA_FILE, "w") as f:
        json.dump(updated_inventory, f, indent=4)

def load_transactions():
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            return json.load(f)
    return []

def add_transaction(item_name, action_type, quantity, party_details):
    transactions = load_transactions()
    new_log = {
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "item_name": item_name,
        "type": action_type,
        "quantity": int(quantity),
        "party": party_details if party_details.strip() != "" else "N/A"
    }
    transactions.insert(0, new_log)
    with open(LOG_FILE, "w") as f:
        json.dump(transactions, f, indent=4)

# --- LOGIN APP DOOR PROTECTION ---
auth_data = load_auth()
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.markdown("<h1 style='text-align: center; color: #166534; font-weight: 700; margin-top: 5rem;'>🍃 NAGBARI TRADERS</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #64748b; margin-bottom: 2rem;'>Wholesale Stock Portal Login</p>", unsafe_allow_html=True)
    
    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        with st.container(border=True):
            user_pass = st.text_input("Enter Admin Password", type="password")
            if st.button("Login 🔓", use_container_width=True):
                if user_pass == auth_data["password"]:
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error("❌ Incorrect Password. Please try again.")
    st.stop()

# --- INITIALIZE MAIN DASHBOARD DATA ---
if "inventory_data" not in st.session_state:
    st.session_state.inventory_data = load_inventory()
current_inventory = st.session_state.inventory_data

# --- HEADER APP UI ---
st.markdown("<h1>🍃 NAGBARI TRADERS</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #64748b; font-size: 1rem; margin-bottom: 1.5rem;'>Wholesale Stock Management Dashboard</p>", unsafe_allow_html=True)

# --- SIDEBAR: PASSWORD SETTINGS PANEL WITH OTP ---
with st.sidebar:
    st.header("⚙️ Admin Settings")
    st.write(f"Logged in as Owner: `{OWNER_EMAIL}`")
    
    with st.expander("🔐 Change Admin Password"):
        if "otp_sent" not in st.session_state:
            st.session_state.otp_sent = False
            st.session_state.generated_otp = None
            
        if not st.session_state.otp_sent:
            if st.button("Request OTP to Email 📧", use_container_width=True):
                otp = str(random.randint(1000, 9999))
                if send_otp_email(OWNER_EMAIL, otp):
                    st.session_state.generated_otp = otp
                    st.session_state.otp_sent = True
                    st.success("OTP sent successfully to your email!")
                    st.rerun()
        else:
            entered_otp = st.text_input("Enter 4-Digit OTP", max_chars=4)
            new_password_input = st.text_input("Enter New Password", type="password")
            
            if st.button("Verify & Save New Password ✅", use_container_width=True):
                if entered_otp == st.session_state.generated_otp:
                    if new_password_input.strip() != "":
                        save_auth(new_password_input.strip())
                        st.session_state.otp_sent = False
                        st.session_state.generated_otp = None
                        st.success("Password changed securely! Re-login next time.")
                    else:
                        st.error("Password cannot be blank.")
                else:
                    st.error("❌ Incorrect OTP code. Please check your email.")
                    
            if st.button("Cancel ❌", use_container_width=True):
                st.session_state.otp_sent = False
                st.session_state.generated_otp = None
                st.rerun()
                
    if st.button("Logout 🔒", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()

# --- OVERVIEW METRICS ---
st.header("📊 Overview")
with st.container():
    col1, col2, col3 = st.columns(3)
    total_items = len(current_inventory)
    total_stock_kg = sum(item["stock"] for item in current_inventory.values())
    total_value_inr = sum(item["stock"] * item["price"] for item in current_inventory.values())
    with col1: st.metric(label="Varieties", value=f"{total_items}")
    with col2: st.metric(label="Total Stock", value=f"{total_stock_kg:,} KG")
    with col3: st.metric(label="Total Value", value=f"₹{total_value_inr:,}")

# --- LOG TRANSACTION SECTION ---
st.write("---")
st.header("📝 Log New Transaction")
with st.container():
    tx_col1, tx_col2, tx_col3, tx_col4 = st.columns([1.5, 1, 1, 1.5])
    with tx_col1: selected_item = st.selectbox("Select Tea Variety", list(current_inventory.keys()))
    with tx_col2: transaction_type = st.radio("Action Type", ["PURCHASE (Stock In)", "SALE (Stock Out)"])
    with tx_col3: tx_quantity = st.number_input("Quantity (KG)", min_value=1, value=50, step=50)
    with tx_col4: party_info = st.text_input("Party / Supplier Name", placeholder="e.g., Balaji Traders")
        
    if st.button("Submit Transaction ⚡", use_container_width=True):
        current_stock = current_inventory[selected_item]["stock"]
        if transaction_type == "SALE (Stock Out)" and tx_quantity > current_stock:
            st.error(f"❌ Not enough stock! You only have {current_stock} KG left.")
        else:
            if transaction_type == "PURCHASE (Stock In)": current_inventory[selected_item]["stock"] += tx_quantity
            else: current_inventory[selected_item]["stock"] -= tx_quantity
            save_inventory(current_inventory)
            add_transaction(selected_item, transaction_type, tx_quantity, party_info)
            st.session_state.inventory_data = current_inventory
            st.success("Successfully processed transaction!")
            st.rerun()

# --- ADD VARIETY ---
with st.expander("➕ Add Entirely New Tea Variety to Inventory", expanded=False):
    add_col1, add_col2, add_col3 = st.columns([2, 1, 1])
    with add_col1: new_item_name = st.text_input("Tea Variety Name")
    with add_col2: new_item_stock = st.number_input("Opening Stock (KG)", min_value=0, value=0, step=50)
    with add_col3: new_item_price = st.number_input("Wholesale Rate (₹/KG)", min_value=0, value=0, step=10)
    if st.button("Add Variety ✨", use_container_width=True):
        if new_item_name.strip() != "" and new_item_name not in current_inventory:
            current_inventory[new_item_name] = {"stock": new_item_stock, "price": new_item_price, "color": "#cbd5e1"}
            save_inventory(current_inventory)
            add_transaction(new_item_name, "INITIAL STOCK", new_item_stock, "Opening Inventory")
            st.session_state.inventory_data = current_inventory
            st.success(f"Added {new_item_name}!")
            st.rerun()

# --- DETAILS GRID ---
st.header("📦 Current Stock & Pricing")
grid_col1, grid_col2 = st.columns(2)
item_index = 0
for item_name in list(current_inventory.keys()):
    data = current_inventory[item_name]
    current_grid_col = grid_col1 if item_index % 2 == 0 else grid_col2
    item_index += 1
    is_low_stock = data["stock"] < 300
    card_accent_color = "#ef4444" if is_low_stock else data.get("color", "#bef264")
    title_text_color = "#dc2626" if is_low_stock else "#111827"
    status_badge = "⚠️ LOW STOCK" if is_low_stock else "Premium Quality"
    with current_grid_col:
        with st.container(border=True):
            card_head_col1, card_head_col2 = st.columns([4, 1])
            with card_head_col1: st.markdown(f"<span style='background-color: {card_accent_color}22; color: {title_text_color}; padding: 4px 8px; border-radius: 6px; font-size: 0.8rem; font-weight: 700;'>{status_badge}</span>", unsafe_allow_html=True)
            with card_head_col2:
                if st.button("🗑️", key=f"del_{item_name}", use_container_width=True):
                    del current_inventory[item_name]
                    save_inventory(current_inventory)
                    st.session_state.inventory_data = current_inventory
                    st.rerun()
            st.markdown(f"<h3 style='margin-top: 10px; color: {title_text_color};'>{item_name}</h3>", unsafe_allow_html=True)
            metric_col1, metric_col2 = st.columns(2)
            with metric_col1: st.metric(label="Available Stock", value=f"{data['stock']:,} KG")
            with metric_col2:
                new_price = st.number_input("Price", min_value=0, value=data["price"], step=5, key=f"price_in_{item_name}")
                if new_price != data["price"]:
                    current_inventory[item_name]["price"] = new_price
                    save_inventory(current_inventory)
                    st.session_state.inventory_data = current_inventory
                    st.rerun()

# --- HISTORY LOG ---
st.write("---")
st.header("📜 Recent Transactions History Log")
log_data = load_transactions()
if len(log_data) > 0:
    df_logs = pd.DataFrame(log_data)
    df_logs.columns = ["Timestamp", "Tea Variety", "Transaction Type", "Quantity (KG)", "Party / Details"]
    st.dataframe(df_logs, use_container_width=True, hide_index=True)