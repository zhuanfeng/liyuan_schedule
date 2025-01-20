from flask import Flask, request, jsonify, session, render_template, redirect, url_for
from flask_bcrypt import Bcrypt
import mysql.connector
from mysql.connector import Error
import secrets

app = Flask(__name__)

# Configurations
app.config['SECRET_KEY'] = secrets.token_hex(16)
bcrypt = Bcrypt(app)

# Routes
@app.route('/')
def index():
    return redirect(url_for('login'))

# Database connection
def get_db_connection():
    try:
        connection = mysql.connector.connect(
            host='localhost',
            database='liyuan_schedule',
            user='root',
            password='1234'
        )
        return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

# Routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')

    data = request.form
    username = data.get('username')
    password = data.get('password')

    connection = get_db_connection()
    if not connection:
        return jsonify({"message": "Database connection error."}), 500

    cursor = connection.cursor(dictionary=True)
    query = "SELECT password_hash FROM users WHERE username = %s"
    cursor.execute(query, (username,))
    user = cursor.fetchone()
    cursor.close()
    connection.close()

    if user and bcrypt.check_password_hash(user['password_hash'], password):
        session['username'] = username

        # Fetch schedule for the logged-in user
        connection = get_db_connection()
        if not connection:
            return jsonify({"message": "Database connection error."}), 500

        cursor = connection.cursor(dictionary=True)
        query = "SELECT date, hour, student_name FROM schedule WHERE username = %s"
        cursor.execute(query, (username,))
        schedule = cursor.fetchall()
        cursor.close()
        connection.close()

        # Group schedule by date for easier rendering
        grouped_schedule = {}
        for entry in schedule:
            date = entry['date']
            if date not in grouped_schedule:
                grouped_schedule[date] = []
            grouped_schedule[date].append({"hour": entry['hour'], "student_name": entry['student_name']})

        return render_template('schedule.html', username=username, schedule=grouped_schedule)

    return render_template('login.html', error="Invalid username or password")


@app.route('/schedule', methods=['GET'])
def get_schedule():
    if 'username' not in session:
        return render_template('login.html', error="Please log in first.")

    username = session['username']
    connection = get_db_connection()
    if not connection:
        return render_template('schedule.html', error="Database connection error.")

    cursor = connection.cursor(dictionary=True)
    query = "SELECT date, hour, student_name FROM schedule WHERE username = %s"
    cursor.execute(query, (username,))
    schedule = cursor.fetchall()
    cursor.close()
    connection.close()

    # Group schedule by date for easier rendering
    grouped_schedule = {}
    for entry in schedule:
        date = entry['date']
        if date not in grouped_schedule:
            grouped_schedule[date] = []
        grouped_schedule[date].append({"hour": entry['hour'], "student_name": entry['student_name']})

    return render_template('schedule.html', schedule=grouped_schedule, username=username)

@app.route('/schedule', methods=['POST'])
def update_schedule():
    if 'username' not in session:
        return render_template('login.html', error="Please log in first.")

    data = request.form
    username = session['username']
    date = data.get('date')  # Format: YYYY-MM-DD
    hour = data.get('hour')  # 0-23
    student_name = data.get('student_name')

    connection = get_db_connection()
    if not connection:
        return render_template('schedule.html', error="Database connection error.")

    cursor = connection.cursor()

    # Check if entry exists
    query_check = "SELECT id FROM schedule WHERE username = %s AND date = %s AND hour = %s"
    cursor.execute(query_check, (username, date, hour))
    entry = cursor.fetchone()

    if student_name:  # Add or update schedule
        if entry:
            query_update = "UPDATE schedule SET student_name = %s WHERE id = %s"
            cursor.execute(query_update, (student_name, entry[0]))
        else:
            query_insert = "INSERT INTO schedule (username, date, hour, student_name) VALUES (%s, %s, %s, %s)"
            cursor.execute(query_insert, (username, date, hour, student_name))
    else:  # Remove schedule
        if entry:
            query_delete = "DELETE FROM schedule WHERE id = %s"
            cursor.execute(query_delete, (entry[0],))

    connection.commit()
    cursor.close()
    connection.close()

    return get_schedule()

if __name__ == '__main__':
    app.run(debug=True)

