from flask import Flask, render_template, request, session, redirect, url_for
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# Mock DB setup
conn = sqlite3.connect('users.db', check_same_thread=False)
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
        email = request.form['email']
        password = request.form['password']
        c.execute("SELECT password FROM users WHERE email=?", (email,))
        user = c.fetchone()
        if user and check_password_hash(user[0], password):
            session['user'] = email
            return redirect(url_for('home'))
        return 'Invalid credentials'
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = generate_password_hash(request.form['password'])
        try:
            c.execute("INSERT INTO users VALUES (?, ?)", (email, password))
            conn.commit()
            return redirect(url_for('login'))
        except:
            return 'User exists'
    return render_template('register.html')

if __name__ == '__main__':
    app.run(debug=True)