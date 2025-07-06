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

        # 跳转到课表页面
        return redirect(url_for('update_schedule'))

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

    # 获取查询参数
    year = request.args.get('year')
    month = request.args.get('month')
    week = request.args.get('week')
    week_offset = request.args.get('week_offset', '0')
    current_week_offset = int(week_offset)
    
    # 计算日期范围
    today = datetime.date.today()
    
    if year and month:
        year = int(year)
        month = int(month)
        # 获取该月第一天
        first_day = datetime.date(year, month, 1)
        # 计算该月第一个周一的日期
        if first_day.weekday() != 0:
            first_monday = first_day - datetime.timedelta(days=first_day.weekday())
        else:
            first_monday = first_day
            
        if week:
            # 如果指定了周，则计算该月该周的日期范围
            week = int(week)
            # 计算指定周的周一
            monday = first_monday + datetime.timedelta(weeks=(week-1))
            
            # 应用周偏移量，使上一周/下一周功能正常工作
            if week_offset:
                offset = int(week_offset)
                # 只有在非零偏移时才应用
                if offset != 0:
                    monday = monday + datetime.timedelta(weeks=offset)
                
            dates = [monday + datetime.timedelta(days=i) for i in range(7)]
            
            # 初始化课表数据
            grouped_schedule = {date: {hour: None for hour in range(8, 24)} for date in dates}
            
            # 填充数据库中的数据
            for entry in schedule:
                date = entry['date']
                hour = entry['hour']
                student_name = entry['student_name']
                if date in grouped_schedule and hour in grouped_schedule[date]:
                    grouped_schedule[date][hour] = {"student_name": student_name}
                    
            # 计算当前显示的周数（相对于今天）
            current_week = (monday - (today - datetime.timedelta(days=today.weekday()))).days // 7
            
            return render_template('schedule_for_admin.html', 
                                 username=target_username, 
                                 schedule=grouped_schedule, 
                                 current_week=current_week,
                                 teacher_info=teacher_info,
                                 selected_year=year,
                                 selected_month=month,
                                 selected_week=week,
                                 week_offset=int(week_offset),
                                 all_weeks_schedule={})  # 添加空的all_weeks_schedule
        else:
            # 如果没有指定周，显示该月所有周的数据
            all_weeks_schedule = {}
            
            # 计算该月有多少周（最多5周）
            # 获取该月的最后一天
            last_day = datetime.date(year, month + 1 if month < 12 else 1, 1) - datetime.timedelta(days=1)
            # 计算该月实际的周数
            total_weeks = min(5, (last_day.day + first_monday.weekday() - 1) // 7 + 1)
            
            # 初始化所有周的数据（只包括实际存在的周）
            for week_num in range(1, total_weeks + 1):
                week_monday = first_monday + datetime.timedelta(weeks=(week_num-1))
                week_dates = [week_monday + datetime.timedelta(days=i) for i in range(7)]
                
                # 初始化该周的课表数据
                week_schedule = {date: {hour: None for hour in range(8, 24)} for date in week_dates}
                
                # 填充数据库中的数据
                for entry in schedule:
                    date = entry['date']
                    hour = entry['hour']
                    student_name = entry['student_name']
                    if date in week_schedule and hour in week_schedule[date]:
                        week_schedule[date][hour] = {"student_name": student_name}
                
                all_weeks_schedule[week_num] = week_schedule
            
            return render_template('schedule_for_admin.html', 
                                 username=target_username, 
                                 schedule={},  # 空的schedule，因为我们使用all_weeks_schedule
                                 all_weeks_schedule=all_weeks_schedule,
                                 current_week=0,
                                 teacher_info=teacher_info,
                                 selected_year=year,
                                 selected_month=month,
                                 selected_week=None,
                                 week_offset=0,
                                 total_weeks=total_weeks)
    else:
        # 如果没有指定年月，使用当前日期
        # 应用周偏移量
        monday = today - datetime.timedelta(days=today.weekday()) + datetime.timedelta(weeks=current_week_offset)
        dates = [monday + datetime.timedelta(days=i) for i in range(7)]
        
        # 初始化课表数据
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
                             current_week=current_week_offset,
                             teacher_info=teacher_info,
                             selected_year=today.year,
                             selected_month=today.month,
                             selected_week=None,
                             week_offset=current_week_offset,
                             all_weeks_schedule={})

@app.route('/schedule', methods=['GET', 'POST'])
def update_schedule():
    if 'username' not in session:
        return jsonify({"success": False, "message": "用户未登录."}), 403

    if request.method == 'POST':
        data = request.get_json()
        date = data.get('date')
        hour = int(data.get('hour'))
        student_name = data.get('student_name')
        username = session['username']

        connection = get_db_connection()
        if not connection:
            return jsonify({"success": False, "message": "数据库连接错误."}), 500

        cursor = connection.cursor()
        try:
            if student_name:
                query = """
                    INSERT INTO schedule (username, date, hour, student_name)
                    VALUES (%s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE student_name = %s
                """
                cursor.execute(query, (username, date, hour, student_name, student_name))
            else:
                query = "DELETE FROM schedule WHERE username = %s AND date = %s AND hour = %s"
                cursor.execute(query, (username, date, hour))
            
            connection.commit()
            return jsonify({"success": True})
        except Exception as e:
            print(f"Error saving schedule: {str(e)}")
            return jsonify({"success": False, "message": str(e)}), 500
        finally:
            cursor.close()
            connection.close()

    # GET 请求处理
    username = session['username']
    connection = get_db_connection()
    if not connection:
        return render_template('schedule.html', error="Database connection error.")

    # 获取查询参数
    year = request.args.get('year')
    month = request.args.get('month')
    week = request.args.get('week')
    week_offset = request.args.get('week_offset', '0')  # 新增：周偏移量参数
    
    # 获取教师基本信息
    cursor = connection.cursor(dictionary=True)
    query = "SELECT username, subject, address FROM users WHERE username = %s"
    cursor.execute(query, (username,))
    teacher_info = cursor.fetchone()

    # 获取课表信息
    query = "SELECT date, hour, student_name FROM schedule WHERE username = %s"
    cursor.execute(query, (username,))
    schedule = cursor.fetchall()
    cursor.close()
    connection.close()

    # 计算日期范围
    today = datetime.date.today()
    
    if year and month:
        year = int(year)
        month = int(month)
        # 获取该月第一天
        first_day = datetime.date(year, month, 1)
        # 计算该月第一个周一的日期
        if first_day.weekday() != 0:
            first_monday = first_day - datetime.timedelta(days=first_day.weekday())
        else:
            first_monday = first_day
            
        if week:
            # 如果指定了周，则计算该月该周的日期范围
            week = int(week)
            # 计算指定周的周一
            monday = first_monday + datetime.timedelta(weeks=(week-1))
            
            # 应用周偏移量，使上一周/下一周功能正常工作
            if week_offset:
                offset = int(week_offset)
                # 只有在非零偏移时才应用
                if offset != 0:
                    monday = monday + datetime.timedelta(weeks=offset)
                
            dates = [monday + datetime.timedelta(days=i) for i in range(7)]
            
            # 初始化课表数据
            grouped_schedule = {date: {hour: None for hour in range(8, 24)} for date in dates}
            
            # 填充数据库中的数据
            for entry in schedule:
                date = entry['date']
                hour = entry['hour']
                student_name = entry['student_name']
                if date in grouped_schedule and hour in grouped_schedule[date]:
                    grouped_schedule[date][hour] = {"student_name": student_name}
                    
            # 计算当前显示的周数（相对于今天）
            current_week = (monday - (today - datetime.timedelta(days=today.weekday()))).days // 7
            
            return render_template('schedule.html', 
                                username=username, 
                                schedule=grouped_schedule, 
                                current_week=current_week,
                                teacher_info=teacher_info,
                                selected_year=year,
                                selected_month=month,
                                selected_week=week,
                                week_offset=int(week_offset),  # 传递周偏移量到模板
                                all_weeks_schedule={})  # 添加空的all_weeks_schedule
        else:
            # 如果没有指定周，显示该月所有周的数据
            all_weeks_schedule = {}
            
            # 计算该月有多少周（最多5周）
            # 获取该月的最后一天
            last_day = datetime.date(year, month + 1 if month < 12 else 1, 1) - datetime.timedelta(days=1)
            # 计算该月实际的周数
            total_weeks = min(5, (last_day.day + first_monday.weekday() - 1) // 7 + 1)
            
            # 初始化所有周的数据（只包括实际存在的周）
            for week_num in range(1, total_weeks + 1):
                week_monday = first_monday + datetime.timedelta(weeks=(week_num-1))
                week_dates = [week_monday + datetime.timedelta(days=i) for i in range(7)]
                
                # 初始化该周的课表数据
                week_schedule = {date: {hour: None for hour in range(8, 24)} for date in week_dates}
                
                # 填充数据库中的数据
                for entry in schedule:
                    date = entry['date']
                    hour = entry['hour']
                    student_name = entry['student_name']
                    if date in week_schedule and hour in week_schedule[date]:
                        week_schedule[date][hour] = {"student_name": student_name}
                
                all_weeks_schedule[week_num] = week_schedule
            
            return render_template('schedule.html', 
                                username=username, 
                                schedule={},  # 空的schedule，因为我们使用all_weeks_schedule
                                all_weeks_schedule=all_weeks_schedule,
                                current_week=0,
                                teacher_info=teacher_info,
                                selected_year=year,
                                selected_month=month,
                                selected_week=None,
                                week_offset=0,  # 传递周偏移量到模板
                                total_weeks=total_weeks)  # 添加实际周数
    else:
        # 如果没有指定年月，使用当前日期
        # 应用周偏移量
        current_week_offset = int(week_offset)
        monday = today - datetime.timedelta(days=today.weekday()) + datetime.timedelta(weeks=current_week_offset)
        dates = [monday + datetime.timedelta(days=i) for i in range(7)]
        
        # 初始化课表数据
        grouped_schedule = {date: {hour: None for hour in range(8, 24)} for date in dates}
        
        # 填充数据库中的数据
        for entry in schedule:
            date = entry['date']
            hour = entry['hour']
            student_name = entry['student_name']
            if date in grouped_schedule and hour in grouped_schedule[date]:
                grouped_schedule[date][hour] = {"student_name": student_name}
        
        return render_template('schedule.html', 
                            username=username, 
                            schedule=grouped_schedule, 
                            current_week=current_week_offset,
                            teacher_info=teacher_info,
                            selected_year=today.year,
                            selected_month=today.month,
                            selected_week=None,
                            week_offset=current_week_offset,  # 传递周偏移量到模板
                            all_weeks_schedule={})  # 添加空的all_weeks_schedule

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

@app.route('/campus_schedule')
def campus_schedule():
    # 模拟数据，后续可对接数据库
    title = "暑假崇达数理化课程表"
    date_range = "2025.7.13-7.31"
    days = [
        "7/13 星期日", "7/14 星期一", "7/15 星期二", "7/16 星期三", "7/17 星期四", "7/18 星期五", "7/19 星期六",
        "7/20 星期日", "7/21 星期一", "7/22 星期二", "7/23 星期三", "7/24 星期四", "7/25 星期五", "7/26 星期六",
        "7/27 星期日", "7/28 星期一", "7/29 星期二", "7/30 星期三", "7/31 星期四"
    ]
    time_slots = [
        "8:00-9:00", "9:00-10:00", "10:00-11:00", "11:00-12:00",
        "14:00-15:00", "15:00-16:00", "16:00-17:00", "17:00-18:00",
        "19:00-20:00", "20:00-21:00"
    ]
    # 课程安排（示例，实际可从数据库获取）
    schedule = [
        # 每个时段一行，每行是每天的课程类型
        ["化学", "化学", "化学", "化学", "化学", "化学", "化学", "化学", "化学", "化学", "化学", "化学", "化学", "化学", "化学", "化学", "化学", "化学", "化学"],
        ["化学", "化学", "化学", "化学", "化学", "化学", "化学", "化学", "化学", "化学", "化学", "化学", "化学", "化学", "化学", "化学", "化学", "化学", "化学"],
        ["", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""],
        ["", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""],
        ["", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""],
        ["数学", "数学", "数学", "数学", "数学", "数学", "数学", "数学", "数学", "数学", "数学", "数学", "数学", "数学", "数学", "数学", "数学", "数学", "数学"],
        ["数学", "数学", "数学", "数学", "数学", "数学", "数学", "数学", "数学", "数学", "数学", "数学", "数学", "数学", "数学", "数学", "数学", "数学", "数学"],
        ["数学", "数学", "数学", "数学", "数学", "数学", "数学", "数学", "数学", "数学", "数学", "数学", "数学", "数学", "数学", "数学", "数学", "数学", "数学"],
        ["物理", "物理", "物理", "物理", "物理", "物理", "物理", "物理", "物理", "物理", "物理", "物理", "物理", "物理", "物理", "物理", "物理", "物理", "物理"],
        ["物理", "物理", "物理", "物理", "物理", "物理", "物理", "物理", "物理", "物理", "物理", "物理", "物理", "物理", "物理", "物理", "物理", "物理", "物理"]
    ]
    return render_template('campus_schedule.html', title=title, date_range=date_range, days=days, time_slots=time_slots, schedule=schedule)

if __name__ == '__main__':
    app.run(debug=True)
