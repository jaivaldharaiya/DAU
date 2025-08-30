import streamlit as st
import requests
import sqlite3
import pandas as pd
from PIL import Image
import io

# --- Configuration ---
# This should match the address where your Flask app is running.
FLASK_API_URL = "http://127.0.0.1:5001/upload_image"
DATABASE_NAME = 'mydatabase.db'

# --- Helper Function to Get Image Data from DB ---
def get_all_images():
    """
    Connects to the SQLite database and fetches all image records,
    returning them as a pandas DataFrame.
    """
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        # Query the database to select all columns from the 'images' table
        df = pd.read_sql_query("SELECT * FROM images", conn)
        return df
    except Exception as e:
        st.error(f"Could not connect to the database. Is 'main.py' running? Error: {e}")
        return pd.DataFrame() # Return an empty DataFrame on error
    finally:
        if 'conn' in locals():
            conn.close()

# --- Streamlit App Layout ---

st.set_page_config(layout="wide")
st.title("Environmental Concern Detector 🔎")
st.write("Upload an image to test the Gemini Vision analysis backend.")

# Use columns for a cleaner layout
col1, col2 = st.columns(2)

# --- Column 1: Image Upload and Analysis ---
with col1:
    st.header("1. Upload and Analyze Image")

    with st.form("upload_form", clear_on_submit=True):
        # Input fields for the form
        uploaded_file = st.file_uploader("Choose an image...", type=["jpg", "jpeg", "png"])
        user_id_input = st.text_input("Enter User ID (e.g., 1, 2, 3)", "1")
        location_input = st.text_input("Enter Geo Location", "Ahmedabad, Gujarat")
        
        # Submit button
        submit_button = st.form_submit_button("Analyze Image")

    if submit_button and uploaded_file is not None:
        st.info("Sending image to the backend for analysis... please wait.")
        
        # Prepare the data to be sent to the Flask API
        # The API expects a multipart/form-data request
        files = {'image': (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
        payload = {'user_id': user_id_input, 'geo_location': location_input}

        try:
            # Make the POST request
            response = requests.post(FLASK_API_URL, files=files, data=payload)
            
            # Display the uploaded image
            image = Image.open(uploaded_file)
            st.image(image, caption="Image Sent to Backend", use_column_width=True)
            
            # Check the response from the server
            if response.status_code == 201:
                result = response.json()
                st.success(f"✅ Analysis Complete! Server says: '{result.get('message')}'")
                
                # Display the results in a formatted way
                st.subheader("Analysis Result:")
                st.markdown(f"**Description:** `{result.get('description')}`")
                
                if result.get('is_high_priority'):
                    st.error("🚨 **Status: High Priority**")
                else:
                    st.success("✅ **Status: Normal Priority**")

            else:
                st.error(f"❌ Error from server (Code: {response.status_code}): {response.text}")

        except requests.exceptions.ConnectionError:
            st.error("❌ Connection Error: Could not connect to the Flask server. Is `main.py` running?")
        except Exception as e:
            st.error(f"An unexpected error occurred: {e}")

    elif submit_button:
        st.warning("Please upload an image file.")

# --- Column 2: Database Viewer ---
with col2:
    st.header("2. Records in the Database")
    st.write("This table reads directly from the `images` table in `mydatabase.db`.")

    # Fetch and display the image data
    images_dataframe = get_all_images()
    if not images_dataframe.empty:
        st.dataframe(images_dataframe, use_container_width=True)
    else:
        st.info("The 'images' table is currently empty.")

    if st.button("Refresh Database View"):
        st.rerun()


### How to Run This

# Just like before, you'll need **two separate terminals**.

# **Step 1: Start Your Flask Backend**
# In your **first terminal**, make sure your `GOOGLE_API_KEY` is set and run your `main.py` file. (Note: On Windows, you might use `set` instead of `export`).
# ```bash
# # For Mac/Linux
# export GOOGLE_API_KEY="your_api_key_here" 

# # For Windows
# set GOOGLE_API_KEY="your_api_key_here"

# python main.py
# ```
# Leave this terminal running. It's your server.

# **Step 2: Start the Streamlit App**
# In your **second terminal**, run the Streamlit app.
# ```bash
# streamlit run test_vision_app.py