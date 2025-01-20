import calendar
import datetime

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
from flask import redirect, url_for  # 导入 redirect 和 url_for

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

        # Use redirect to go to the schedule page after successful login
        return redirect(url_for('get_schedule'))

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

    # 获取当前月份的天数和所有日期
    today = datetime.date.today()
    month_days = calendar.monthrange(today.year, today.month)[1]
    dates = [datetime.date(today.year, today.month, day) for day in range(1, month_days + 1)]

    # Group schedule by date for easier rendering
    grouped_schedule = {date: [] for date in dates}  # 初始化所有日期
    for entry in schedule:
        date = entry['date']
        if date in grouped_schedule:
            grouped_schedule[date].append({"hour": entry['hour'], "student_name": entry['student_name']})

    return render_template('schedule.html', username=username, schedule=grouped_schedule)


@app.route('/schedule/toggle', methods=['POST'])
def toggle_schedule():
    if 'username' not in session:
        return "Unauthorized", 403

    data = request.get_json()
    date = data['date']
    hour = data['hour']
    username = session['username']

    connection = get_db_connection()
    if not connection:
        return "Database connection error.", 500

    cursor = connection.cursor()
    # Check if the slot is booked
    cursor.execute("SELECT student_name FROM schedule WHERE username = %s AND date = %s AND hour = %s", (username, date, hour))
    result = cursor.fetchone()

    if result:
        # If booked, delete the entry
        cursor.execute("DELETE FROM schedule WHERE username = %s AND date = %s AND hour = %s", (username, date, hour))
    else:
        # If not booked, insert a new entry (you can modify the student_name as needed)
        cursor.execute("INSERT INTO schedule (username, date, hour, student_name) VALUES (%s, %s, %s, %s)", (username, date, hour, "Student Name"))

    connection.commit()
    cursor.close()
    connection.close()
    return "Success", 200

@app.route('/schedule', methods=['POST'])
def update_schedule():
    if 'username' not in session:
        return jsonify({"message": "Unauthorized"}), 401

    data = request.get_json()
    date = data.get('date')
    hour = data.get('hour')
    student_name = data.get('student_name')
    username = session['username']

    connection = get_db_connection()
    if not connection:
        return jsonify({"message": "Database connection error."}), 500

    cursor = connection.cursor()
    # 插入或更新课程安排
    query = """
    INSERT INTO schedule (username, date, hour, student_name)
    VALUES (%s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE student_name = %s
    """
    cursor.execute(query, (username, date, hour, student_name, student_name))
    connection.commit()
    cursor.close()
    connection.close()

    return jsonify({"success": True})


if __name__ == '__main__':
    app.run(debug=True)

