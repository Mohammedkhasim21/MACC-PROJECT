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
import uuid

app = Flask(__name__)
app.secret_key = str(uuid.uuid4())  # Secure random secret key

# Configure SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Regular expression for email validation
EMAIL_REGEX = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

# Database model for User
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    quota = db.Column(db.Integer, nullable=True)
    approved = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<User {self.email}>'

# Check and update database schema
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

# Create database tables and update schema
with app.app_context():
    update_database_schema()
    # Create default admin user if not exists
    if not User.query.filter_by(email='admin@example.com').first():
        admin = User(
            email='admin@example.com',
            password='password123',
            quota=None,
            approved=True,
            created_at=datetime.utcnow()
        )
        db.session.add(admin)
        db.session.commit()

# Authentication Template (Login and Register)
AUTH_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
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
      width: 8px;
    }
    ::-webkit-scrollbar-track {
      background: #f1f1f1;
    }
    ::-webkit-scrollbar-thumb {
      background: #4b5563;
      border-radius: 4px;
    }
    ::-webkit-scrollbar-thumb:hover {
      background: #374151;
    }
  </style>
</head>
<body class="min-h-screen bg-gray-100 flex flex-col">
  <!-- Header -->
  <header class="bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-lg">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
      <h1 class="text-2xl sm:text-3xl font-bold tracking-tight text-center">Welcome to MACC Chart Generator</h1>
    </div>
  </header>

  <!-- Main Content -->
  <main class="flex-grow max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
    <div class="bg-white shadow-2xl rounded-2xl p-8 fade-in max-w-md mx-auto">
      <h2 class="text-2xl sm:text-3xl font-semibold text-gray-800 text-center mb-8">{{ title }}</h2>
      <form method="POST" class="space-y-6">
        <div>
          <label for="username" class="block text-sm font-medium text-gray-700">Email</label>
          <input type="email" name="username" id="username" placeholder="Enter your email" required
                 class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm p-3">
        </div>
        <div>
          <label for="password" class="block text-sm font-medium text-gray-700">Password</label>
          <input type="password" name="password" id="password" placeholder="Enter your password" required
                 class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm p-3">
        </div>
        <div class="text-center">
          <button type="submit" class="inline-flex items-center px-6 py-3 bg-indigo-600 text-white font-semibold rounded-lg shadow-md hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 transition duration-300 hover-scale">
            {{ title }}
          </button>
        </div>
      </form>
      <p class="text-center text-red-600 mt-4">{{ message }}</p>
      <p class="text-center text-sm text-gray-600 mt-4">
        {% if title == "Login" %}
          Don't have an account? <a href="{{ url_for('register') }}" class="text-indigo-600 hover:underline">Register here</a>
        {% else %}
          Already have an account? <a href="{{ url_for('login') }}" class="text-indigo-600 hover:underline">Login here</a>
        {% endif %}
      </p>
    </div>
  </main>

  <!-- Footer -->
  <footer class="bg-gray-800 text-white py-6">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
      <p class="text-sm">© 2025 MACC Chart Generator. All rights reserved.</p>
    </div>
  </footer>
</body>
</html>
"""

# Main App Template (Chart Generation Page)
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
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
      width: 8px;
    }
    ::-webkit-scrollbar-track {
      background: #f1f1f1;
    }
    ::-webkit-scrollbar-thumb {
      background: #4b5563;
      border-radius: 4px;
    }
    ::-webkit-scrollbar-thumb:hover {
      background: #374151;
    }
  </style>
</head>
<body class="min-h-screen bg-gray-100 flex flex-col">
  <!-- Header -->
  <header class="bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-lg">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 flex justify-between items-center">
      <h1 class="text-2xl sm:text-3xl font-bold tracking-tight">MACC Chart Generator</h1>
      <form method="POST" action="{{ url_for('logout') }}">
        <button type="submit" class="bg-red-500 hover:bg-red-600 text-white font-semibold py-2 px-4 rounded-lg transition duration-300 hover-scale">
          Logout
        </button>
      </form>
    </div>
  </header>

  <!-- Main Content -->
  <main class="flex-grow max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
    <div class="bg-white shadow-2xl rounded-2xl p-8 fade-in">
      <h2 class="text-2xl sm:text-3xl font-semibold text-gray-800 text-center mb-8">Generate Your MACC Chart</h2>
      <form method="POST" class="space-y-6 max-w-3xl mx-auto">
        <div>
          <label for="project_name" class="block text-sm font-medium text_gray-700">Organisation Name</label>
          <input type="text" name="project_name" id="project_name" placeholder="Enter Organisation Name" required
                 class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm p-3">
        </div>
        <div>
          <label for="categories" class="block text-sm font-medium text-gray-700">Interventions/Projects (comma-separated)</label>
          <input type="text" name="categories" id="categories" placeholder="Enter Interventions/Projects" required
                 class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm p-3">
        </div>
        <div>
          <label for="values" class="block text-sm font-medium text-gray-700">MACC Value In USD/Ton CO2 (comma-separated)</label>
          <input type="text" name="values" id="values" placeholder="Enter MACC Values" required
                 class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm p-3">
        </div>
        <div>
          <label for="widths" class="block text-sm font-medium text-gray-700">CO2 Abatement Value (Million Ton) (comma-separated)</label>
          <input type="text" name="widths" id="widths" placeholder="Enter CO2 Abatement Values" required
                 class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm p-3">
        </div>
        <div>
          <label for="line_value" class="block text-sm font-medium text-gray-700">Internal Carbon Price in USD/Ton CO2 (optional)</label>
          <input type="number" name="line_value" id="line_value" placeholder="Enter Internal Carbon Price"
                 class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm p-3">
        </div>
        <div class="text-center">
          <button type="submit" class="inline-flex items-center px-6 py-3 bg-indigo-600 text-white font-semibold rounded-lg shadow-md hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 transition duration-300 hover-scale">
            Generate Chart
          </button>
        </div>
      </form>

      {% if chart %}
        <div class="mt-12">
          <h3 class="text-xl font-semibold text-gray-800 text-center mb-6">Generated Chart</h3>
          <div class="bg-gray-50 p-6 rounded-lg shadow-inner">
            <img src="data:image/png;base64,{{ chart }}" alt="MACC Chart" class="max-w-full h-auto mx-auto rounded-lg shadow-md hover-scale">
          </div>
        </div>
      {% endif %}

      {% if session['user'] == 'admin@example.com' %}
        <div class="mt-8 text-center">
          <a href="{{ url_for('admin') }}" class="inline-flex items-center px-6 py-3 bg-blue-600 text-white font-semibold rounded-lg shadow-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition duration-300 hover-scale">
            Go to Admin Panel
          </a>
        </div>
      {% endif %}
    </div>
  </main>

  <!-- Footer -->
  <footer class="bg-gray-800 text-white py-6">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
      <p class="text-sm">© 2025 MACC Chart Generator. All rights reserved.</p>
    </div>
  </footer>
</body>
</html>
"""

# Admin Panel Template
ADMIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
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
      width: 8px;
    }
    ::-webkit-scrollbar-track {
      background: #f1f1f1;
    }
    ::-webkit-scrollbar-thumb {
      background: #4b5563;
      border-radius: 4px;
    }
    ::-webkit-scrollbar-thumb:hover {
      background: #374151;
    }
  </style>
</head>
<body class="min-h-screen bg-gray-100 flex flex-col">
  <!-- Header -->
  <header class="bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-lg">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 flex justify-between items-center">
      <h1 class="text-2xl sm:text-3xl font-bold tracking-tight">MACC Chart Generator</h1>
      <form method="POST" action="{{ url_for('logout') }}">
        <button type="submit" class="bg-red-500 hover:bg-red-600 text-white font-semibold py-2 px-4 rounded-lg transition duration-300 hover-scale">
          Logout
        </button>
      </form>
    </div>
  </header>

  <!-- Main Content -->
  <main class="flex-grow max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
    <div class="bg-white shadow-2xl rounded-2xl p-8 fade-in max-w-2xl mx-auto">
      <h2 class="text-2xl sm:text-3xl font-semibold text-gray-800 text-center mb-8">Admin Panel</h2>
      <form method="POST" class="space-y-6">
        <div>
          <label for="username" class="block text-sm font-medium text-gray-700">User Email</label>
          <input type="email" name="username" id="username" placeholder="Enter user email" required
                 class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm p-3">
        </div>
        <div>
          <label for="quota" class="block text-sm font-medium text-gray-700">New Quota (optional)</label>
          <input type="number" name="quota" id="quota" placeholder="Enter new quota"
                 class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm p-3">
        </div>
        <div class="flex justify-center gap-4">
          <button type="submit" class="inline-flex items-center px-6 py-3 bg-indigo-600 text-white font-semibold rounded-lg shadow-md hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 transition duration-300 hover-scale">
            Update Quota
          </button>
          <button type="submit" name="approve" class="inline-flex items-center px-6 py-3 bg-green-600 text-white font-semibold rounded-lg shadow-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2 transition duration-300 hover-scale">
            Approve User
          </button>
        </div>
      </form>
      <p class="text-center text-green-600 mt-4 font-semibold">{{ message }}</p>
      <h3 class="text-xl font-semibold text-gray-800 text-center mt-8 mb-4">Current Users</h3>
      <ul class="space-y-3">
        {% for user in users %}
          <li class="bg-gray-50 p-4 rounded-lg shadow-sm">
            <span class="font-medium">{{ user.email }}</span> - 
            Quota: {{ user.quota if user.quota is not none else "Unlimited" }} - 
            Approved: {{ "Yes" if user.approved else "No" }}
          </li>
        {% endfor %}
      </ul>
      <div class="text-center mt-8">
        <a href="{{ url_for('index') }}" class="inline-flex items-center px-6 py-3 bg-blue-600 text-white font-semibold rounded-lg shadow-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition duration-300 hover-scale">
          Back to Main App
        </a>
      </div>
    </div>
  </main>

  <!-- Footer -->
  <footer class="bg-gray-800 text-white py-6">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
      <p class="text-sm">© 2025 MACC Chart Generator. All rights reserved.</p>
    </div>
  </footer>
</body>
</html>
"""

# Routes
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        if not re.match(EMAIL_REGEX, username):
            return render_template_string(AUTH_TEMPLATE, title="Login", message="Username must be a valid email address.")
        
        user = User.query.filter_by(email=username).first()
        if user and user.password == password:
            if not user.approved:
                return render_template_string(AUTH_TEMPLATE, title="Login", message="Awaiting admin approval.")
            session["user"] = username
            return redirect(url_for("index"))
        return render_template_string(AUTH_TEMPLATE, title="Login", message="Invalid credentials.")
    return render_template_string(AUTH_TEMPLATE, title="Login", message="")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        if not re.match(EMAIL_REGEX, username):
            return render_template_string(AUTH_TEMPLATE, title="Register", message="Username must be a valid email address.")
        
        if User.query.filter_by(email=username).first():
            return render_template_string(AUTH_TEMPLATE, title="Register", message="User already exists.")
        
        new_user = User(email=username, password=password, quota=3, approved=False)
        db.session.add(new_user)
        db.session.commit()
        return render_template_string(AUTH_TEMPLATE, title="Login", message="Registered. Awaiting admin approval.")
    return render_template_string(AUTH_TEMPLATE, title="Register", message="")

@app.route("/logout", methods=["POST"])
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))

@app.route("/", methods=["GET", "POST"])
def index():
    if "user" not in session:
        return redirect(url_for("login"))

    user = User.query.filter_by(email=session["user"]).first()
    if not user.approved:
        return "<h2>Access Denied.</h2><p>Your account is not yet approved by the admin.</p>"

    if user.quota is not None and user.quota <= 0:
        return render_template_string("""
<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Limit Reached</title>
  <style>
    body {
      font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
      background-color: #f8f9fa;
      margin: 0;
      padding: 2rem;
      display: flex;
      justify-content: center;
      align-items: center;
      height: 100vh;
    }
    .card {
      background: white;
      padding: 2rem;
      border-radius: 12px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.1);
      max-width: 400px;
      width: 100%;
      text-align: center;
    }
    h2 {
      color: #dc3545;
      margin-bottom: 1rem;
    }
    p {
      color: #555;
      margin-bottom: 2rem;
    }
    a.button {
      display: inline-block;
      background-color: #007bff;
      color: white;
      padding: 0.75em 1.5em;
      border-radius: 5px;
      text-decoration: none;
      font-size: 1rem;
    }
    a.button:hover {
      background-color: #0056b3;
    }
    .logout-button {
      background-color: #dc3545;
      color: white;
      padding: 10px 15px;
      border: none;
      border-radius: 5px;
      cursor: pointer;
      font-size: 16px;
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
                return "Error: Mismatched lengths of inputs."

            total_abatement = sum(widths)
            x_positions = np.cumsum([0] + widths[:-1])
            colors = ["#" + ''.join(random.choices('0123456789ABCDEF', k=6)) for _ in categories]

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
            plt.text(last_x + last_width / 2, -6, f"Total: {total_abatement:.1f}",
                     ha='center', fontsize=20, color="black")

            buf = io.BytesIO()
            plt.savefig(buf, format="png")
            buf.seek(0)
            chart = base64.b64encode(buf.getvalue()).decode("utf-8")
            buf.close()
            plt.close()

            # Decrement quota for non-admin users with a valid quota
            if user.quota is not None and user.email != 'admin@example.com':
                user.quota = max(0, user.quota - 1)
                db.session.commit()

        except Exception as e:
            return f"Error processing your input: {e}"

    return render_template_string(HTML_TEMPLATE, chart=chart)

@app.route("/admin", methods=["GET", "POST"])
def admin():
    if session.get("user") != "admin@example.com":
        return redirect(url_for("login"))

    message = ""
    if request.method == "POST":
        target_user_email = request.form["username"]
        if not re.match(EMAIL_REGEX, target_user_email):
            message = "Username must be a valid email address."
        elif "approve" in request.form:
            target_user = User.query.filter_by(email=target_user_email).first()
            if target_user:
                target_user.approved = True
                db.session.commit()
                message = f"{target_user_email} approved."
            else:
                message = "User not found."
        else:
            try:
                new_quota = int(request.form["quota"])
                target_user = User.query.filter_by(email=target_user_email).first()
                if target_user:
                    target_user.quota = new_quota
                    db.session.commit()
                    message = f"Quota updated for {target_user_email}"
                else:
                    message = "User not found."
            except ValueError:
                message = "Invalid quota input."

    users = User.query.all()
    return render_template_string(ADMIN_TEMPLATE, users=users, message=message)

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)