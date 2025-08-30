import sqlite3
from flask import Flask, request, jsonify
import os
import base64
import requests # No new libraries needed

# --- Configuration ---
DATABASE_NAME = 'mydatabase.db'
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
# This is the correct, working endpoint for the Gemini 2.5 Flash model.
MODEL_ENDPOINT = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-05-20:generateContent?key={GOOGLE_API_KEY}"

# The keywords we want to detect in the image description
HIGH_PRIORITY_KEYWORDS = ["cut tree", "stump", "trash", "garbage", "construction", "excavator", "smoke", "deforestation", "waste", "pollution"]

# --- Flask App Initialization ---
app = Flask(__name__)

# --- Database Setup ---
def initialize_database():
    """
    This function connects to the database and creates the 'users' and 'images'
    tables if they haven't been created yet. It's designed to be run
    once when the server starts.
    """
    connection = sqlite3.connect(DATABASE_NAME)
    cursor = connection.cursor()
    print("Database connected. Ensuring tables exist...")

    # SQL command to create the 'users' table
    # We've added a 'password' column that cannot be empty (NOT NULL).
    create_user_table_query = """
    CREATE TABLE IF NOT EXISTS users (
        userid INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone_number TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL,
        occupation TEXT,
        aadhar_verified INTEGER DEFAULT 0,
        credit_score INTEGER
    );
    """

    # SQL command to create the 'images' table (unchanged)
    create_image_table_query = """
    CREATE TABLE IF NOT EXISTS images (
        image_id INTEGER PRIMARY KEY AUTOINCREMENT,
        geo_location TEXT,
        image_url TEXT NOT NULL,
        llm_classification TEXT,
        is_useful INTEGER DEFAULT 0,
        captured_by_userid INTEGER,
        FOREIGN KEY (captured_by_userid) REFERENCES users (userid)
    );
    """

    # Run the SQL commands
    cursor.execute(create_user_table_query)
    cursor.execute(create_image_table_query)

    print("Tables are ready.")

    connection.commit()
    connection.close()

# --- API Routes ---

@app.route('/')
def home():
    return "Hello! The user database server is running."

@app.route('/adduser', methods=['POST'])
def add_new_user():

    data = request.get_json()

    # Get the name, phone number, and new password field from the JSON data.
    user_name = data.get('name')
    phone_number = data.get('phone')
    password = data.get('password')

    # If any of the required fields are missing, send back an error message.
    if not all([user_name, phone_number, password]):
        return jsonify({'message': 'Error: Please provide name, phone number, and password.'}), 400

    try:
        connection = sqlite3.connect(DATABASE_NAME)
        cursor = connection.cursor()

        # The SQL query is updated to include the 'password' column.
        insert_query = "INSERT INTO users (name, phone_number, password) VALUES (?, ?, ?)"

        # Execute the query, passing the user's data including the password.
        cursor.execute(insert_query, (user_name, phone_number, password))

        connection.commit()

        return jsonify({'message': f"Success: User '{user_name}' was added to the database."}), 201

    except sqlite3.IntegrityError:
        return jsonify({'message': f"Error: A user with phone number '{phone_number}' already exists."}), 409
    except Exception as e:
        return jsonify({'message': 'An error occurred on the server.', 'error': str(e)}), 500
    finally:
        if 'connection' in locals() and connection:
            connection.close()

# --- Main Execution Block ---
# --- ✨ NEW: Image Analysis Endpoint (Now using Gemini) ✨ ---

def analyze_image_with_gemini(image_base64):
    """
    Sends the image to the Google Gemini Vision API and returns the description.
    """
    if not GOOGLE_API_KEY:
        return "Error: GOOGLE_API_KEY environment variable not set."

    headers = {"Content-Type": "application/json"}

    prompt_text = (
        "Analyze this image for environmental concerns. "
        "Describe what you see in one short sentence. "
        "Focus on any signs of tree cutting, trash, construction, or smoke."
    )

    # This is the specific JSON payload structure required by the Gemini API for multimodal input.
    payload = {
        "contents": [{
            "parts": [
                {"text": prompt_text},
                {
                    "inline_data": {
                        "mime_type": "image/jpeg",
                        "data": image_base64
                    }
                }
            ]
        }]
    }

    try:
        response = requests.post(MODEL_ENDPOINT, headers=headers, json=payload)
        response.raise_for_status() # Raise an error for bad status codes
        
        # Parse the response to get the generated text.
        # This navigates the Gemini API's JSON response structure.
        result = response.json()
        description = result['candidates'][0]['content']['parts'][0]['text']
        return description
    except requests.exceptions.RequestException as e:
        print(f"API request failed: {e}")
        # Return the error message from the API if available
        error_response = response.json() if response else {}
        error_message = error_response.get("error", {}).get("message", str(e))
        return f"Error: Failed to communicate with the vision API. Details: {error_message}"


@app.route('/upload_image', methods=['POST'])
def upload_image():
    """
    Receives an image, user_id, and geo_location from Flutter.
    Analyzes the image with Gemini and saves the results.
    """
    # 1. Check for required data (this part is unchanged)
    if 'image' not in request.files:
        return jsonify({"message": "Error: No image file provided."}), 400
    user_id = request.form.get('user_id')
    geo_location = request.form.get('geo_location')
    if not user_id or not geo_location:
        return jsonify({"message": "Error: user_id and geo_location are required."}), 400

    image_file = request.files['image']

    # 2. Process image (this part is unchanged)
    image_bytes = image_file.read()
    image_base64 = base64.b64encode(image_bytes).decode('utf-8')

    # 3. Call the Vision LLM (now Gemini)
    description = analyze_image_with_gemini(image_base64)

    # 4. Analyze the response (this part is unchanged)
    is_high_priority = any(keyword in description.lower() for keyword in HIGH_PRIORITY_KEYWORDS)

    # 5. Save to database (this part is unchanged)
    image_url_placeholder = f"user_{user_id}_image_{image_file.filename}"
    try:
        connection = sqlite3.connect(DATABASE_NAME)
        cursor = connection.cursor()
        insert_query = """
        INSERT INTO images (geo_location, image_url, llm_classification, is_useful, captured_by_userid)
        VALUES (?, ?, ?, ?, ?)
        """
        cursor.execute(insert_query, (geo_location, image_url_placeholder, description, int(is_high_priority), user_id))
        connection.commit()
    except Exception as e:
        return jsonify({"message": "Database error.", "error": str(e)}), 500
    finally:
        if 'connection' in locals():
            connection.close()

    # 6. Send response back to Flutter
    return jsonify({
        "message": "Image uploaded and analyzed successfully!",
        "description": description,
        "is_high_priority": is_high_priority
    }), 201


# --- Main Execution Block ---
if __name__ == '__main__':
    initialize_database()
    # For Render, the port is often set automatically, but 5000 is a good default for local testing.
    # debug=False is better for production, but True is fine for the hackathon.
    app.run(host='0.0.0.0', port=5001, debug=True)


# ### Your Action Plan for the Hackathon:

# 1.  **Get a Google API Key (2 minutes):**
#     * Go to **[Google AI Studio](https://aistudio.google.com/app/apikey)**.
#     * Click "**Create API key**".
#     * Copy the key immediately and save it somewhere safe.

# 2.  **Update `requirements.txt` (30 seconds):**
#     Make sure your `requirements.txt` file for Render has these lines:
#     ```text
#     Flask
#     requests
#     gunicorn
    



