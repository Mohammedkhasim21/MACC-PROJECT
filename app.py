import matplotlib
matplotlib.use('Agg')  # Use the 'Agg' backend for non-interactive rendering

from flask import Flask, request, render_template_string, redirect, url_for, session
import matplotlib.pyplot as plt
import numpy as np
import io
import base64
import os
import random

app = Flask(__name__)
app.secret_key = "your_secret_key"  # Secret key for session management

# Simulated user database (for demonstration purposes)
users = {"admin": "password123"}

# HTML template for login (registration removed)
AUTH_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;500&display=swap" rel="stylesheet">
    <style>
        body {
            font-family: 'Roboto', sans-serif;
            background-color: #f4f7fc;
            margin: 0;
            padding: 0;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
        }
        .auth-container {
            background-color: white;
            padding: 40px;
            border-radius: 8px;
            box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1);
            width: 100%;
            max-width: 400px;
            text-align: center;
        }
        h2 {
            font-size: 32px;
            margin-bottom: 20px;
            color: #333;
        }
        input {
            width: 100%;
            padding: 12px;
            margin: 10px 0;
            border: 1px solid #ddd;
            border-radius: 5px;
            font-size: 16px;
        }
        button {
            width: 100%;
            padding: 12px;
            border: none;
            border-radius: 5px;
            background-color: #007BFF;
            color: white;
            font-size: 18px;
            cursor: pointer;
            transition: background-color 0.3s;
        }
        button:hover {
            background-color: #0056b3;
        }
        p {
            font-size: 16px;
            color: #888;
        }
        .message {
            font-size: 14px;
            color: #e74c3c;
            margin-top: 10px;
        }
    </style>
</head>
<body>
    <div class="auth-container">
        <h2>{{ title }}</h2>
        <form method="POST">
            <input type="text" name="username" placeholder="Username" required><br>
            <input type="password" name="password" placeholder="Password" required><br>
            <button type="submit">Submit</button>
        </form>
        <p class="message">{{ message }}</p>
    </div>
</body>
</html>
"""

# HTML template for the input form and the chart
HTML_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>Marginal Abatement Cost Curve (MACC)</title>
    <style>
        body {
            font-family: 'Roboto', sans-serif;
            text-align: center;
            background-color: #f4f7fc;
            margin: 0;
            padding: 20px;
        }
        form {
            display: inline-block;
            margin-top: 20px;
            text-align: left;
        }
        input, button {
            display: block;
            margin-top: 15px;
            padding: 12px;
            width: 550px;
            font-size: 18px;
            border-radius: 5px;
            border: 1px solid #ddd;
        }
        button {
            background-color: #007BFF;
            color: white;
            border: none;
            cursor: pointer;
            transition: background-color 0.3s;
        }
        button:hover {
            background-color: #0056b3;
        }
        .logout-button {
            position: absolute;
            top: 20px;
            right: 20px;
            background-color: #ff5c5c;
            color: white;
            border: none;
            padding: 12px 25px;
            cursor: pointer;
            font-size: 18px;
            width:100px;
        }
        .logout-button:hover {
            background-color: #e04e4e;
        }
        img {
            margin-top: 20px;
            max-width: 100%;
            height: auto;
        }
        h1 {
            font-size: 36px;
            color: #333;
        }
        .chart-labels {
            font-size: 20px;
        }
        .chart-title {
            font-size: 24px;
            font-weight: bold;
        }
        .chart-axis-labels {
            font-size: 20px;
        }
    </style>
</head>
<body>
    <h1>Marginal Abatement Cost Curve (MACC)</h1>

    <form action="{{ url_for('logout') }}" method="POST">
        <button type="submit" class="logout-button">Logout</button>
    </form>

    <form method="POST">
        <input type="text" name="project_name" placeholder="Enter Organisation Name" required><br>
        <input type="text" name="categories" placeholder="Enter Interventions/Projects (comma-separated)" required><br>
        <input type="text" name="values" placeholder="Enter MACC Value In USD/Ton CO2 (comma-separated)" required><br>
        <input type="text" name="widths" placeholder="Enter CO2 Abatement Value (Million Ton) (comma-separated)" required><br>
        <input type="number" name="line_value" placeholder=" Enter Internal carbon price in USD/Ton CO2 (optional)"><br>
        <button type="submit">Generate Chart</button>
    </form>

    {% if chart %}
    <h2 class="chart-title">Generated MACC Chart:</h2>
    <img src="data:image/png;base64,{{ chart }}" alt="MACC Chart">
    {% endif %}
</body>
</html>
"""

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        if username in users and users[username] == password:
            session["user"] = username
            return redirect(url_for("index"))
        return render_template_string(AUTH_TEMPLATE, title="Login", message="Invalid credentials.")
    return render_template_string(AUTH_TEMPLATE, title="Login", message="")

@app.route("/logout", methods=["POST"])
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))

@app.route("/", methods=["GET", "POST"])
def index():
    if "user" not in session:
        return redirect(url_for("login"))
    
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
                return "Error: The number of Interventions/Projects, values, and widths must be the same."

            total_abatement = sum(widths)
            x_positions = np.cumsum([0] + widths[:-1])
            colors = ["#" + ''.join(random.choices('0123456789ABCDEF', k=6)) for _ in range(len(categories))]

            plt.figure(figsize=(20, 25))
            plt.bar(x_positions, values, width=widths, color=colors, edgecolor='black', align='edge')

            for x, y, w in zip(x_positions, values, widths):
                plt.text(x + w / 2, y + 1, str(y), ha='center',rotation=90, fontsize=20)

            plt.xticks(x_positions + np.array(widths) / 2, categories, ha="center",rotation=90,  fontsize=20)
            plt.title(f"Marginal Abatement Cost Curve (MACC) - {project_name}", fontsize=24)
            plt.xlabel("CO2 Abatement, Million Tonne", fontsize=20)
            plt.ylabel("MACC Value In USD/Ton CO2", fontsize=20)

            for x, width in zip(x_positions, widths):
                plt.text(x + width / 2, -1.5, f"{int(width)}", ha="center", fontsize=20, color="black")

            if line_value is not None:
                plt.axhline(y=line_value, color='red', linestyle='--', linewidth=2)
                plt.text(x_positions[-1] + widths[-1] / 2, line_value + 1, f"Internal carbon price {line_value}",
                         color='black', fontsize=20, ha='center')

            plt.tick_params(axis='y', labelsize=20)
            plt.subplots_adjust(bottom=0.3, right=0.95)

            last_x = x_positions[-1]
            last_width = widths[-1]
            plt.text(last_x + last_width / 2, -5, f"Total: {total_abatement:.1f}",
                     ha='center', fontsize=20, color="black")

            buf = io.BytesIO()
            plt.savefig(buf, format="png")
            buf.seek(0)
            chart = base64.b64encode(buf.getvalue()).decode("utf-8")
            buf.close()
            plt.close()
        except Exception as e:
            return f"Error processing your input: {e}"

    return render_template_string(HTML_TEMPLATE, chart=chart)

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
