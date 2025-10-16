# app.py - Simplified Flask app with mocked users (no DB for Vercel compatibility)
from flask import Flask, render_template, request, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# Mocked users (in-memory for prototype - not production-safe)
users = {
    'test@example.com': generate_password_hash('password123')
}

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        if email in users and check_password_hash(users[email], password):
            session['user'] = email
            return redirect(url_for('home'))
        return 'Invalid credentials', 401
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = generate_password_hash(request.form.get('password'))
        if email in users:
            return 'User exists', 409
        users[email] = password  # Add to mock dict
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/home')
def home():
    if 'user' in session:
        return f'Logged in as {session["user"]}'
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)