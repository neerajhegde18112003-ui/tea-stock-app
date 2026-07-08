import streamlit as st

# --- MODERN THEME CONFIGURATION ---
st.set_page_config(
    page_title="Nagbari Traders",
    page_icon="🍃",
    layout="wide",
)

# Custom CSS for modern styling, colors, and layouts
st.markdown("""
    <style>
    /* Global App Settings */
    [data-testid="stAppViewContainer"] > .main {
        background-color: #f8fafc;
    }
    
    /* Premium thick cards */
    [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"] > div > div > div > div {
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.08);
        background-color: white;
        padding: 20px !important;
        border: 1px solid #e2e8f0;
        margin-bottom: 12px;
    }

    /* Titles and Typography styling */
    h1 { font-size: 2.2rem !important; color: #166534; font-weight: 700; text-align: center; margin-bottom: 0px; }
    h2 { font-size: 1.4rem !important; color: #1e293b; font-weight: 600; margin-top: 1rem !important; margin-bottom: 0.5rem !important;}
    h3 { font-size: 1.3rem !important; font-weight: 700; margin: 0px !important; }
    
    .field-label { font-size: 0.75rem; color: #64748b; font-weight: 600; margin-bottom: 2px; }
    </style>
""", unsafe_allow_html=True)

# --- SYSTEM MEMORY ---
if "nagbari_inventory_v3" not in st.session_state:
    st.session_state.nagbari_inventory_v3 = {
        "Assam CTC Tea": {"stock": 1250, "price": 240, "color": "#bef264"},
        "Darjeeling": {"stock": 250, "price": 650, "color": "#86efac"},
        "Nilgiri Green": {"stock": 800, "price": 380, "color": "#6ee7b7"},
        "Orthodox Leaf": {"stock": 150, "price": 420, "color": "#a7f3d0"}
    }

# --- MAIN APP UI ---
st.markdown("<h1>🍃 NAGBARI TRADERS</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #64748b; font-size: 1rem; margin-bottom: 1.5rem;'>Wholesale Stock Management Dashboard</p>", unsafe_allow_html=True)

# --- TOP BUSINESS OVERVIEW METRICS ---
st.header("📊 Overview")
with st.container():
    col1, col2, col3 = st.columns(3)
    
    total_items = len(st.session_state.nagbari_inventory_v3)
    total_stock_kg = sum(item["stock"] for item in st.session_state.nagbari_inventory_v3.values())
    total_value_inr = sum(item["stock"] * item["price"] for item in st.session_state.nagbari_inventory_v3.values())

    with col1:
        st.metric(label="Varieties", value=f"{total_items}")
    with col2:
        st.metric(label="Total Stock", value=f"{total_stock_kg:,} KG")
    with col3:
        st.metric(label="Total Value", value=f"₹{total_value_inr:,}")

# --- ADD NEW ITEM SECTION ---
st.write("---")
with st.expander("➕ Add New Tea Variety to Inventory", expanded=False):
    add_col1, add_col2, add_col3 = st.columns([2, 1, 1])
    
    with add_col1:
        new_item_name = st.text_input("Tea Variety Name", placeholder="e.g., Earl Grey Premium")
    with add_col2:
        new_item_stock = st.number_input("Opening Stock (KG)", min_value=0, value=0, step=50)
    with add_col3:
        new_item_price = st.number_input("Wholesale Rate (₹/KG)", min_value=0, value=0, step=10)
        
    if st.button("Add to Dashboard ✨", use_container_width=True):
        if new_item_name.strip() == "":
            st.error("Please enter a valid name for the tea variety.")
        elif new_item_name in st.session_state.nagbari_inventory_v3:
            st.error("This tea variety already exists!")
        else:
            # Assign a random clean color hex code for the new card top-line decoration
            st.session_state.nagbari_inventory_v3[new_item_name] = {
                "stock": new_item_stock,
                "price": new_item_price,
                "color": "#cbd5e1" # Clean neutral gray for added items
            }
            st.success(f"Added {new_item_name} successfully!")
            st.rerun()

# --- 2-COLUMN PREMIUM GRID ---
st.header("📦 Stock Details")

# Strict side-by-side layout (2 items per row)
grid_col1, grid_col2 = st.columns(2)

item_index = 0
# Creating a list of keys so deleting inside the loop doesn't throw python errors
for item_name in list(st.session_state.nagbari_inventory_v3.keys()):
    data = st.session_state.nagbari_inventory_v3[item_name]
    current_grid_col = grid_col1 if item_index % 2 == 0 else grid_col2
    item_index += 1
    
    # Check if stock is low (less than 300 KG)
    is_low_stock = data["stock"] < 300
    card_accent_color = "#ef4444" if is_low_stock else data.get("color", "#bef264")
    title_text_color = "#dc2626" if is_low_stock else "#111827"
    status_badge = "<span style='color: #dc2626; font-weight: 700; font-size: 0.85rem;'>⚠️ LOW STOCK ALERT</span>" if is_low_stock else "<span style='color: #64748b;'>Nagbari Premium Quality</span>"
    
    with current_grid_col:
        with st.container(border=True):
            # Header Row inside Card to hold color bar and Delete Button side by side
            card_head_col1, card_head_col2 = st.columns([4, 1])
            with card_head_col1:
                st.markdown(f"<div style='height: 5px; width: 60px; background-color: {card_accent_color}; border-radius: 2px; margin-bottom: 8px;'></div>", unsafe_allow_html=True)
            with card_head_col2:
                # Discontinue / Delete feature button
                if st.button("🗑️", key=f"del_{item_name}", help=f"Discontinue {item_name}", use_container_width=True):
                    del st.session_state.nagbari_inventory_v3[item_name]
                    st.rerun()
            
            # Details Layout
            st.markdown(f"<h3 style='color: {title_text_color};'>{item_name}</h3>", unsafe_allow_html=True)
            st.markdown(f"<p style='margin-top: 2px; margin-bottom: 12px;'>{status_badge}</p>", unsafe_allow_html=True)
            
            # Current Statistics
            metric_col1, metric_col2 = st.columns(2)
            with metric_col1:
                st.metric(label="Available Stock", value=f"{data['stock']} KG")
            with metric_col2:
                st.metric(label="Wholesale Rate", value=f"₹{data['price']} / KG")
            
            st.write("---")
            
            # Dual Inline Editor (Stock and Price side-by-side)
            st.markdown("<p style='color: #1e293b; font-weight: 600; font-size: 0.9rem; margin-bottom: 8px;'>⚙️ Quick Update Fields</p>", unsafe_allow_html=True)
            edit_stock_col, edit_price_col, save_btn_col = st.columns([1.2, 1.2, 1])
            
            with edit_stock_col:
                st.markdown("<div class='field-label'>New Stock (KG)</div>", unsafe_allow_html=True)
                new_qty = st.number_input(
                    "Stock", min_value=0, value=data["stock"], step=50, key=f"stock_in_{item_name}", label_visibility="collapsed"
                )
            
            with edit_price_col:
                st.markdown("<div class='field-label'>New Rate (₹)</div>", unsafe_allow_html=True)
                new_price = st.number_input(
                    "Price", min_value=0, value=data["price"], step=5, key=f"price_in_{item_name}", label_visibility="collapsed"
                )
                
            with save_btn_col:
                st.write("<div style='height: 20px;'></div>", unsafe_allow_html=True)
                if st.button("Save ✅", key=f"save_all_{item_name}", use_container_width=True):
                    st.session_state.nagbari_inventory_v3[item_name]["stock"] = new_qty
                    st.session_state.nagbari_inventory_v3[item_name]["price"] = new_price
                    st.rerun()