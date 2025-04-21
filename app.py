import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend

from flask import Flask, request, render_template_string, redirect, url_for, session
import matplotlib.pyplot as plt  # type: ignore
import numpy as np
import io
import base64
import os
import random

app = Flask(__name__)
app.secret_key = "your_secret_key"  # Change this in production

# In-memory user storage
users = {
    "admin": {"password": "password123", "quota": None}
}

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
    <input name="username" placeholder="Username" required>
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

  {% if session['user'] == 'admin' %}
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
        if username in users and users[username]["password"] == password:
            session["user"] = username
            return redirect(url_for("index"))
        return render_template_string(AUTH_TEMPLATE, title="Login", message="Invalid credentials.")
    return render_template_string(AUTH_TEMPLATE, title="Login", message="")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        if username in users:
            return render_template_string(AUTH_TEMPLATE, title="Register", message="User already exists.")
        users[username] = {"password": password, "quota": 5}
        return redirect(url_for("login"))
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
    quota = user_data.get("quota")

    if quota == 0:
        return "<h2>Usage limit reached.</h2><p>Please contact admin for more use.</p>"

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
                plt.text(x + w / 2, y + 1, str(y), ha='center', fontsize=20)

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

        except Exception as e:
            return f"Error processing your input: {e}"

    return render_template_string(HTML_TEMPLATE, chart=chart)

@app.route("/admin", methods=["GET", "POST"])
def admin():
    if session.get("user") != "admin":
        return redirect(url_for("login"))

    message = ""
    if request.method == "POST":
        target_user = request.form["username"]
        try:
            new_quota = int(request.form["quota"])
            if target_user in users:
                users[target_user]["quota"] = new_quota
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
    body {
      font-family: Arial, sans-serif;
      background-color: #f4f4f4;
      padding: 2rem;
      margin: 0;
    }
    .container {
      max-width: 600px;
      margin: auto;
      background: white;
      padding: 2rem;
      border-radius: 10px;
      box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }
    h2 {
      text-align: center;
      color: #333;
    }
    form {
      display: flex;
      flex-direction: column;
      gap: 1rem;
      margin-top: 1rem;
    }
    input, button {
      padding: 0.75em;
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
    p.message {
      text-align: center;
      color: green;
      font-weight: bold;
    }
    h3 {
      margin-top: 2rem;
      color: #555;
    }
    ul {
      list-style-type: none;
      padding: 0;
    }
    li {
      background: #f1f1f1;
      margin: 0.3rem 0;
      padding: 0.5rem;
      border-radius: 5px;
    }
    a {
      display: block;
      text-align: center;
      margin-top: 2rem;
      color: #007bff;
      text-decoration: none;
    }
    a:hover {
      text-decoration: underline;
    }
    @media (max-width: 600px) {
      .container {
        padding: 1rem;
      }
    }
  </style>
</head>
<body>
  <div class="container">
    <h2>Admin Panel</h2>
    <form method="POST">
      <input name="username" placeholder="Username" required>
      <input name="quota" type="number" placeholder="New quota" required>
      <button type="submit">Update Quota</button>
    </form>
    <p class="message">{{ message }}</p>
    <h3>Current User Quotas:</h3>
    <ul>
    {% for username, data in users.items() %}
      <li><strong>{{ username }}</strong>: {{ data.quota if data.quota is not none else "Unlimited" }}</li>
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
