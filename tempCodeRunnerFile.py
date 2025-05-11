import matplotlib
matplotlib.use('Agg')

from flask import Flask, request, render_template_string, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
import matplotlib.pyplot as plt
import numpy as np
import io
import base64
import random
import re
from datetime import datetime
import sqlite3
from sqlalchemy import inspect
import secrets
import os
import logging
import bcrypt
import pytz

# Helper function to get current IST time
def get_ist_time():
    ist = pytz.timezone('Asia/Kolkata')
    return datetime.now(ist)

# Custom logging formatter for IST timestamps
class ISTFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        ist = pytz.timezone('Asia/Kolkata')
        dt = datetime.fromtimestamp(record.created, ist)
        if datefmt:
            return dt.strftime(datefmt)
        return dt.strftime('%Y-%m-%d %H:%M:%S %Z')

# Configure logging with IST timestamps
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
formatter = ISTFormatter('%(asctime)s - %(levelname)s - %(message)s')
for handler in logging.getLogger().handlers:
    handler.setFormatter(formatter)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_urlsafe(32))

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

EMAIL_REGEX = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    quota = db.Column(db.Integer, nullable=True)
    approved = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=get_ist_time)
    last_login = db.Column(db.DateTime, nullable=True)
    remember_token = db.Column(db.String(100), unique=True, nullable=True)

    def set_password(self, password):
        self.password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    def check_password(self, password):
        try:
            return bcrypt.checkpw(password.encode('utf-8'), self.password.encode('utf-8'))
        except Exception as e:
            logging.error(f"Password check failed for {self.email}: {e}")
            return False

    def __repr__(self):
        return f'<User {self.email}>'

def update_database_schema():
    inspector = inspect(db.engine)
    if not inspector.has_table('user'):
        db.create_all()
    else:
        columns = [col['name'] for col in inspector.get_columns('user')]
        if 'created_at' not in columns:
            with sqlite3.connect('users.db') as conn:
                conn.execute('ALTER TABLE user ADD COLUMN created_at DATETIME')
                conn.commit()
        if 'remember_token' not in columns:
            with sqlite3.connect('users.db') as conn:
                conn.execute('ALTER TABLE user ADD COLUMN remember_token VARCHAR(100)')
                conn.commit()
        if 'last_login' not in columns:
            with sqlite3.connect('users.db') as conn:
                conn.execute('ALTER TABLE user ADD COLUMN last_login DATETIME')
                conn.commit()

with app.app_context():
    update_database_schema()
    if not User.query.filter_by(email='admin@example.com').first():
        admin = User(
            email='admin@example.com',
            quota=None,
            approved=True,
            created_at=get_ist_time()
        )
        admin.set_password('password123')
        db.session.add(admin)
        db.session.commit()

AUTH_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <title>{{ title }} | MACC Chart Generator</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    @keyframes fadeIn {
      from { opacity: 0; transform: translateY(10px); }
      to { opacity: 1; transform: translateY(0); }
    }
    .fade-in {
      animation: fadeIn 0.5s ease-out;
    }
    .hover-scale {
      transition: transform 0.3s ease;
    }
    .hover-scale:hover {
      transform: scale(1.05);
    }
    ::-webkit-scrollbar {
      width: 6px;
    }
    ::-webkit-scrollbar-track {
      background: #f1f1f1;
    }
    ::-webkit-scrollbar-thumb {
      background: #4b5563;
      border-radius: 3px;
    }
    ::-webkit-scrollbar-thumb:hover {
      background: #374151;
    }
    input, button {
      -webkit-appearance: none;
      -moz-appearance: none;
      appearance: none;
    }
  </style>
</head>
<body class="min-h-screen bg-gray-100 flex flex-col">
  <header class="bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-md">
    <div class="container mx-auto px-4 py-4">
      <h1 class="text-xl sm:text-2xl font-bold tracking-tight text-center">MACC Chart Generator</h1>
    </div>
  </header>
  <main class="flex-grow container mx-auto px-4 py-8">
    <div class="bg-white shadow-lg rounded-xl p-6 fade-in w-full max-w-md mx-auto">
      <h2 class="text-xl sm:text-2xl font-semibold text-gray-800 text-center mb-6">{{ title }}</h2>
      <form method="POST" class="space-y-4">
        <div>
          <label for="username" class="block text-sm font-medium text-gray-700">Email</label>
          <input type="email" name="username" id="username" placeholder="Enter your email" required
                 class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 text-sm p-3">
        </div>
        <div>
          <label for="password" class="block text-sm font-medium text-gray-700">Password</label>
          <input type="password" name="password" id="password" placeholder="Enter your password" required
                 class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 text-sm p-3">
        </div>
        <div>
          <label for="remember" class="flex items-center text-sm font-medium text-gray-700">
            <input type="checkbox" name="remember" id="remember" class="mr-2" checked> Remember Me
          </label>
        </div>
        <div class="text-center">
          <button type="submit" class="w-full px-4 py-2 bg-indigo-600 text-white font-medium rounded-lg shadow-sm hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 transition duration-300 hover-scale text-sm">
            {{ title }}
          </button>
        </div>
      </form>
      <p class="text-center text-red-600 mt-4 text-sm">{{ message }}</p>
      <p class="text-center text-sm text-gray-600 mt-4">
        {% if title == "Login" %}
          Don't have an account? <a href="{{ url_for('register') }}" class="text-indigo-600 hover:underline">Register here</a>
        {% else %}
          Already have an account? <a href="{{ url_for('login') }}" class="text-indigo-600 hover:underline">Login here</a>
        {% endif %}
      </p>
    </div>
  </main>
  <footer class="bg-gray-800 text-white py-4">
    <div class="container mx-auto px-4 text-center">
      <p class="text-xs">© 2025 MACC Chart Generator. All rights reserved.</p>
    </div>
  </footer>
</body>
</html>
"""

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <title>MACC Chart Generator</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    @keyframes fadeIn {
      from { opacity: 0; transform: translateY(10px); }
      to { opacity: 1; transform: translateY(0); }
    }
    .fade-in {
      animation: fadeIn 0.5s ease-out;
    }
    .hover-scale {
      transition: transform 0.3s ease;
    }
    .hover-scale:hover {
      transform: scale(1.05);
    }
    ::-webkit-scrollbar {
      width: 6px;
    }
    ::-webkit-scrollbar-track {
      background: #f1f1f1;
    }
    ::-webkit-scrollbar-thumb {
      background: #4b5563;
      border-radius: 3px;
    }
    ::-webkit-scrollbar-thumb:hover {
      background: #374151;
    }
    .username-display {
      background: linear-gradient(45deg, #4b5563, #1f2937);
      color: white;
      padding: 0.5rem 1rem;
      border-radius: 8px;
      font-weight: 600;
      letter-spacing: 0.05em;
      box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
      position: absolute;
      top: 10px;
      right: 10px;
      font-size: 0.75rem;
    }
    @media (max-width: 640px) {
      .username-display {
        top: 60px;
        right: 10px;
        font-size: 0.7rem;
        padding: 0.4rem 0.8rem;
      }
    }
    input, button {
      -webkit-appearance: none;
      -moz-appearance: none;
      appearance: none;
    }
  </style>
</head>
<body class="min-h-screen bg-gray-100 flex flex-col">
  <header class="bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-md">
    <div class="container mx-auto px-4 py-4 flex flex-col sm:flex-row justify-between items-center">
      <h1 class="text-xl sm:text-2xl font-bold tracking-tight text-center sm:text-left">MACC Chart Generator</h1>
      <form method="POST" action="{{ url_for('logout') }}" class="mt-2 sm:mt-0">
        <button type="submit" class="w-full sm:w-auto bg-red-500 hover:bg-red-600 text-white font-medium py-2 px-4 rounded-lg transition duration-300 hover-scale text-sm">
          Logout
        </button>
      </form>
    </div>
  </header>
  <main class="flex-grow container mx-auto px-4 py-8 relative">
    <div class="username-display">
      UserId: {{ session['user'] }}
    </div>
    <div class="bg-white shadow-lg rounded-xl p-6 fade-in mt-12">
      <h2 class="text-xl sm:text-2xl font-semibold text-gray-800 text-center mb-6">Generate Your MACC Chart</h2>
      <form method="POST" class="space-y-4">
        <div>
          <label for="project_name" class="block text-sm font-medium text-gray-700">Organisation Name</label>
          <input type="text" name="project_name" id="project_name" placeholder="Enter Organisation Name" required
                 class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 text-sm p-3">
        </div>
        <div>
          <label for="categories" class="block text-sm font-medium text-gray-700">Interventions/Projects (comma-separated)</label>
          <input type="text" name="categories" id="categories" placeholder="Enter Interventions/Projects" required
                 class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 text-sm p-3">
        </div>
        <div>
          <label for="values" class="block text-sm font-medium text-gray-700">MACC Value In USD/Ton CO2 (comma-separated)</label>
          <input type="text" name="values" id="values" placeholder="Enter MACC Values" required
                 class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 text-sm p-3">
        </div>
        <div>
          <label for="widths" class="block text-sm font-medium text-gray-700">CO2 Abatement Value (Million Ton) (comma-separated)</label>
          <input type="text" name="widths" id="widths" placeholder="Enter CO2 Abatement Values" required
                 class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 text-sm p-3">
        </div>
        <div>
          <label for="line_value" class="block text-sm font-medium text-gray-700">Internal Carbon Price in USD/Ton CO2 (optional)</label>
          <input type="number" name="line_value" id="line_value" placeholder="Enter Internal Carbon Price"
                 class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 text-sm p-3">
        </div>
        <div class="text-center">
          <button type="submit" class="w-full px-4 py-2 bg-indigo-600 text-white font-medium rounded-lg shadow-sm hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 transition duration-300 hover-scale text-sm">
            Generate Chart
          </button>
        </div>
      </form>
      {% if chart %}
        <div class="mt-8">
          <h3 class="text-lg font-semibold text-gray-800 text-center mb-4">Generated Chart</h3>
          <div class="bg-gray-50 p-4 rounded-lg shadow-inner">
            <img src="data:image/png;base64,{{ chart }}" alt="MACC Chart" class="w-full h-auto mx-auto rounded-lg shadow-md hover-scale">
          </div>
        </div>
      {% endif %}
      {% if session['user'] == 'admin@example.com' %}
        <div class="mt-6 text-center">
          <a href="{{ url_for('admin') }}" class="inline-flex items-center px-4 py-2 bg-blue-600 text-white font-medium rounded-lg shadow-sm hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition duration-300 hover-scale text-sm">
            Go to Admin Panel
          </a>
        </div>
      {% endif %}
    </div>
  </main>
  <footer class="bg-gray-800 text-white py-4">
    <div class="container mx-auto px-4 text-center">
      <p class="text-xs">© 2025 MACC Chart Generator. All rights reserved.</p>
    </div>
  </footer>
</body>
</html>
"""

ADMIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <title>Admin Panel | MACC Chart Generator</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    @keyframes fadeIn {
      from { opacity: 0; transform: translateY(10px); }
      to { opacity: 1; transform: translateY(0); }
    }
    .fade-in {
      animation: fadeIn 0.5s ease-out;
    }
    .hover-scale {
      transition: transform 0.3s ease;
    }
    .hover-scale:hover {
      transform: scale(1.05);
    }
    ::-webkit-scrollbar {
      width: 6px;
    }
    ::-webkit-scrollbar-track {
      background: #f1f1f1;
    }
    ::-webkit-scrollbar-thumb {
      background: #4b5563;
      border-radius: 3px;
    }
    ::-webkit-scrollbar-thumb:hover {
      background: #374151;
    }
    input, button {
      -webkit-appearance: none;
      -moz-appearance: none;
      appearance: none;
    }
  </style>
</head>
<body class="min-h-screen bg-gray-100 flex flex-col">
  <header class="bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-md">
    <div class="container mx-auto px-4 py-4 flex flex-col sm:flex-row justify-between items-center">
      <h1 class="text-xl sm:text-2xl font-bold tracking-tight text-center sm:text-left">MACC Chart Generator</h1>
      <form method="POST" action="{{ url_for('logout') }}" class="mt-2 sm:mt-0">
        <button type="submit" class="w-full sm:w-auto bg-red-500 hover:bg-red-600 text-white font-medium py-2 px-4 rounded-lg transition duration-300 hover-scale text-sm">
          Logout
        </button>
      </form>
    </div>
  </header>
  <main class="flex-grow container mx-auto px-4 py-8">
    <div class="bg-white shadow-lg rounded-xl p-6 fade-in w-full max-w-2xl mx-auto">
      <h2 class="text-xl sm:text-2xl font-semibold text-gray-800 text-center mb-6">Admin Panel</h2>
      <form method="POST" class="space-y-4">
        <div>
          <label for="username" class="block text-sm font-medium text-gray-700">User Email</label>
          <input type="email" name="username" id="username" placeholder="Enter user email" required
                 class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 text-sm p-3">
        </div>
        <div>
          <label for="quota" class="block text-sm font-medium text-gray-700">New Quota (optional)</label>
          <input type="number" name="quota" id="quota" placeholder="Enter new quota"
                 class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 text-sm p-3">
        </div>
        <div class="flex flex-col sm:flex-row justify-center gap-3">
          <button type="submit" class="w-full sm:w-auto px-4 py-2 bg-indigo-600 text-white font-medium rounded-lg shadow-sm hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 transition duration-300 hover-scale text-sm">
            Update Quota
          </button>
          <button type="submit" name="approve" class="w-full sm:w-auto px-4 py-2 bg-green-600 text-white font-medium rounded-lg shadow-sm hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2 transition duration-300 hover-scale text-sm">
            Approve User
          </button>
          <button type="submit" name="reset_password" class="w-full sm:w-auto px-4 py-2 bg-yellow-600 text-white font-medium rounded-lg shadow-sm hover:bg-yellow-700 focus:outline-none focus:ring-2 focus:ring-yellow-500 focus:ring-offset-2 transition duration-300 hover-scale text-sm">
            Reset Password
          </button>
        </div>
      </form>
      <p class="text-center text-green-600 mt-4 text-sm font-semibold">{{ message }}</p>
      <h3 class="text-lg font-semibold text-gray-800 text-center mt-6 mb-4">Current Users</h3>
      <ul class="space-y-2">
        {% for user in users %}
          <li class="bg-gray-50 p-3 rounded-lg shadow-sm text-sm">
            <span class="font-medium">{{ user.email }}</span> - 
            Quota: {{ user.quota if user.quota is not none else "Unlimited" }} - 
            Approved: {{ "Yes" if user.approved else "No" }}
          </li>
        {% endfor %}
      </ul>
      <div class="text-center mt-6">
        <a href="{{ url_for('index') }}" class="inline-flex items-center px-4 py-2 bg-blue-600 text-white font-medium rounded-lg shadow-sm hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition duration-300 hover-scale text-sm">
          Back to Main App
        </a>
      </div>
    </div>
  </main>
  <footer class="bg-gray-800 text-white py-4">
    <div class="container mx-auto px-4 text-center">
      <p class="text-xs">© 2025 MACC Chart Generator. All rights reserved.</p>
    </div>
  </footer>
</body>
</html>
"""

@app.before_request
def auto_login():
    if 'user' not in session and 'remember_token' in request.cookies:
        token = request.cookies.get('remember_token')
        logging.debug(f"Checking remember_token: {token}")
        user = User.query.filter_by(remember_token=token).first()
        if user:
            if user.approved:
                session['user'] = user.email
                user.last_login = get_ist_time()
                try:
                    db.session.commit()
                    logging.info(f"Auto-login successful for {user.email} at {user.last_login.strftime('%Y-%m-%d %H:%M:%S %Z')}")
                except Exception as e:
                    logging.error(f"Failed to update last_login for {user.email}: {e}")
                    db.session.rollback()
            else:
                logging.warning(f"Auto-login failed for {user.email}: not approved")
        else:
            logging.warning(f"Auto-login failed: invalid remember_token {token}")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        remember = 'remember' in request.form
        logging.debug(f"Login attempt for {username}, remember={remember}")
        if not re.match(EMAIL_REGEX, username):
            logging.error(f"Invalid email format: {username}")
            return render_template_string(AUTH_TEMPLATE, title="Login", message="Username must be a valid email address.")
        
        user = User.query.filter_by(email=username).first()
        if user and user.check_password(password):
            if not user.approved:
                logging.warning(f"Login failed for {username}: awaiting approval")
                return render_template_string(AUTH_TEMPLATE, title="Login", message="Awaiting admin approval.")
            session["user"] = username
            user.last_login = get_ist_time()
            ist_time = user.last_login
            try:
                db.session.commit()
                logging.info(f"User {username} logged in at {ist_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
            except Exception as e:
                logging.error(f"Failed to update last_login for {username}: {e}")
                db.session.rollback()
                return render_template_string(AUTH_TEMPLATE, title="Login", message="Internal server error.")
            if remember:
                token = secrets.token_urlsafe(32)
                user.remember_token = token
                try:
                    db.session.commit()
                    logging.info(f"Remember token set for {username}: {token}")
                except Exception as e:
                    logging.error(f"Failed to save remember token for {username}: {e}")
                    db.session.rollback()
                    return render_template_string(AUTH_TEMPLATE, title="Login", message="Internal server error.")
                response = redirect(url_for("index"))
                response.set_cookie('remember_token', token, max_age=31536000, httponly=True, samesite='Lax')
                logging.debug(f"Cookie set for {username} with max_age=31536000")
                return response
            return redirect(url_for("index"))
        logging.warning(f"Login failed for {username}: invalid credentials")
        return render_template_string(AUTH_TEMPLATE, title="Login", message="Invalid credentials.")
    return render_template_string(AUTH_TEMPLATE, title="Login", message="")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        logging.debug(f"Registration attempt for {username}")
        if not re.match(EMAIL_REGEX, username):
            logging.error(f"Invalid email format for registration: {username}")
            return render_template_string(AUTH_TEMPLATE, title="Register", message="Username must be a valid email address.")
        
        if User.query.filter_by(email=username).first():
            logging.warning(f"Registration failed: {username} already exists")
            return render_template_string(AUTH_TEMPLATE, title="Register", message="User already exists.")
        
        new_user = User(email=username, quota=3, approved=False)
        new_user.set_password(password)
        try:
            db.session.add(new_user)
            db.session.commit()
            logging.info(f"User registered: {username}")
            return render_template_string(AUTH_TEMPLATE, title="Login", message="Registered. Awaiting admin approval.")
        except Exception as e:
            logging.error(f"Registration failed for {username}: {e}")
            db.session.rollback()
            return render_template_string(AUTH_TEMPLATE, title="Register", message="Internal server error.")
    return render_template_string(AUTH_TEMPLATE, title="Register", message="")

@app.route("/logout", methods=["POST"])
def logout():
    if 'user' in session:
        user = User.query.filter_by(email=session['user']).first()
        if user:
            user.remember_token = None
            try:
                db.session.commit()
                logging.info(f"Remember token cleared for {user.email}")
            except Exception as e:
                logging.error(f"Failed to clear remember token for {user.email}: {e}")
                db.session.rollback()
    session.pop("user", None)
    response = redirect(url_for("login"))
    response.delete_cookie('remember_token')
    logging.info("User logged out")
    return response

@app.route("/", methods=["GET", "POST"])
def index():
    if "user" not in session:
        logging.debug("No user in session, redirecting to login")
        return redirect(url_for("login"))

    user = User.query.filter_by(email=session["user"]).first()
    if not user:
        logging.error(f"Session user {session['user']} not found in database")
        session.pop("user", None)
        return redirect(url_for("login"))
    if not user.approved:
        logging.warning(f"Access denied for {user.email}: not approved")
        return "<h2>Access Denied.</h2><p>Your account is not yet approved by the admin.</p>"

    if user.quota is not None and user.quota <= 0:
        logging.info(f"Quota reached for {user.email}")
        return render_template_string("""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <title>Limit Reached</title>
  <style>
    body {
      font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
      background-color: #f8f9fa;
      margin: 0;
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: 100vh;
      overflow: hidden;
    }
    .card {
      background: white;
      padding: 1.5rem;
      border-radius: 10px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.1);
      max-width: 90%;
      width: 100%;
      text-align: center;
    }
    h2 {
      color: #dc3545;
      margin-bottom: 0.75rem;
      font-size: 1.5rem;
    }
    p {
      color: #555;
      margin-bottom: 1rem;
      font-size: 0.9rem;
    }
    .logout-button {
      background-color: #dc3545;
      color: white;
      padding: 8px 12px;
      border: none;
      border-radius: 5px;
      cursor: pointer;
      font-size: 0.9rem;
    }
    .logout-button:hover {
      background-color: #c82333;
    }
  </style>
</head>
<body>
  <div class="card">
    <h2>Usage Limit Reached</h2>
    <p>Your chart generation limit has been reached.</p>
    <p>Please contact the admin to request additional access.</p>
    <form method="POST" action="{{ url_for('logout') }}">
      <button type="submit" class="logout-button">Logout</button>
    </form>
  </div>
</body>
</html>
""")

    chart = None
    if request.method == "POST":
        try:
            project_name = request.form["project_name"]
            categories = request.form["categories"].split(",")
            values = list(map(float, request.form["values"].split(",")))
            widths = list(map(float, request.form["widths"].split(",")))
            line_value = request.form.get("line_value", None)
            line_value = float(line_value) if line_value else None

            if len(categories) != len(values) or len(categories) != len(widths):
                logging.error(f"Input mismatch for {user.email}: categories={len(categories)}, values={len(values)}, widths={len(widths)}")
                return "Error: Mismatched lengths of inputs."

            total_abatement = sum(widths)
            x_positions = np.cumsum([0] + widths[:-1])
            colors = ["#" + ''.join(random.choices('0123456786789ABCDEF', k=6)) for _ in categories]

            plt.figure(figsize=(20, 25))
            plt.bar(x_positions, values, width=widths, color=colors, edgecolor='black', align='edge')

            for x, y, w in zip(x_positions, values, widths):
                plt.text(x + w / 2, y + 1, str(y), ha='center', rotation=90, fontsize=20)

            plt.xticks(x_positions + np.array(widths) / 2, categories, ha="center", rotation=90, fontsize=20)
            plt.title(f"Marginal Abatement Cost Curve (MACC) - {project_name}", fontsize=24)
            plt.xlabel("CO2 Abatement, Million Tonne", fontsize=20)
            plt.ylabel("MACC Values USD/Ton CO2", fontsize=20)

            for x, width in zip(x_positions, widths):
                plt.text(x + width / 2, -1.5, f"{int(width)}", ha="center", fontsize=20)

            if line_value is not None:
                plt.axhline(y=line_value, color='red', linestyle='--', linewidth=2)
                plt.text(x_positions[0] - 0.2, line_value + 1,
                         f"Internal carbon price {line_value}", color='black', fontsize=20, ha='left')

            plt.tick_params(axis='y', labelsize=20)
            plt.subplots_adjust(bottom=0.3, right=0.95)

            last_x = x_positions[-1]
            last_width = widths[-1]
            plt.text(last_x + last_width / 2, -10, f"Total: {total_abatement:.1f}",
                     ha='center', fontsize=20, color="black")

            buf = io.BytesIO()
            plt.savefig(buf, format="png")
            buf.seek(0)
            chart = base64.b64encode(buf.getvalue()).decode("utf-8")
            buf.close()
            plt.close()

            if user.quota is not None and user.email != 'admin@example.com':
                user.quota = max(0, user.quota - 1)
                try:
                    db.session.commit()
                    logging.info(f"Quota decremented for {user.email}: new quota={user.quota}")
                except Exception as e:
                    logging.error(f"Failed to decrement quota for {user.email}: {e}")
                    db.session.rollback()

        except Exception as e:
            logging.error(f"Chart generation failed for {user.email}: {e}")
            return f"Error processing your input: {e}"

    logging.debug(f"Rendering index page for {user.email}")
    return render_template_string(HTML_TEMPLATE, chart=chart, last_login=user.last_login)

@app.route("/admin", methods=["GET", "POST"])
def admin():
    if session.get("user") != "admin@example.com":
        logging.debug("Admin access attempt by non-admin, redirecting to login")
        return redirect(url_for("login"))

    message = ""
    if request.method == "POST":
        target_user_email = request.form["username"]
        logging.debug(f"Admin action for {target_user_email}")
        if not re.match(EMAIL_REGEX, target_user_email):
            message = "Username must be a valid email address."
            logging.error(f"Invalid email format in admin panel: {target_user_email}")
        elif "approve" in request.form:
            target_user = User.query.filter_by(email=target_user_email).first()
            if target_user:
                target_user.approved = True
                try:
                    db.session.commit()
                    message = f"{target_user_email} approved."
                    logging.info(f"User {target_user_email} approved")
                except Exception as e:
                    logging.error(f"Failed to approve {target_user_email}: {e}")
                    db.session.rollback()
                    message = "Internal server error."
            else:
                message = "User not found."
                logging.warning(f"User {target_user_email} not found for approval")
        elif "reset_password" in request.form:
            target_user = User.query.filter_by(email=target_user_email).first()
            if target_user:
                new_password = secrets.token_urlsafe(12)
                target_user.set_password(new_password)
                try:
                    db.session.commit()
                    message = f"Password reset for {target_user_email}. New temporary password: {new_password}"
                    logging.info(f"Password reset for {target_user_email}")
                except Exception as e:
                    logging.error(f"Failed to reset password for {target_user_email}: {e}")
                    db.session.rollback()
                    message = "Internal server error."
            else:
                message = "User not found."
                logging.warning(f"User {target_user_email} not found for password reset")
        else:
            try:
                new_quota = int(request.form["quota"])
                target_user = User.query.filter_by(email=target_user_email).first()
                if target_user:
                    target_user.quota = new_quota
                    try:
                        db.session.commit()
                        message = f"Quota updated for {target_user_email}"
                        logging.info(f"Quota updated for {target_user_email}: {new_quota}")
                    except Exception as e:
                        logging.error(f"Failed to update quota for {target_user_email}: {e}")
                        db.session.rollback()
                        message = "Internal server error."
                else:
                    message = "User not found."
                    logging.warning(f"User {target_user_email} not found for quota update")
            except ValueError:
                message = "Invalid quota input."
                logging.error(f"Invalid quota input for {target_user_email}")

    users = User.query.all()
    logging.debug("Rendering admin panel")
    return render_template_string(ADMIN_TEMPLATE, users=users, message=message)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    logging.info(f"Starting Flask app on port {port}")
    app.run(host="0.0.0.0", port=port, debug=True)