import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend

from flask import Flask, request, render_template_string, redirect, url_for, session
import matplotlib.pyplot as plt
import numpy as np
import io
import base64
import os
import random
import json
import re

app = Flask(__name__)
app.secret_key = "your_secret_key"  # Change this in production

# Path to store user credentials
USERS_FILE = "users.json"

# Regular expression for email validation
EMAIL_REGEX = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

# Load users from JSON file or initialize with default admin
def load_users():
    try:
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        # Initialize with default admin user
        default_users = {
            "admin@example.com": {"password": "password123", "quota": None, "approved": True}
        }
        save_users(default_users)
        return default_users

# Save users to JSON file
def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=4)

# Initialize users
users = load_users()

# Templates
AUTH_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{{ title }}</title>
  <style>
    body {
      font-family: Arial, sans-serif;
      padding: 2rem;
      background-color: #f9f9f9;
    }
    h2 {
      text-align: center;
      color: #333;
    }
    form {
      display: flex;
      flex-direction: column;
      margin: auto;
      max-width: 400px;
    }
    input, button {
      padding: 0.75em;
      margin: 0.5em 0;
      font-size: 1em;
    }
    button {
      background-color: #007bff;
      color: white;
      border: none;
      cursor: pointer;
    }
    button:hover {
      background-color: #0056b3;
    }
    a {
      color: #007bff;
      text-decoration: none;
    }
    p {
      text-align: center;
    }
  </style>
</head>
<body>
  <h2>{{ title }}</h2>
  <form method="POST">
    <input name="username" type="email" placeholder="Email" required>
    <input name="password" type="password" placeholder="Password" required>
    <button type="submit">{{ title }}</button>
  </form>
  <p>{{ message }}</p>
  {% if title == "Login" %}
    <p>Don't have an account? <a href="{{ url_for('register') }}">Register here</a></p>
  {% else %}
    <p>Already have an account? <a href="{{ url_for('login') }}">Login here</a></p>
  {% endif %}
</body>
</html>
"""

HTML_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>MACC Chart Generator</title>
  <style>
    body {
      font-family: Arial, sans-serif;
      padding: 2rem;
      background-color: #f4f4f4;
      margin: 0;
      overflow-x: hidden;
      height: 100vh;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
    }
    h2, h3 {
      text-align: center;
      color: #333;
    }
    form {
      display: flex;
      flex-direction: column;
      margin: auto;
      max-width: 600px;
    }
    input, button {
      padding: 0.75em;
      margin: 0.5em 0;
      font-size: 1em;
    }
    button {
      background-color: #28a745;
      color: white;
      border: none;
      cursor: pointer;
    }
    button:hover {
      background-color: #218838;
    }
    img {
      display: block;
      margin: 2rem auto;
      max-width: 100%;
      height: auto;
      border: 1px solid #ccc;
    }
    a {
      display: block;
      text-align: center;
      margin-top: 1rem;
      color: #007bff;
      text-decoration: none;
    }
    a:hover {
      text-decoration: underline;
    }
    .logout-button {
      background-color: #dc3545;
      padding: 10px 15px;
      color: white;
      border: none;
      position: fixed;
      top: 10px;
      right: 10px;
      font-size: 14px;
      cursor: pointer;
    }
    .logout-button:hover {
      background-color: #c82333;
    }
     .admin-link a {
      color: #28a745;
      text-decoration: none;
    }
    .admin-link a:hover {
      text-decoration: underline;
    }
    .admin-panel-link {
      text-align: center;
      position: relative;
      bottom: 20px;
      font-size: 16px;
    }
     .footer, .admin-link {
      text-align: center;
      margin-top: 20px;
    }
    @media (max-width: 768px) {
      body {
        padding: 1rem;
      }
      .logout-button {
        font-size: 12px;
        padding: 8px 12px;
      }
      .admin-panel-link {
        font-size: 14px;
      }
    }
  </style>
</head>
<body>
  <h2>MACC Chart Generator</h2>
  <form method="POST">
    <input type="text" name="project_name" placeholder="Enter Organisation Name" required><br>
    <input type="text" name="categories" placeholder="Enter Interventions/Projects (comma-separated)" required><br>
    <input type="text" name="values" placeholder="Enter MACC Value In USD/Ton CO2 (comma-separated)" required><br>
    <input type="text" name="widths" placeholder="Enter CO2 Abatement Value (Million Ton) (comma-separated)" required><br>
    <input type="number" name="line_value" placeholder="Enter Internal carbon price in USD/Ton CO2 (optional)"><br>
    <button type="submit">Generate Chart</button>
  </form>

  {% if chart %}
    <h3>Generated Chart:</h3>
    <img src="data:image/png;base64,{{ chart }}" alt="MACC Chart">
  {% endif %}

  <form method="POST" action="{{ url_for('logout') }}">
    <button type="submit" class="logout-button">Logout</button>
  </form>

  {% if session['user'] == 'admin@example.com' %}
    <div class="admin-link">
      <p><a href="{{ url_for('admin') }}">Go to Admin Panel</a></p>
    </div>
  {% endif %}
</body>
</html>
"""

# Routes
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = users.get(username)
        if not re.match(EMAIL_REGEX, username):
            return render_template_string(AUTH_TEMPLATE, title="Login", message="Username must be a valid email address.")
        if user and user["password"] == password:
            if not user.get("approved", False):
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
        if username in users:
            return render_template_string(AUTH_TEMPLATE, title="Register", message="User already exists.")
        users[username] = {"password": password, "quota": 3, "approved": False}
        save_users(users)
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

    user = session["user"]
    user_data = users.get(user)
    if not user_data.get("approved", False):
        return "<h2>Access Denied.</h2><p>Your account is not yet approved by the admin.</p>"

    quota = user_data.get("quota")
    if quota == 0:
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
            plt.ylabel("Internal Carbon Pricing USD/Ton CO2", fontsize=20)

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

            if quota is not None:
                users[user]["quota"] -= 1
                save_users(users)

        except Exception as e:
            return f"Error processing your input: {e}"

    return render_template_string(HTML_TEMPLATE, chart=chart)

@app.route("/admin", methods=["GET", "POST"])
def admin():
    if session.get("user") != "admin@example.com":
        return redirect(url_for("login"))

    message = ""
    if request.method == "POST":
        target_user = request.form["username"]
        if not re.match(EMAIL_REGEX, target_user):
            message = "Username must be a valid email address."
        elif "approve" in request.form:
            if target_user in users:
                users[target_user]["approved"] = True
                save_users(users)
                message = f"{target_user} approved."
            else:
                message = "User not found."
        else:
            try:
                new_quota = int(request.form["quota"])
                if target_user in users:
                    users[target_user]["quota"] = new_quota
                    save_users(users)
                    message = f"Quota updated for {target_user}"
                else:
                    message = "User not found."
            except ValueError:
                message = "Invalid quota input."

    return render_template_string("""
<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Admin Panel</title>
  <style>
    body { font-family: Arial, sans-serif; background-color: #f4f4f4; padding: 2rem; }
    .container { max-width: 600px; margin: auto; background: white; padding: 2rem; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); }
    h2, h3 { text-align: center; }
    form { display: flex; flex-direction: column; gap: 1rem; margin-top: 1rem; }
    input {
      padding: 0.75em;
      margin: 0.5em 0;
      font-size: 1em;
      width: 100%;
      box-sizing: border-box;
    }
    button { background-color: #007bff; color: white; border: none; cursor: pointer; }
    button:hover { background-color: #0056b3; }
    .message { text-align: center; color: green; font-weight: bold; }
    ul { list-style-type: none; padding: 0; }
    li { background: #f1f1f1; margin: 0.3rem 0; padding: 0.5rem; border-radius: 5px; }
    a { display: block; text-align: center; margin-top: 2rem; color: #007bff; text-decoration: none; }
    a:hover { text-decoration: underline; }
  </style>
</head>
<body>
  <div class="container">
    <h2>Admin Panel</h2>
    <form method="POST">
      <input name="username" type="email" placeholder="User Email" required>
      <input name="quota" type="number" placeholder="New quota (if updating)">
      <button type="submit">Update Quota</button>
      <button type="submit" name="approve">Approve User</button>
    </form>
    <p class="message">{{ message }}</p>
    <h3>Current Users:</h3>
    <ul>
    {% for username, data in users.items() %}
      <li>
        <strong>{{ username }}</strong> -
        Quota: {{ data.quota if data.quota is not none else "Unlimited" }} -
        Approved: {{ "Yes" if data.get("approved") else "No" }}
      </li>
    {% endfor %}
    </ul>
    <a href="{{ url_for('index') }}">← Back to Main App</a>
  </div>
</body>
</html>
""", users=users, message=message)

# Run the app
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)