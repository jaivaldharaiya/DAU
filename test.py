import streamlit as st
import requests
import sqlite3
import pandas as pd
from PIL import Image
import json # Import json to handle the response

# --- Configuration ---
FLASK_API_URL = "http://127.0.0.1:5001/upload_image"
DATABASE_NAME = 'mydatabase.db'

# --- UI Helper Dictionary ---
# This dictionary helps display the results in a more user-friendly way.
CLASSIFICATION_INFO = {
    "DEF": {"name": "Deforestation", "color": "error"},
    "POL": {"name": "Pollution", "color": "error"},
    "ENC": {"name": "Encroachment", "color": "error"},
    "ECO": {"name": "Ecological Stress", "color": "warning"},
    "OTH": {"name": "Other", "color": "warning"},
    "Not_relevant": {"name": "Not Relevant", "color": "success"},
}


# --- Helper Function to Get Image Data from DB ---
def get_all_images():
    """Connects to the SQLite DB and fetches all image records."""
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        df = pd.read_sql_query("SELECT * FROM images", conn)
        return df
    except Exception as e:
        st.error(f"Could not connect to the database. Is 'main.py' running? Error: {e}")
        return pd.DataFrame()
    finally:
        if 'conn' in locals():
            conn.close()

# --- Streamlit App Layout ---

st.set_page_config(layout="wide")
st.title("Mangrove Environmental Classifier 🌳")
st.write("Upload an image to test the classification endpoint.")

# Create two columns for a clean layout
col1, col2 = st.columns(2)

# --- Column 1: Image Upload and Analysis Results ---
with col1:
    st.header("1. Upload Image for Classification")

    with st.form("upload_form", clear_on_submit=True):
        uploaded_file = st.file_uploader("Choose an image...", type=["jpg", "jpeg", "png"])
        user_id_input = st.text_input("Enter User ID", "1")
        location_input = st.text_input("Enter Geo Location", "Sundarbans, West Bengal")
        submit_button = st.form_submit_button("Classify Image")

    if submit_button and uploaded_file is not None:
        with st.spinner("Sending image to backend for analysis... please wait."):
            # Prepare data for the multipart/form-data request
            files = {'image': (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
            payload = {'user_id': user_id_input, 'geo_location': location_input}

            try:
                # Make the POST request to your Flask app
                response = requests.post(FLASK_API_URL, files=files, data=payload)
                
                # Display the uploaded image
                image = Image.open(uploaded_file)
                st.image(image, caption="Image Sent for Analysis", use_container_width=True)

                if response.status_code == 201:
                    result = response.json()
                    st.success("✅ Analysis Complete!")
                    
                    # --- Display the structured results ---
                    st.subheader("Classification Result:")
                    
                    classification_code = result.get('classification', 'Not_relevant')
                    reasoning_text = result.get('reasoning', 'No reasoning provided.')

                    # Get display info from our helper dictionary
                    info = CLASSIFICATION_INFO.get(classification_code, {"name": "Unknown", "color": "info"})
                    
                    # Display with colors using st.error, st.warning, or st.success
                    if info['color'] == 'error':
                        st.error(f"**Classification:** {classification_code} ({info['name']})")
                    elif info['color'] == 'warning':
                        st.warning(f"**Classification:** {classification_code} ({info['name']})")
                    else:
                        st.success(f"**Classification:** {classification_code} ({info['name']})")

                    st.markdown(f"**Reasoning:**")
                    st.info(reasoning_text)
                    
                else:
                    st.error(f"❌ Error from server (Code: {response.status_code}): {response.text}")

            except requests.exceptions.ConnectionError:
                st.error("❌ Connection Error: Could not connect to Flask. Is `main.py` running?")
            except Exception as e:
                st.error(f"An unexpected error occurred: {e}")

    elif submit_button:
        st.warning("Please upload an image file first.")

# --- Column 2: Live Database Viewer ---
with col2:
    st.header("2. Records in the `images` Table")
    st.write("This table reads directly from `mydatabase.db`.")
    
    if st.button("Refresh Database View"):
        st.rerun() # Reruns the script to fetch new data

    images_dataframe = get_all_images()
    if not images_dataframe.empty:
        # Display the dataframe, making it fill the column width
        st.dataframe(images_dataframe, use_container_width=True)
    else:
        st.info("The 'images' table is currently empty.")



# ### How to Run

# The process is the same, but you will run this new file.

# 1.  **Run your Flask Backend**: In your **first terminal**, make sure `main.py` (with the new classification logic) is running.
# 2.  **Run this Streamlit App**: In your **second terminal**, run the command:
#     ```bash
#     streamlit run test_classifier_app.py
    
