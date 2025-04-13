import calendar
import datetime

from flask import Flask, request, jsonify, session, render_template, redirect, url_for, flash
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

@app.template_filter('format_date')
def format_date(value, format='%m-%d'):
    """格式化日期为指定格式"""
    if not value:
        return value
    
    # 首先使用基本的英文格式
    basic_format = format.replace('年', 'Y').replace('月', 'M').replace('日', 'D')
    result = value.strftime(basic_format)
    
    # 然后替换回中文字符
    result = result.replace('Y', '年').replace('M', '月').replace('D', '日')
    return result

@app.template_filter('translate_weekday')
def translate_weekday(weekday):
    translations = {
        'Monday': '星期一',
        'Tuesday': '星期二',
        'Wednesday': '星期三',
        'Thursday': '星期四',
        'Friday': '星期五',
        'Saturday': '星期六',
        'Sunday': '星期日'
    }
    # 确保返回纯中文格式
    return translations.get(weekday, '星期一')
    return translations.get(weekday, weekday)


# Database connection
def get_db_connection():
    try:
        connection = mysql.connector.connect(
            host='localhost',
            database='liyuan_schedule',
            user='root',
            password='167163,LFPdyyzsd'
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

        # 特殊逻辑：如果用户名是"小荔"，跳转到 admin 页面
        if username == "小荔":
            return redirect(url_for('admin'))

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


@app.route('/admin', methods=['GET'])
def admin():
    if 'username' not in session:
        return jsonify({"success": False, "message": "用户未登录."}), 403

    # 检查用户名是否为"小荔"
    username = session['username']
    if username != "小荔":
        return render_template('login.html', error="非管理员账户无法进入该页面")

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    # 查询所有用户
    query = "SELECT username FROM users"
    cursor.execute(query)
    teachers = cursor.fetchall()
    cursor.close()
    connection.close()

    # 过滤掉"小荔"
    teachers = [teacher for teacher in teachers if teacher['username'] != "小荔"]

    return render_template('admin.html', teachers=teachers)

@app.route('/admin/add', methods=['POST'])
def add_teacher():
    if 'username' not in session:
        return jsonify({"success": False, "message": "用户未登录."}), 403

    # 检查用户名是否为"小荔"
    username = session['username']
    if username != "小荔":
        return render_template('login.html', error="非管理员账户无法进入该页面")

    username = request.form.get('username')
    password = request.form.get('password')

    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

    connection = get_db_connection()
    cursor = connection.cursor()
    query = "INSERT INTO users (username, password_hash) VALUES (%s, %s)"
    try:
        cursor.execute(query, (username, hashed_password))
        connection.commit()
        flash(f"Teacher '{username}' added successfully!", 'success')
    except Exception as e:
        flash(f"Error adding teacher: {str(e)}", 'error')
    finally:
        cursor.close()
        connection.close()

    return redirect(url_for('admin'))

@app.route('/admin/delete', methods=['POST'])
def delete_teacher():
    if 'username' not in session:
        return jsonify({"success": False, "message": "用户未登录."}), 403

    # 检查用户名是否为"小荔"
    username = session['username']
    if username != "小荔":
        return render_template('login.html', error="非管理员账户无法进入该页面")

    username = request.form.get('username')

    connection = get_db_connection()
    cursor = connection.cursor()
    query = "DELETE FROM users WHERE username = %s"
    try:
        cursor.execute(query, (username,))
        connection.commit()
        flash(f"Teacher '{username}' deleted successfully!", 'success')
    except Exception as e:
        flash(f"Error deleting teacher: {str(e)}", 'error')
    finally:
        cursor.close()
        connection.close()

    return redirect(url_for('admin'))

@app.route('/admin/update', methods=['POST'])
def update_teacher():
    if 'username' not in session:
        return jsonify({"success": False, "message": "用户未登录."}), 403

    # 检查用户名是否为"小荔"
    username = session['username']
    if username != "小荔":
        return render_template('login.html', error="非管理员账户无法进入该页面")

    username = request.form.get('username')
    new_password = request.form.get('new_password')

    hashed_password = bcrypt.generate_password_hash(new_password).decode('utf-8')

    connection = get_db_connection()
    cursor = connection.cursor()
    query = "UPDATE users SET password_hash = %s WHERE username = %s"
    try:
        cursor.execute(query, (hashed_password, username))
        connection.commit()
        flash(f"Password for '{username}' updated successfully!", 'success')
    except Exception as e:
        flash(f"Error updating password: {str(e)}", 'error')
    finally:
        cursor.close()
        connection.close()

    return redirect(url_for('admin'))
@app.route('/schedule_for_admin', methods=['GET'])
def schedule_for_admin():
    if 'username' not in session or session['username'] != '小荔':
        return render_template('login.html', error="Unauthorized access.")

    target_username = request.args.get('username')
    if not target_username:
        return jsonify({"success": False, "message": "No target user specified."}), 400

    connection = get_db_connection()
    if not connection:
        return render_template('schedule_for_admin.html', error="Database connection error.")

    # 获取教师基本信息
    cursor = connection.cursor(dictionary=True)
    query = "SELECT username, subject, address FROM users WHERE username = %s"
    cursor.execute(query, (target_username,))
    teacher_info = cursor.fetchone()

    # 获取课表信息
    query = "SELECT date, hour, student_name FROM schedule WHERE username = %s"
    cursor.execute(query, (target_username,))
    schedule = cursor.fetchall()
    cursor.close()
    connection.close()

    # 获取周偏移量参数
    week_param = request.args.get('week', '0')
    current_week = int(week_param)
    
    # 获取当前周的日期范围
    today = datetime.date.today()
    monday = today - datetime.timedelta(days=today.weekday())
    
    # 根据参数调整周数
    if current_week != 0:
        monday = monday + datetime.timedelta(days=7 * current_week)
    
    dates = [monday + datetime.timedelta(days=i) for i in range(7)]

    # 初始化为嵌套字典：外层键为日期，内层键为小时
    grouped_schedule = {date: {hour: None for hour in range(8, 24)} for date in dates}

    # 填充数据库中的数据
    for entry in schedule:
        date = entry['date']
        hour = entry['hour']
        student_name = entry['student_name']
        if date in grouped_schedule and hour in grouped_schedule[date]:
            grouped_schedule[date][hour] = {"student_name": student_name}

    return render_template('schedule_for_admin.html', 
                         username=target_username, 
                         schedule=grouped_schedule, 
                         current_week=current_week,
                         teacher_info=teacher_info)

@app.route('/schedule', methods=['GET'])
def get_schedule():
    if 'username' not in session:
        return jsonify({"success": False, "message": "用户未登录."}), 403

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

    # 获取周偏移量参数
    week_param = request.args.get('week', '0')
    week_offset = int(week_param)
    
    # 获取当前周的日期范围
    today = datetime.date.today()
    monday = today - datetime.timedelta(days=today.weekday())
    
    # 根据偏移量调整周数
    monday += datetime.timedelta(days=7 * week_offset)
    
    dates = [monday + datetime.timedelta(days=i) for i in range(7)]

    # 初始化为嵌套字典：外层键为日期，内层键为小时
    grouped_schedule = {date: {hour: None for hour in range(8, 24)} for date in dates}

    # 填充数据库中的数据
    for entry in schedule:
        date = entry['date']
        hour = entry['hour']
        student_name = entry['student_name']
        if date in grouped_schedule and hour in grouped_schedule[date]:
            grouped_schedule[date][hour] = {"student_name": student_name}

    return render_template('schedule.html', username=username, schedule=grouped_schedule, current_week=week_offset)

@app.route('/schedule/toggle', methods=['POST'])
def toggle_schedule():
    if 'username' not in session:
        return jsonify({"success": False, "message": "用户未登录."}), 403

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

@app.route('/schedule', methods=['POST', 'DELETE'])
def update_schedule():
    data = request.get_json()
    date = data.get('date')
    hour = data.get('hour')

    if 'username' not in session:
        return jsonify({"success": False, "message": "用户未登录."}), 403

    username = session['username']
    connection = get_db_connection()
    if not connection:
        return jsonify({"success": False, "message": "Database connection error."}), 500

    cursor = connection.cursor()
    if request.method == 'POST':
        # 添加或更新学生名字
        student_name = data.get('student_name')
        query = """
            INSERT INTO schedule (username, date, hour, student_name)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE student_name = %s
        """
        cursor.execute(query, (username, date, hour, student_name, student_name))
    elif request.method == 'DELETE':
        # 删除学生名字
        query = "DELETE FROM schedule WHERE username = %s AND date = %s AND hour = %s"
        cursor.execute(query, (username, date, hour))

    connection.commit()
    cursor.close()
    connection.close()

    return jsonify({"success": True})

def add_user_to_db(username, password):

    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

    connection = get_db_connection()
    cursor = connection.cursor()
    query = "INSERT INTO users (username, password_hash) VALUES (%s, %s)"
    try:
        cursor.execute(query, (username, hashed_password))
        connection.commit()
        flash(f"Teacher '{username}' added successfully!", 'success')
    except Exception as e:
        flash(f"Error adding teacher: {str(e)}", 'error')
    finally:
        cursor.close()
        connection.close()

    return redirect(url_for('admin'))

@app.route('/logout')
def logout():
    session.clear()  # 清除所有session数据
    return redirect(url_for('login'))

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    username = session['username']
    connection = get_db_connection()
    if not connection:
        return render_template('profile.html', error="数据库连接错误")
    
    if request.method == 'POST':
        subject = request.form.get('subject')
        address = request.form.get('address')
        
        cursor = connection.cursor()
        query = "UPDATE users SET subject = %s, address = %s WHERE username = %s"
        try:
            cursor.execute(query, (subject, address, username))
            connection.commit()
            flash("个人信息更新成功！", "success")
        except Exception as e:
            flash(f"更新失败：{str(e)}", "error")
        finally:
            cursor.close()
    
    cursor = connection.cursor(dictionary=True)
    query = "SELECT username, subject, address FROM users WHERE username = %s"
    cursor.execute(query, (username,))
    user_info = cursor.fetchone()
    cursor.close()
    connection.close()
    
    return render_template('profile.html', user_info=user_info)

@app.route('/change_password', methods=['GET', 'POST'])
def change_password():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        old_password = request.form.get('old_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        if not all([old_password, new_password, confirm_password]):
            return render_template('change_password.html', error="请填写所有字段")
        
        if new_password != confirm_password:
            return render_template('change_password.html', error="新密码和确认密码不匹配")
        
        username = session['username']
        connection = get_db_connection()
        if not connection:
            return render_template('change_password.html', error="数据库连接错误")
        
        cursor = connection.cursor(dictionary=True)
        query = "SELECT password_hash FROM users WHERE username = %s"
        cursor.execute(query, (username,))
        user = cursor.fetchone()
        
        if not user or not bcrypt.check_password_hash(user['password_hash'], old_password):
            cursor.close()
            connection.close()
            return render_template('change_password.html', error="原密码错误")
        
        hashed_password = bcrypt.generate_password_hash(new_password).decode('utf-8')
        update_query = "UPDATE users SET password_hash = %s WHERE username = %s"
        cursor.execute(update_query, (hashed_password, username))
        connection.commit()
        cursor.close()
        connection.close()
        
        return render_template('change_password.html', success="密码修改成功")
    
    return render_template('change_password.html')

def init_db():
    connection = get_db_connection()
    if not connection:
        return
    
    cursor = connection.cursor()
    try:
        # 检查列是否存在
        cursor.execute("SHOW COLUMNS FROM users LIKE 'subject'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE users ADD COLUMN subject VARCHAR(50) DEFAULT NULL")
        
        cursor.execute("SHOW COLUMNS FROM users LIKE 'address'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE users ADD COLUMN address VARCHAR(200) DEFAULT NULL")
        
        connection.commit()
    except Exception as e:
        print(f"初始化数据库时出错: {str(e)}")
    finally:
        cursor.close()
        connection.close()

# 在应用启动时初始化数据库
init_db()

if __name__ == '__main__':
    app.run(debug=True)
