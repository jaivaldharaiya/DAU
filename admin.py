import streamlit as st
import requests
import pandas as pd
import base64
from io import BytesIO
from PIL import Image

# --- Configuration ---
FLASK_BASE_URL = "https://dau-o5gq.onrender.com"
CLASSIFICATION_INFO = {
    "DEF": {"name": "Deforestation", "icon": "🌳"},
    "POL": {"name": "Pollution", "icon": "🗑️"},
    "ENC": {"name": "Encroachment", "icon": "🏗️"},
    "ECO": {"name": "Ecological Stress", "icon": "🔬"},
    "OTH": {"name": "Other", "icon": "🔥"},
    "Not_relevant": {"name": "Not Relevant", "icon": "🤷"},
}

# --- API Functions (Frontend) ---
def get_cases(status):
    """Fetches cases from the backend API with robust error handling."""
    try:
        response = requests.get(f"{FLASK_BASE_URL}/cases/{status}")
        if response.status_code == 200:
            try:
                return pd.DataFrame(response.json())
            except requests.exceptions.JSONDecodeError:
                st.error("Error: Received an invalid JSON response from the server.")
        else:
            st.error(f"Failed to fetch cases. Server returned status code {response.status_code}.")
            st.text(f"Server response: {response.text}") # Display raw server error for debugging
    except requests.exceptions.ConnectionError:
        st.error("Connection Error: Could not connect to the backend server.")
    return pd.DataFrame()

def handle_api_response(response, success_message):
    """Helper function to handle API responses for approve/reject actions."""
    if response.status_code == 200:
        st.toast(success_message, icon="✅")
    else:
        try:
            st.error(f"Failed to perform action: {response.json().get('message')}")
        except requests.exceptions.JSONDecodeError:
            st.error(f"Failed to perform action. Server returned status {response.status_code}.")
            st.text(f"Server response: {response.text}")

def approve_case(image_id):
    """Sends a request to the backend to approve a case."""
    try:
        response = requests.post(f"{FLASK_BASE_URL}/approve_case/{image_id}")
        handle_api_response(response, f"Case #{image_id} approved!")
    except requests.exceptions.ConnectionError:
        st.error("Connection Error: Could not connect to the backend server.")

def reject_case(image_id):
    """Sends a request to the backend to reject (delete) a case."""
    try:
        response = requests.delete(f"{FLASK_BASE_URL}/reject_case/{image_id}")
        handle_api_response(response, f"Case #{image_id} rejected.")
    except requests.exceptions.ConnectionError:
        st.error("Connection Error: Could not connect to the backend server.")

# --- Helper to decode base64 images ---
def display_case_image(case, caption):
    if 'image_data' in case and case['image_data']:
        try:
            image_bytes = base64.b64decode(case['image_data'])
            image = Image.open(BytesIO(image_bytes))
            st.image(image, caption=caption, use_column_width=True)
        except Exception as e:
            st.error(f"Error displaying image: {e}")
    else:
        st.image("https://placehold.co/600x400/grey/white?text=No+Image", caption=caption)

# --- Main Application UI ---
st.set_page_config(page_title="Mangrove Watch Portal", layout="wide", page_icon="🛡️")

def login_page():
    st.title("🛡️ Authority Login Portal")
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.form_submit_button("Login"):
            if username == "admin" and password == "password":
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("Invalid username or password.")

def main_dashboard():
    st.sidebar.title("Welcome, Admin!")
    if st.sidebar.button("Logout", type="primary"):
        st.session_state.logged_in = False
        st.rerun()

    st.title("Mangrove Environmental Monitoring Dashboard")
    pending_tab, approved_tab = st.tabs(["🚨 Pending Review", "✅ Approved Cases"])

    # --- Helper function for filtering and displaying cases ---
    def display_filtered_cases(tab_title, cases_df, show_actions=False):
        st.subheader(tab_title)

        if cases_df.empty:
            st.success("All clear! No cases to display.")
            return

        # --- NEW: Filter Controls ---
        filter_col1, filter_col2 = st.columns([1, 2])
        
        # Create a list of classification options for the filter
        class_options = ["All"] + [f"{info['icon']} {info['name']}" for info in CLASSIFICATION_INFO.values()]
        
        with filter_col1:
            selected_class_name = st.selectbox("Filter by Type", options=class_options, key=f"filter_{tab_title}")
        
        with filter_col2:
            search_query = st.text_input("Search by AI Reasoning", placeholder="e.g., oil spill, tree cutting...", key=f"search_{tab_title}").lower()

        # --- Filter Logic ---
        filtered_cases = cases_df.copy()

        # 1. Filter by selected classification
        if selected_class_name != "All":
            # Find the code (e.g., 'DEF') corresponding to the selected name ('🌳 Deforestation')
            selected_code = next((code for code, info in CLASSIFICATION_INFO.items() if f"{info['icon']} {info['name']}" == selected_class_name), None)
            if selected_code:
                filtered_cases = filtered_cases[filtered_cases['llm_classification'] == selected_code]

        # 2. Filter by search query in the description
        if search_query:
            # Ensure the 'description' column exists and is of string type before searching
            if 'description' in filtered_cases.columns:
                 filtered_cases = filtered_cases[filtered_cases['description'].str.lower().str.contains(search_query, na=False)]

        # --- Display Cases ---
        if filtered_cases.empty:
            st.warning("No cases match the current filter criteria.")
        else:
            for _, case in filtered_cases.iterrows():
                with st.container(border=True):
                    col1, col2 = st.columns([1, 2])
                    with col1:
                        display_case_image(case, caption=f"Case ID: {case['image_id']}")
                    with col2:
                        info = CLASSIFICATION_INFO.get(case['llm_classification'], {})
                        st.subheader(f"{info.get('icon', '❓')} {info.get('name', 'Unknown')} Report")
                        st.markdown(f"**Location:** `{case['geo_location']}`")
                        st.markdown(f"**Classification Code:** `{case['llm_classification']}`")
                        
                        # --- NEW: Displaying AI Description ---
                        if 'description' in case and pd.notna(case['description']):
                            st.info(f"**AI Reasoning:** {case['description']}")

                        # Show approve/reject buttons only in the pending tab
                        if show_actions:
                            b_col1, b_col2 = st.columns(2)
                            b_col1.button("Approve", key=f"approve_{case['image_id']}", 
                                          on_click=approve_case, args=(case['image_id'],), type="primary", use_container_width=True)
                            b_col2.button("Reject", key=f"reject_{case['image_id']}", 
                                          on_click=reject_case, args=(case['image_id'],), use_container_width=True)
    
    # --- Tab Implementations ---
    with pending_tab:
        pending_cases = get_cases(status=0)
        display_filtered_cases("New Reports Awaiting Approval", pending_cases, show_actions=True)

    with approved_tab:
        approved_cases = get_cases(status=1)
        display_filtered_cases("Approved Reports", approved_cases, show_actions=False)
        
# --- Authentication Check ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if st.session_state.logged_in:
    main_dashboard()
else:
    login_page()