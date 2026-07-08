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

# --- LOAD DATA FUNCTIONS WITH BATCH MIGRATION ---
def load_inventory():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f: 
            data = json.load(f)
            # Ensure old data structures are migrated to use batches
            for item in data:
                if "batches" not in data[item]:
                    # Create an initial batch using their existing stock and price
                    stock = data[item].get("stock", 0)
                    price = data[item].get("purchase_price", 200.0)
                    data[item]["batches"] = [{"qty": stock, "cost": price}] if stock > 0 else []
                if "sale_price" not in data[item]:
                    data[item]["sale_price"] = data[item].get("price", 250.0)
            return data
    return {
        "Assam CTC Tea": {
            "sale_price": 250.0,
            "color": "#bef264",
            "batches": [{"qty": 1000, "cost": 200.0}]
        }
    }

def save_inventory(updated_inventory):
    with open(DATA_FILE, "w") as f: json.dump(updated_inventory, f, indent=4)

def load_transactions():
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f: return json.load(f)
    return []

def add_transaction(item_name, action_type, quantity, rate, margin_earned, cost_details, party_details):
    transactions = load_transactions()
    total_amount = int(quantity) * float(rate)
    new_log = {
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "item_name": item_name,
        "type": action_type,
        "quantity": int(quantity),
        "rate (₹)": float(rate),
        "total_amount (₹)": total_amount,
        "net_profit_realized (₹)": float(margin_earned),
        "cost_used_details": cost_details,
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

# --- INITIALIZE DATA ---
if "inventory_data" not in st.session_state: st.session_state.inventory_data = load_inventory()
current_inventory = st.session_state.inventory_data
transactions_history = load_transactions()

# --- TOTAL SINGLE AMOUNT PROFIT ---
realized_net_profit = sum(float(tx.get("net_profit_realized (₹)", 0)) for tx in transactions_history if tx["type"] == "SALE (Stock Out)")

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
                    st.session_state.generated_otp = otp; st.session_state.otp_sent = True; st.rerun()
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

# --- OVERVIEW METRICS ---
st.header("📊 Financial Overview")
with st.container():
    col1, col2, col3 = st.columns(3)
    
    total_stock_kg = 0
    total_asset_value = 0
    for item in current_inventory.values():
        for batch in item.get("batches", []):
            total_stock_kg += batch["qty"]
            total_asset_value += (batch["qty"] * batch["cost"])
            
    with col1: st.metric(label="Total Physical Stock Balance", value=f"{total_stock_kg:,} KG")
    with col2: st.metric(label="Inventory Asset Cost Value", value=f"₹{round(total_asset_value, 2):,}")
    with col3: st.metric(label="Total Accumulated Profit (Single Amount) 💰", value=f"₹{round(realized_net_profit, 2):,}")

# --- LOG TRANSACTION SECTION (BATCH TRACKING ENGINE) ---
st.write("---")
st.header("📝 Log New Transaction")
with st.container():
    tx_col1, tx_col2, tx_col3, tx_col4 = st.columns([1.5, 1, 1, 1.5])
    with tx_col1: selected_item = st.selectbox("Select Tea Variety", list(current_inventory.keys()))
    with tx_col2: transaction_type = st.radio("Action Type", ["PURCHASE (Stock In)", "SALE (Stock Out)"])
    with tx_col3: tx_quantity = st.number_input("Quantity (KG)", min_value=1, value=100, step=50)
    
    # Set default rates
    batches_list = current_inventory[selected_item].get("batches", [])
    current_total_stock = sum(b["qty"] for b in batches_list)
    latest_cost = batches_list[-1]["cost"] if len(batches_list) > 0 else 0.0
    default_rate = latest_cost if transaction_type == "PURCHASE (Stock In)" else current_inventory[selected_item]["sale_price"]
    
    with tx_col4: 
        tx_rate = st.number_input("Transaction Rate (₹/KG)", min_value=0.0, value=float(default_rate), step=5.0, key=f"tx_rate_{selected_item}_{transaction_type}")
        party_info = st.text_input("Party / Supplier Name", placeholder="e.g., Balaji Traders")
        
    if st.button("Submit Transaction ⚡", use_container_width=True):
        item_data = current_inventory[selected_item]
        margin_earned = 0.0
        cost_details_str = ""
        
        if transaction_type == "SALE (Stock Out)" and tx_quantity > current_total_stock:
            st.error(f"❌ Low Stock Alert! You only have {current_total_stock} KG left in total batches.")
        else:
            if transaction_type == "PURCHASE (Stock In)":
                # Add a completely separate clean batch
                if "batches" not in item_data: item_data["batches"] = []
                item_data["batches"].append({"qty": int(tx_quantity), "cost": float(tx_rate)})
                cost_details_str = f"Added new batch @ ₹{tx_rate}/KG"
            else:
                # FIFO Batch Sales Deduction Logic
                remaining_to_sell = int(tx_quantity)
                cost_breakdown = []
                
                while remaining_to_sell > 0 and len(item_data["batches"]) > 0:
                    oldest_batch = item_data["batches"][0]
                    
                    if oldest_batch["qty"] <= remaining_to_sell:
                        # Use up this entire batch
                        qty_taken = oldest_batch["qty"]
                        batch_cost = oldest_batch["cost"]
                        margin_earned += (float(tx_rate) - float(batch_cost)) * qty_taken
                        cost_breakdown.append(f"{qty_taken}KG from batch @ ₹{batch_cost}")
                        
                        remaining_to_sell -= qty_taken
                        item_data["batches"].pop(0) # Remove used batch
                    else:
                        # Deduct partially from this batch
                        qty_taken = remaining_to_sell
                        batch_cost = oldest_batch["cost"]
                        margin_earned += (float(tx_rate) - float(batch_cost)) * qty_taken
                        cost_breakdown.append(f"{qty_taken}KG from batch @ ₹{batch_cost}")
                        
                        oldest_batch["qty"] -= remaining_to_sell
                        remaining_to_sell = 0
                
                cost_details_str = ", ".join(cost_breakdown)
                
            save_inventory(current_inventory)
            add_transaction(selected_item, transaction_type, tx_quantity, tx_rate, margin_earned, cost_details_str, party_info)
            st.session_state.inventory_data = current_inventory
            st.success("Ledger adjusted and separate batches mapped seamlessly!")
            st.rerun()

# --- ADD VARIETY ---
with st.expander("➕ Add Entirely New Tea Variety to Inventory", expanded=False):
    add_col1, add_col2, add_col3, add_col4 = st.columns([1.5, 1, 1, 1])
    with add_col1: new_item_name = st.text_input("Tea Variety Name")
    with add_col2: new_item_stock = st.number_input("Opening Stock (KG)", min_value=0, value=0, step=50)
    with add_col3: new_item_p_price = st.number_input("Initial Batch Cost (₹/KG)", min_value=0.0, value=0.0, step=10.0)
    with add_col4: new_item_s_price = st.number_input("Target Sale Rate (₹/KG)", min_value=0.0, value=0.0, step=10.0)
    
    if st.button("Add Variety ✨", use_container_width=True):
        if new_item_name.strip() != "" and new_item_name not in current_inventory:
            batches = [{"qty": int(new_item_stock), "cost": float(new_item_p_price)}] if new_item_stock > 0 else []
            current_inventory[new_item_name] = {
                "sale_price": new_item_s_price, "color": "#cbd5e1", "batches": batches
            }
            save_inventory(current_inventory)
            add_transaction(new_item_name, "INITIAL STOCK", new_item_stock, new_item_p_price, 0.0, "Opening Inventory Batch", "Opening Inventory")
            st.session_state.inventory_data = current_inventory
            st.rerun()

# --- DETAILS GRID SHOWING SEPARATE COST BATCHES ---
st.header("📦 Current Stock & Batch Breakdown Matrix")
grid_col1, grid_col2 = st.columns(2)
item_index = 0
for item_name in list(current_inventory.keys()):
    data = current_inventory[item_name]
    current_grid_col = grid_col1 if item_index % 2 == 0 else grid_col2
    item_index += 1
    
    batches_list = data.get("batches", [])
    total_item_stock = sum(b["qty"] for b in batches_list)
    
    with current_grid_col:
        with st.container(border=True):
            card_head_col1, card_head_col2 = st.columns([4, 1])
            with card_head_col1: st.markdown(f"### {item_name}")
            with card_head_col2:
                if st.button("🗑️", key=f"del_{item_name}", use_container_width=True):
                    del current_inventory[item_name]; save_inventory(current_inventory)
                    st.session_state.inventory_data = current_inventory; st.rerun()
            
            # Show separate active costs
            st.markdown("**📋 Live Unsold Batches in Warehouse:**")
            if len(batches_list) == 0:
                st.write("*Out of Stock*")
            else:
                for idx, b in enumerate(batches_list):
                    st.write(f"• **Batch #{idx+1}:** {b['qty']:,} KG remaining @ **₹{b['cost']}/KG**")
            
            st.write("---")
            m1, m2 = st.columns(2)
            with m1: st.metric(label="Total Physical Stock", value=f"{total_item_stock:,} KG")
            with m2: st.metric(label="Base Target Selling Price", value=f"₹{data['sale_price']}")
            
            new_s = st.number_input("Update Target Selling Price (₹/KG)", min_value=0.0, value=float(data["sale_price"]), step=5.0, key=f"edit_s_{item_name}")
            if new_s != data["sale_price"]:
                current_inventory[item_name]["sale_price"] = new_s
                save_inventory(current_inventory); st.session_state.inventory_data = current_inventory; st.rerun()

# --- HISTORY LOG SHOWING ACCURATE SEPARATE COST BREAKDOWN ---
st.write("---")
st.header("📜 Recent Transactions History Log")
if len(transactions_history) > 0:
    df_logs = pd.DataFrame(transactions_history)
    df_logs = df_logs[["date", "item_name", "type", "quantity", "rate (₹)", "total_amount (₹)", "net_profit_realized (₹)", "cost_used_details", "party"]]
    df_logs.columns = ["Timestamp", "Tea Variety", "Type", "Qty (KG)", "Rate Used (₹)", "Total Value (₹)", "Profit (Single Amount ₹)", "Exact Cost Source Details", "Party / Details"]
    st.dataframe(df_logs, use_container_width=True, hide_index=True)