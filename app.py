import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend

from flask import Flask, request, render_template_string, redirect, url_for, session
import matplotlib.pyplot as plt
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

AUTH_TEMPLATE = """
<!doctype html>
<title>{{ title }}</title>
<h2>{{ title }}</h2>
<form method="POST">
  <input name="username" placeholder="Username" required><br><br>
  <input name="password" type="password" placeholder="Password" required><br><br>
  <button type="submit">{{ title }}</button>
</form>
<p style="color:red;">{{ message }}</p>
{% if title == "Login" %}
<p>Don't have an account? <a href="{{ url_for('register') }}">Register here</a></p>
{% else %}
<p>Already have an account? <a href="{{ url_for('login') }}">Login here</a></p>
{% endif %}
"""

HTML_TEMPLATE = """
<!doctype html>
<title>MACC Chart Generator</title>
<h2>MACC Chart Generator</h2>
<form method="POST">
  <input name="project_name" placeholder="Project Name" required><br><br>
  <input name="categories" placeholder="Categories (comma-separated)" required><br><br>
  <input name="values" placeholder="Values (comma-separated)" required><br><br>
  <input name="widths" placeholder="Widths (comma-separated)" required><br><br>
  <input name="line_value" placeholder="Optional Line Value (e.g. internal carbon price)"><br><br>
  <button type="submit">Generate Chart</button>
</form>

{% if chart %}
<h3>Generated Chart:</h3>
<img src="data:image/png;base64,{{ chart }}" alt="MACC Chart">
{% endif %}

<form method="POST" action="{{ url_for('logout') }}">
  <button type="submit">Logout</button>
</form>

{% if session['user'] == 'admin' %}
<p><a href="{{ url_for('admin') }}">Go to Admin Panel</a></p>
{% endif %}
"""

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
        users[username] = {"password": password, "quota": 5}  # Default quota
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
            plt.xlabel("CO2 Abatement, Million tonne", fontsize=20)
            plt.ylabel("Internal Carbon Pricing in USD/ton CO2", fontsize=20)

            for i, (x, width) in enumerate(zip(x_positions, widths)):
                plt.text(x + width / 2, -1.5, f"{int(width)}", ha="center", fontsize=20, color="black")

            if line_value is not None:
                plt.axhline(y=line_value, color='red', linestyle='--', linewidth=2)
                plt.text(x_positions[-1] + widths[-1] / 2, line_value + 1, f"Internal carbon price {line_value}",
                         color='red', fontsize=20, ha='center')

            plt.tick_params(axis='y', labelsize=20)
            plt.subplots_adjust(bottom=0.3, right=0.95)

            last_x = x_positions[-1]
            last_width = widths[-1]
            last_value = values[-1]
            total_text = f"Total:\n{total_abatement:.2f}"
            plt.text(last_x + last_width + 2, last_value / 2, total_text,
                     rotation=90, fontsize=20, va='center', color="black")

            buf = io.BytesIO()
            plt.savefig(buf, format="png")
            buf.seek(0)
            chart = base64.b64encode(buf.getvalue()).decode("utf-8")
            buf.close()
            plt.close()

            # Decrease quota
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
    <h2>Admin Panel</h2>
    <form method="POST">
        <input name="username" placeholder="Username" required>
        <input name="quota" type="number" placeholder="New quota" required>
        <button type="submit">Update Quota</button>
    </form>
    <p>{{ message }}</p>
    <h3>Current User Quotas:</h3>
    <ul>
    {% for username, data in users.items() %}
        <li>{{ username }}: {{ data.quota if data.quota is not none else "Unlimited" }}</li>
    {% endfor %}
    </ul>
    """, users=users, message=message)

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
