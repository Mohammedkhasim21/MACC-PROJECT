# from flask import Flask, render_template_string, request, redirect, url_for, session, send_file
# from matplotlib.figure import Figure
# import io
# import sqlite3
# import os

# app = Flask(__name__)
# app.secret_key = 'your_secret_key'

# DATABASE = 'users.db'
# ADMIN_USERNAME = 'admin@example.com'
# ADMIN_PASSWORD = 'adminpass'

# def init_db():
#     conn = sqlite3.connect(DATABASE)
#     c = conn.cursor()
#     c.execute('''
#         CREATE TABLE IF NOT EXISTS users (
#             username TEXT PRIMARY KEY,
#             password TEXT NOT NULL,
#             quota INTEGER NOT NULL DEFAULT 3
#         )
#     ''')
#     conn.commit()
#     conn.close()

# init_db()

# AUTH_TEMPLATE = """
# <!doctype html>
# <title>{{ title }}</title>
# <style>
#   body {
#     font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
#     background-color: #f0f2f5;
#     display: flex;
#     justify-content: center;
#     align-items: center;
#     height: 100vh;
#     margin: 0;
#   }
#   .card {
#     background: white;
#     padding: 2.5rem;
#     border-radius: 12px;
#     box-shadow: 0 6px 16px rgba(0, 0, 0, 0.1);
#     width: 100%;
#     max-width: 400px;
#   }
#   h2 {
#     text-align: center;
#     color: #333;
#     margin-bottom: 1.5rem;
#   }
#   input, button {
#     width: 100%;
#     padding: 0.75rem;
#     margin-bottom: 1rem;
#     font-size: 1em;
#     border: 1px solid #ccc;
#     border-radius: 6px;
#   }
#   button {
#     background-color: #007bff;
#     color: white;
#     border: none;
#     font-weight: bold;
#     transition: background 0.3s ease;
#   }
#   button:hover {
#     background-color: #0056b3;
#   }
#   p {
#     text-align: center;
#     font-size: 0.95em;
#   }
#   a {
#     color: #007bff;
#     text-decoration: none;
#   }
#   a:hover {
#     text-decoration: underline;
#   }
# </style>
# <div class="card">
#   <h2>{{ title }}</h2>
#   <form method="POST">
#     <input type="text" name="username" placeholder="Email" required>
#     <input type="password" name="password" placeholder="Password" required>
#     <button type="submit">{{ title }}</button>
#   </form>
#   <p>{{ message }}</p>
#   {% if title == 'Login' %}
#     <p>Don't have an account? <a href="{{ url_for('register') }}">Register</a></p>
#   {% else %}
#     <p>Already have an account? <a href="{{ url_for('login') }}">Login</a></p>
#   {% endif %}
# </div>
# """

# HTML_TEMPLATE = """
# <!doctype html>
# <title>MACC Chart Generator</title>
# <style>
#   body {
#     font-family: 'Segoe UI', Tahoma, sans-serif;
#     background-color: #f8f9fa;
#     margin: 0;
#     padding: 2rem;
#     min-height: 100vh;
#     display: flex;
#     flex-direction: column;
#   }
#   .container {
#     background: white;
#     padding: 2rem;
#     border-radius: 10px;
#     max-width: 800px;
#     margin: auto;
#     box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
#   }
#   h2, h3 {
#     text-align: center;
#     color: #343a40;
#   }
#   form {
#     display: flex;
#     flex-direction: column;
#     gap: 1rem;
#   }
#   input, button {
#     padding: 0.75rem;
#     font-size: 1rem;
#     border-radius: 5px;
#     border: 1px solid #ced4da;
#   }
#   button {
#     background-color: #28a745;
#     color: white;
#     font-weight: bold;
#     border: none;
#     transition: background 0.3s ease;
#   }
#   button:hover {
#     background-color: #218838;
#   }
#   img {
#     display: block;
#     margin: 2rem auto;
#     max-width: 100%;
#     border-radius: 8px;
#     border: 1px solid #dee2e6;
#   }
#   .logout-button {
#     background-color: #dc3545;
#     margin-top: 2rem;
#     align-self: center;
#   }
#   .admin-link, .footer {
#     text-align: center;
#     margin-top: 1rem;
#   }
#   @media (max-width: 768px) {
#     .container {
#       padding: 1rem;
#     }
#   }
# </style>
# <div class="container">
#   <h2>MACC Chart Generator</h2>
#   <p>Logged in as: {{ username }} | Remaining quota: {{ quota }}</p>
#   <form method="POST">
#     <input type="text" name="measures" placeholder="Enter measure names (comma-separated)" required>
#     <input type="text" name="costs" placeholder="Enter costs (comma-separated)" required>
#     <input type="text" name="abatements" placeholder="Enter abatement values (comma-separated)" required>
#     <button type="submit">Generate Chart</button>
#   </form>
#   {% if image %}
#     <img src="{{ url_for('macc_chart') }}" alt="MACC Chart">
#   {% endif %}
#   <form method="POST" action="{{ url_for('logout') }}">
#     <button class="logout-button" type="submit">Logout</button>
#   </form>
#   {% if is_admin %}
#     <div class="admin-link"><a href="{{ url_for('admin') }}">Go to Admin Panel</a></div>
#   {% endif %}
# </div>
# """

# LIMIT_TEMPLATE = """
# <!doctype html>
# <title>Quota Reached</title>
# <style>
#   body {
#     font-family: 'Segoe UI', Tahoma, sans-serif;
#     background-color: #fff3cd;
#     display: flex;
#     justify-content: center;
#     align-items: center;
#     height: 100vh;
#   }
#   .card {
#     background-color: #fff;
#     border: 1px solid #ffeeba;
#     padding: 2rem;
#     border-radius: 10px;
#     box-shadow: 0 4px 12px rgba(0,0,0,0.1);
#     max-width: 500px;
#     text-align: center;
#   }
#   h2 {
#     color: #856404;
#   }
#   p {
#     color: #856404;
#   }
# </style>
# <div class="card">
#   <h2>Usage Limit Reached</h2>
#   <p>You have used up your chart generation quota. Please contact support or the admin to request more.</p>
# </div>
# """

# ADMIN_TEMPLATE = """
# <!doctype html>
# <title>Admin Panel</title>
# <style>
#   body {
#     font-family: 'Segoe UI', Tahoma, sans-serif;
#     background-color: #f0f2f5;
#     padding: 2rem;
#   }
#   .container {
#     background: white;
#     padding: 2rem;
#     border-radius: 10px;
#     max-width: 600px;
#     margin: auto;
#     box-shadow: 0 4px 12px rgba(0,0,0,0.1);
#   }
#   h2 {
#     text-align: center;
#     color: #343a40;
#   }
#   table {
#     width: 100%;
#     margin-top: 1rem;
#     border-collapse: collapse;
#   }
#   th, td {
#     border: 1px solid #dee2e6;
#     padding: 0.75rem;
#     text-align: center;
#   }
#   form {
#     display: inline;
#   }
#   input {
#     width: 60px;
#     padding: 0.4rem;
#     border: 1px solid #ccc;
#     border-radius: 4px;
#   }
#   button {
#     padding: 0.4rem 0.75rem;
#     background-color: #007bff;
#     color: white;
#     border: none;
#     border-radius: 4px;
#     margin-left: 0.5rem;
#   }
# </style>
# <div class="container">
#   <h2>Admin Panel</h2>
#   <table>
#     <tr><th>User</th><th>Quota</th><th>Update</th></tr>
#     {% for user in users %}
#       <tr>
#         <td>{{ user[0] }}</td>
#         <td>{{ user[1] }}</td>
#         <td>
#           <form method="POST">
#             <input type="hidden" name="username" value="{{ user[0] }}">
#             <input type="number" name="quota" min="0" value="{{ user[1] }}">
#             <button type="submit">Set</button>
#           </form>
#         </td>
#       </tr>
#     {% endfor %}
#   </table>
# </div>
# """

# @app.route('/register', methods=['GET', 'POST'])
# def register():
#     message = ''
#     if request.method == 'POST':
#         username = request.form['username']
#         password = request.form['password']
#         if '@' not in username or '.' not in username:
#             message = 'Please enter a valid email address.'
#         else:
#             conn = sqlite3.connect(DATABASE)
#             c = conn.cursor()
#             try:
#                 c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
#                 conn.commit()
#                 return redirect(url_for('login'))
#             except sqlite3.IntegrityError:
#                 message = 'User already exists.'
#             finally:
#                 conn.close()
#     return render_template_string(AUTH_TEMPLATE, title="Register", message=message)

# @app.route('/', methods=['GET', 'POST'])
# @app.route('/login', methods=['GET', 'POST'])
# def login():
#     message = ''
#     if request.method == 'POST':
#         username = request.form['username']
#         password = request.form['password']
#         conn = sqlite3.connect(DATABASE)
#         c = conn.cursor()
#         c.execute("SELECT password FROM users WHERE username = ?", (username,))
#         user = c.fetchone()
#         conn.close()
#         if user and user[0] == password:
#             session['username'] = username
#             return redirect(url_for('index'))
#         else:
#             message = 'Invalid username or password.'
#     return render_template_string(AUTH_TEMPLATE, title="Login", message=message)

# @app.route('/logout', methods=['POST'])
# def logout():
#     session.pop('username', None)
#     return redirect(url_for('login'))

# @app.route('/admin', methods=['GET', 'POST'])
# def admin():
#     if session.get('username') != ADMIN_USERNAME:
#         return redirect(url_for('login'))
#     conn = sqlite3.connect(DATABASE)
#     c = conn.cursor()
#     if request.method == 'POST':
#         username = request.form['username']
#         quota = int(request.form['quota'])
#         c.execute("UPDATE users SET quota = ? WHERE username = ?", (quota, username))
#         conn.commit()
#     c.execute("SELECT username, quota FROM users")
#     users = c.fetchall()
#     conn.close()
#     return render_template_string(ADMIN_TEMPLATE, users=users)

# @app.route('/index', methods=['GET', 'POST'])
# def index():
#     username = session.get('username')
#     if not username:
#         return redirect(url_for('login'))
#     conn = sqlite3.connect(DATABASE)
#     c = conn.cursor()
#     c.execute("SELECT quota FROM users WHERE username = ?", (username,))
#     row = c.fetchone()
#     if not row or row[0] <= 0:
#         return render_template_string(LIMIT_TEMPLATE)
#     quota = row[0]
#     image = False
#     if request.method == 'POST':
#         try:
#             measures = request.form['measures'].split(',')
#             costs = list(map(float, request.form['costs'].split(',')))
#             abatements = list(map(float, request.form['abatements'].split(',')))
#             generate_chart(measures, costs, abatements)
#             c.execute("UPDATE users SET quota = quota - 1 WHERE username = ?", (username,))
#             conn.commit()
#             image = True
#         except:
#             image = False
#     conn.close()
#     return render_template_string(HTML_TEMPLATE, username=username, quota=quota, image=image, is_admin=(username == ADMIN_USERNAME))

# @app.route('/macc_chart')
# def macc_chart():
#     return send_file("macc_chart.png", mimetype='image/png')

# def generate_chart(measures, costs, abatements):
#     fig = Figure(figsize=(10, 5))
#     ax = fig.subplots()
#     data = sorted(zip(measures, costs, abatements), key=lambda x: x[1]/x[2])
#     cum_width = 0
#     for label, cost, abatement in data:
#         ax.bar(cum_width, cost, width=abatement, align='edge', label=label)
#         cum_width += abatement
#     ax.set_xlabel("Abatement (MtCO₂e)")
#     ax.set_ylabel("Cost ($/tCO₂e)")
#     ax.set_title("Marginal Abatement Cost Curve")
#     fig.tight_layout()
#     fig.savefig("macc_chart.png")

# if __name__ == '__main__':
#     app.run(debug=True)


# # Run the app
# if __name__ == "__main__":
#     port = int(os.environ.get("PORT", 5000))
#     app.run(host="0.0.0.0", port=port, debug=True)