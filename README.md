Mangrove Sentinel
Tagline: Empowering Coastal Guardians. Protecting Vital Ecosystems.

Team: CodeStrom

Team Leader: Jaival Sunil Dharaiya

🚀 Project Overview

Mangrove Sentinel is an AI-powered, community-driven mobile platform designed to protect vital mangrove ecosystems. It addresses the critical challenge of monitoring vast and remote coastal areas by empowering local citizens to become "Sentinels" of their environment.

Using our intuitive mobile app, users can report threats like illegal deforestation, pollution, and encroachment in real-time by uploading geotagged photos. These reports are intelligently analyzed by our AI backend, which verifies their authenticity and flags high-priority incidents for authorities, enabling swift and effective conservation action.

✨ Key Features
Real-time Reporting: Users can quickly capture and upload geotagged photos of environmental threats.

AI-Powered Validation: A Python backend uses the Gemini Vision API to analyze images, classify threats, and assign a priority level.

Gamified Conservation: Users earn "EcoCoins" for validated reports, encouraging active and continued participation.

Rewards Ecosystem: A dedicated in-app section where users can redeem their earned EcoCoins for dummy offers, creating a positive feedback loop.

Centralized Authority Dashboard (Future Scope): A web-based portal for authorities to view, verify, and act upon validated reports.

🛠️ Tech Stack
The project is built with a modern, scalable tech stack optimized for performance and rapid development.

Component

Technology

Mobile App

Flutter & Dart - For building a high-performance, cross-platform mobile application from a single codebase.

Backend Server

Python (Flask) - For its simplicity, robustness, and seamless integration with AI/ML libraries.

Database

SQLite - A lightweight, file-based database perfect for rapid prototyping and deployment.

AI Image Analysis

Google Gemini 2.5 Flash API - For state-of-the-art multimodal analysis of user-submitted images.

Deployment

Render - For hosting the live Flask backend API.

📲 How to Use the App
The easiest way to test the application is by installing the provided APK on an Android device.

Install the App:

Download the app-release.apk file from this repository.

Transfer it to your Android phone and follow the on-screen prompts to install it. You may need to "Allow installation from unknown sources."

Login / Register:

Open the Mangrove Sentinel app.

Enter your phone number and a password.

If your phone number is new, the app will automatically create an account for you. If you've used it before, it will log you in.

Submit a Report:

From the Dashboard tab, tap the "Tap to select Image" area.

Choose to take a photo with your camera or select one from your gallery.

The app will automatically fetch your GPS location.

Add an optional description and click "Submit Report."

View Rewards:

Navigate to the Leaderboard and Rewards tabs to see your EcoCoin balance and browse available offers.

🌐 Backend API
The backend is live and handles all user authentication, data storage, and AI analysis.

Live Server URL: https://dau-o5gq.onrender.com

You can test the server's status by visiting the link in your browser. You should see the message: Hello! The user database server is running.

👨‍💻 For Developers: Running Locally
Backend (Python)

Ensure you have Python and Pip installed.

Create a virtual environment: python -m venv venv

Activate it: source venv/bin/activate (macOS/Linux) or venv\Scripts\activate (Windows).

Install dependencies: pip install -r requirements.txt

Set your Google API Key: export GOOGLE_API_KEY="YOUR_API_KEY"

Run the server: python main.py

Frontend (Flutter)

Ensure you have the Flutter SDK installed.

Connect a device or start an emulator.

Navigate to the mangrove_sentinel_app directory.

Get dependencies: flutter pub get

Run the app: flutter run

