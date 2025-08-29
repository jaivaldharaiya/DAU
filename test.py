import sqlite3
from flask import Flask, request, jsonify

# --- Configuration ---
DATABASE_NAME = 'mydatabase.db'

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
    """A simple welcome message to confirm the server is running."""
    return "Hello! The user database server is running."

@app.route('/adduser', methods=['POST'])
def add_new_user():
    """
    Handles adding a new user to the database.
    It expects a JSON message like: {"name": "John Doe", "phone": "1234567890", "password": "securepassword123"}
    """
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
if __name__ == '__main__':
    initialize_database()
    app.run(host='0.0.0.0', port=5000, debug=True)

