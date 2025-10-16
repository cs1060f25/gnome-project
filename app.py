from flask import Flask, render_template, request, session, redirect, url_for
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__, template_folder='templates')  # Explicit template folder
app.secret_key = 'supersecretkey'  # Secure key

# DB setup
DB_PATH = 'users.db'
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS users (email TEXT UNIQUE, password TEXT)''')
conn.commit()

@app.route('/')
def home():
    if 'user' in session:
        return f'Logged in as {session["user"]}'
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        if not email or not password:
            return 'Missing fields', 400
        c.execute("SELECT password FROM users WHERE email=?", (email,))
        user = c.fetchone()
        if user and check_password_hash(user[0], password):
            session['user'] = email
            return redirect(url_for('home'))
        return 'Invalid credentials', 401
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        if not email or not password:
            return 'Missing fields', 400
        hashed = generate_password_hash(password)
        try:
            c.execute("INSERT INTO users VALUES (?, ?)", (email, hashed))
            conn.commit()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            return 'User exists', 409
    return render_template('register.html')

if __name__ == '__main__':
    os.makedirs('templates', exist_ok=True)  # Ensure templates dir exists
    app.run(debug=True)