import sqlite3
from flask import Flask, request, jsonify
import os
import base64
import requests
import json

# --- Configuration ---
DATABASE_NAME = 'mydatabase.db'
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")


# Gemini API endpoint
MODEL_ENDPOINT = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-05-20:generateContent?key={GOOGLE_API_KEY}"

# --- Flask App Initialization ---
app = Flask(__name__)

# --- Database Setup ---
def initialize_database():
    connection = sqlite3.connect(DATABASE_NAME)
    cursor = connection.cursor()
    print("Database connected. Ensuring tables exist...")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        userid INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone_number TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL,
        occupation TEXT,
        aadhar_verified INTEGER DEFAULT 0,
        credit_score INTEGER
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS images (
        image_id INTEGER PRIMARY KEY AUTOINCREMENT,
        geo_location TEXT,
        image_data BLOB,
        llm_classification TEXT,
        description TEXT,
        is_useful INTEGER DEFAULT 0,
        captured_by_userid INTEGER,
        FOREIGN KEY (captured_by_userid) REFERENCES users (userid)
    );
    """)

    print("Tables are ready.")
    connection.commit()
    connection.close()

import re
import json
ALLOWED_CLASSES = {"DEF", "POL", "ENC", "ECO", "OTH", "Not_relevant"}

def _normalize_class(label: str) -> str:
    """Map free-form labels to one of the allowed codes."""
    if not label:
        return "Not_relevant"
    v = label.strip().upper().replace("-", "_")
    # direct codes
    if v in {"DEF", "POL", "ENC", "ECO", "OTH"}:
        return v
    if v in {"NOT_RELEVANT", "NOT_RELEVANT_", "NOT_RELEVANT__"}:
        return "Not_relevant"
    # common words → codes
    if "DEFOR" in v or "BURN" in v or "LOG" in v:
        return "DEF"
    if "POLLUT" in v or "WASTE" in v or "SEWAGE" in v or "OIL" in v:
        return "POL"
    if "ENCROACH" in v or "CONSTRUCT" in v or "LANDFILL" in v or "AQUACULTURE" in v:
        return "ENC"
    if "ECO" in v or "STRESS" in v or "PEST" in v or "ALGA" in v or "DIE" in v:
        return "ECO"
    if "OTHER" in v or "UNSPECIFIED" in v or "POACH" in v or "FIRE" in v:
        return "OTH"
    return "Not_relevant"

def _parse_gemini_json_text(text: str) -> dict:
    """Be tolerant to code fences / extra prose and pull out a JSON object."""
    s = (text or "").strip()

    # strip code fences like ```json ... ``` or ``` ...
    if s.startswith("```"):
        s = re.sub(r"^```(?:json)?\s*", "", s, flags=re.IGNORECASE)
        s = re.sub(r"\s*```$", "", s)

    # 1) try whole string
    try:
        return json.loads(s)
    except Exception:
        pass

    # 2) try the largest {...} block
    m = re.search(r"\{.*\}", s, flags=re.DOTALL)
    if m:
        candidate = m.group(0)
        try:
            return json.loads(candidate)
        except Exception:
            pass

    # 3) last-ditch: regex for the two fields
    result = {}
    m_cls = re.search(r'"?classification"?\s*:\s*"([^"]+)"', s, flags=re.IGNORECASE)
    if m_cls:
        result["classification"] = m_cls.group(1)
    m_reason = re.search(r'"?reasoning"?\s*:\s*"(.*?)"', s, flags=re.IGNORECASE | re.DOTALL)
    if m_reason:
        # squash excessive whitespace/newlines
        result["reasoning"] = re.sub(r"\s+", " ", m_reason.group(1)).strip()
    return result
# --- Gemini API helper ---
def analyze_image_with_gemini(image_base64):
    """
    Sends the image to the Google Gemini Vision API and returns a dict:
      { "classification": <DEF|POL|ENC|ECO|OTH|Not_relevant>, "reasoning": <str> }
    """
    if not GOOGLE_API_KEY:
        return {"error": "GOOGLE_API_KEY environment variable not set."}

    headers = {"Content-Type": "application/json"}

    prompt_text = (
        "You are an environmental monitoring assistant. "
        "Analyze this image and classify it into exactly one of the following categories:\n\n"
        "- DEF (Deforestation): Cutting, clearing, or burning of mangrove trees.\n"
        "- POL (Pollution): Dumping or release of harmful substances (solid waste, oil spill, sewage, etc.).\n"
        "- ENC (Encroachment): Illegal construction, land reclamation, aquaculture pond conversion.\n"
        "- ECO (Ecological Stress): Natural or human-induced threats (pest infestation, algal blooms, mass die-off).\n"
        "- OTH (Other): Poaching, illegal fishing, fire, or unspecified disturbance.\n"
        "- Not_relevant: If the image does not relate to mangrove environmental concerns.\n\n"
        "Return only a JSON object with exactly these two fields:\n"
        '{\"classification\": \"DEF|POL|ENC|ECO|OTH|Not_relevant\", \"reasoning\": \"<short explanation>\"}\n'
        "Do not include any extra text or markdown."
    )

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
        resp = requests.post(MODEL_ENDPOINT, headers=headers, json=payload)
        resp.raise_for_status()
        body = resp.json()

        # get model text
        model_text = body["candidates"][0]["content"]["parts"][0]["text"]

        # robust parse
        parsed = _parse_gemini_json_text(model_text)

        # normalize + validate
        classification_raw = parsed.get("classification", "")
        classification = _normalize_class(classification_raw)
        reasoning = parsed.get("reasoning", "").strip() or "No reasoning provided."

        return {"classification": classification, "reasoning": reasoning}

    except requests.exceptions.RequestException as e:
        error_response = resp.json() if 'resp' in locals() and resp is not None else {}
        error_message = error_response.get("error", {}).get("message", str(e))
        return {"error": f"Failed to communicate with the vision API. Details: {error_message}"}
    except Exception as e:
        return {"error": f"Unexpected parsing error: {str(e)}"}
    
# --- API Routes ---
@app.route('/')
def home():
    return "Hello! The user database server is running."

@app.route('/adduser', methods=['POST'])
def add_new_user():
    data = request.get_json()
    user_name = data.get('name')
    phone_number = data.get('phone')
    password = data.get('password')

    if not all([user_name, phone_number, password]):
        return jsonify({'message': 'Error: Please provide name, phone number, and password.'}), 400

    try:
        connection = sqlite3.connect(DATABASE_NAME)
        cursor = connection.cursor()
        cursor.execute("INSERT INTO users (name, phone_number, password) VALUES (?, ?, ?)",
                       (user_name, phone_number, password))
        connection.commit()
        return jsonify({'message': f"Success: User '{user_name}' was added to the database."}), 201
    except sqlite3.IntegrityError:
        return jsonify({'message': f"Error: A user with phone number '{phone_number}' already exists."}), 409
    except Exception as e:
        return jsonify({'message': 'An error occurred on the server.', 'error': str(e)}), 500
    finally:
        if 'connection' in locals():
            connection.close()

@app.route('/login', methods=['POST'])
def login_user():
    data = request.get_json()
    phone_number = data.get('phone')
    password = data.get('password')

    if not phone_number or not password:
        return jsonify({'message': 'Error: Please provide both phone number and password.'}), 400

    try:
        connection = sqlite3.connect(DATABASE_NAME)
        cursor = connection.cursor()
        cursor.execute("SELECT userid, password FROM users WHERE phone_number = ?", (phone_number,))
        user_record = cursor.fetchone()
        if user_record is None:
            return jsonify({'message': 'Login failed: User not found.'}), 401
        stored_password = user_record[1]
        if password == stored_password:
            return jsonify({'message': 'Login successful!', 'userid': user_record[0]}), 200
        else:
            return jsonify({'message': 'Login failed: Incorrect password.'}), 401
    except Exception as e:
        return jsonify({'message': 'An error occurred on the server.', 'error': str(e)}), 500
    finally:
        if 'connection' in locals():
            connection.close()

@app.route('/upload_image', methods=['POST'])
def upload_image():
    if 'image' not in request.files:
        return jsonify({"message": "Error: No image file provided."}), 400

    user_id = request.form.get('user_id')
    geo_location = request.form.get('geo_location')
    if not user_id or not geo_location:
        return jsonify({"message": "Error: user_id and geo_location are required."}), 400

    image_file = request.files['image']
    image_bytes = image_file.read()
    image_base64 = base64.b64encode(image_bytes).decode('utf-8')

    # --- For Debugging: See what the API is returning ---
    # print("Sending image to Gemini for analysis...")
    analysis_result = analyze_image_with_gemini(image_base64)
    
    # --- Recommended: Print the raw and parsed results to your console ---
    # --- This helps verify if the LLM response is what you expect.   ---
    # print(f"GEMINI RAW RESPONSE: {analysis_result}")
    
    if "error" in analysis_result:
        return jsonify(analysis_result), 500

    classification = analysis_result.get('classification')
    reasoning = analysis_result.get('reasoning', 'No reasoning provided.')

    # --- KEY LOGIC CHANGE ---
    # If the image is classified as 'Not_relevant' by the LLM, we can ignore it
    # or handle it separately. For this example, we'll just stop processing.
    if classification == 'Not_relevant':
        return jsonify({
            "message": "Image analyzed as not relevant and was not stored.",
            "classification": classification,
            "reasoning": reasoning
        }), 200 # 200 OK is appropriate here, it's not a server error.

    # All other valid classifications (DEF, POL, etc.) are considered "pending cases".
    # Therefore, we will store them with is_useful = 0.
    # An admin will later approve them via the /approve_case/<id> endpoint, changing it to 1.
    is_useful_status = 0 

    try:
        connection = sqlite3.connect(DATABASE_NAME)
        cursor = connection.cursor()
        cursor.execute("""
            INSERT INTO images (geo_location, image_data, llm_classification, description, is_useful, captured_by_userid)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            geo_location,
            sqlite3.Binary(image_bytes),
            classification,  # This correctly maps to the 'llm_classification' column
            reasoning,       # This correctly maps to the 'description' column
            is_useful_status,# This is now correctly set to 0 for pending review
            user_id
        ))
        connection.commit()
        image_id = cursor.lastrowid # Get the ID of the newly inserted image
    except Exception as e:
        return jsonify({"message": "Database error.", "error": str(e)}), 500
    finally:
        if 'connection' in locals():
            connection.close()

    return jsonify({
        "message": "Image classified and stored successfully as a pending case!",
        "image_id": image_id,
        "classification": classification,
        "reasoning": reasoning
    }), 201

@app.route('/cases/<int:status>', methods=['GET'])
def get_cases_api(status):
    """API to get cases. status=0 for pending, status=1 for approved."""
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM images WHERE is_useful = ?", (status,))
        rows = cursor.fetchall()

        cases = []
        for row in rows:
            case = dict(row)
            if "image_data" in case and case["image_data"]:
                try:
                    case["image_data"] = base64.b64encode(case["image_data"]).decode("utf-8")
                except Exception:
                    case["image_data"] = None
            cases.append(case)

        return jsonify(cases), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()

@app.route('/approve_case/<int:image_id>', methods=['POST'])
def approve_case_api(image_id):
    conn = None # Define connection variable to ensure it's accessible in finally block
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()

        # --- NEW LOGIC: Find the user who submitted the case ---
        # We need to get the user's ID before we can award a credit.
        cursor.execute("SELECT captured_by_userid FROM images WHERE image_id = ?", (image_id,))
        result = cursor.fetchone()

        # If the image ID doesn't exist, we can't proceed.
        if result is None:
            return jsonify({'message': f'Error: Case with ID {image_id} not found.'}), 404
        
        user_id_to_credit = result[0]

        # --- Original Logic: Approve the case ---
        cursor.execute("UPDATE images SET is_useful = 1 WHERE image_id = ?", (image_id,))
        
        # --- NEW LOGIC: Award one credit point to the user ---
        # The COALESCE function safely handles cases where credit_score is NULL by treating it as 0.
        cursor.execute("""
            UPDATE users 
            SET credit_score = COALESCE(credit_score, 0) + 1 
            WHERE userid = ?
        """, (user_id_to_credit,))

        # Commit both the case approval and the credit score update in a single transaction
        conn.commit()
        
        return jsonify({'message': f'Success: Case #{image_id} approved and 1 credit awarded to user #{user_id_to_credit}.'}), 200

    except Exception as e:
        # It's good practice to have error handling for the database operations
        return jsonify({'message': 'An error occurred on the server.', 'error': str(e)}), 500

    finally:
        if conn:
            conn.close()

@app.route('/reject_case/<int:image_id>', methods=['DELETE'])
def reject_case_api(image_id):
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM images WHERE image_id = ?", (image_id,))
        conn.commit()
        if cursor.rowcount == 0:
            return jsonify({'message': f'Error: Case with ID {image_id} not found.'}), 404
        return jsonify({'message': f'Success: Case #{image_id} rejected and deleted.'}), 200
    finally:
        if 'conn' in locals():
            conn.close()

@app.route('/users', methods=['GET'])
def get_all_users():
    """API to fetch all users with their ID, name, and credit score."""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        conn.row_factory = sqlite3.Row # This allows accessing columns by name
        cursor = conn.cursor()
        
        # The COALESCE function ensures that if credit_score is NULL, it will be returned as 0.
        cursor.execute("SELECT userid, name, COALESCE(credit_score, 0) as credit_score FROM users ORDER BY credit_score DESC")
        
        rows = cursor.fetchall()

        # Convert the list of database row objects into a list of simple dictionaries
        users_list = [dict(row) for row in rows]

        return jsonify(users_list), 200

    except Exception as e:
        return jsonify({"error": "Failed to fetch users.", "details": str(e)}), 500
        
    finally:
        if conn:
            conn.close()

# --- Main Execution Block ---
if __name__ == '__main__':
    initialize_database()
    port = int(os.environ.get("PORT", 5001))
    app.run(host='0.0.0.0', port=port, debug=False)
