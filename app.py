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
                             week_offset=current_week_offset,  # 传递周偏移量到模板
                             all_weeks_schedule={})  # 添加空的all_weeks_schedule

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
        
        # 校区课程表：增加classroom字段，唯一索引为(month, campus, classroom, day_index, time_slot_index)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS campus_schedule (
                id INT AUTO_INCREMENT PRIMARY KEY,
                schedule_title VARCHAR(100) NOT NULL DEFAULT '暑假崇达数理化课程表',
                date_range VARCHAR(50) NOT NULL DEFAULT '2025.7.13-7.31',
                month VARCHAR(7) NOT NULL DEFAULT '2025-07',
                campus VARCHAR(20) NOT NULL DEFAULT 'wendefu',
                classroom VARCHAR(20) NOT NULL DEFAULT 'a',
                day_index INT NOT NULL,
                time_slot_index INT NOT NULL,
                day_label VARCHAR(20) NOT NULL,
                time_slot VARCHAR(20) NOT NULL,
                subject VARCHAR(20) DEFAULT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                UNIQUE KEY unique_schedule (month, campus, classroom, day_index, time_slot_index)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        
        # 学生课程表：新增表，唯一索引为(month, campus, student_name, day_index, time_slot_index)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS student_schedule (
                id INT AUTO_INCREMENT PRIMARY KEY,
                schedule_title VARCHAR(100) NOT NULL DEFAULT '暑假崇达数理化课程表',
                date_range VARCHAR(50) NOT NULL DEFAULT '2025.7.13-7.31',
                month VARCHAR(7) NOT NULL DEFAULT '2025-07',
                campus VARCHAR(20) NOT NULL DEFAULT 'wendefu',
                student_name VARCHAR(50) NOT NULL,
                day_index INT NOT NULL,
                time_slot_index INT NOT NULL,
                day_label VARCHAR(20) NOT NULL,
                time_slot VARCHAR(20) NOT NULL,
                subject VARCHAR(20) DEFAULT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                UNIQUE KEY unique_student_schedule (month, campus, student_name, day_index, time_slot_index)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        
        # 学生课程表名称管理表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS student_schedule_names (
                id INT AUTO_INCREMENT PRIMARY KEY,
                month VARCHAR(7) NOT NULL DEFAULT '2025-07',
                campus VARCHAR(20) NOT NULL DEFAULT 'wendefu',
                student_name VARCHAR(50) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY unique_student_name (month, campus, student_name)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        
        # 检查是否需要添加classroom字段
        cursor.execute("SHOW COLUMNS FROM campus_schedule LIKE 'classroom'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE campus_schedule ADD COLUMN classroom VARCHAR(20) NOT NULL DEFAULT 'a'")
            # 删除旧的unique key并创建新的
            try:
                cursor.execute("DROP INDEX unique_schedule ON campus_schedule")
            except:
                pass
            cursor.execute("CREATE UNIQUE INDEX unique_schedule ON campus_schedule (month, campus, classroom, day_index, time_slot_index)")
        
        connection.commit()
    except Exception as e:
        print(f"初始化数据库时出错: {str(e)}")
    finally:
        cursor.close()
        connection.close()

# 在应用启动时初始化数据库
init_db()

@app.route('/campus_schedule', methods=['GET', 'POST'])
def campus_schedule():
    # 获取当前月份参数
    month = request.args.get('month') if request.method == 'GET' else request.json.get('month')
    # 获取当前校区参数
    campus = request.args.get('campus', 'wendefu')
    # 获取课表类型参数
    schedule_type = request.args.get('type', 'classroom')  # 默认为教室课表

    # 默认当前年月
    if not month:
        today = datetime.date.today()
        month = f"{today.year}-{today.month:02d}"

    if request.method == 'POST':
        # 处理课程表更新
        data = request.get_json()
        campus = data.get('campus', 'wendefu')
        schedule_type = data.get('type', 'classroom')
        day_index = data.get('day_index')
        time_slot_index = data.get('time_slot_index')
        subject = data.get('subject')
        day_label = data.get('day_label')
        time_slot = data.get('time_slot')
        
        connection = get_db_connection()
        if not connection:
            return jsonify({"success": False, "message": "数据库连接错误"}), 500
        
        cursor = connection.cursor()
        try:
            if schedule_type == 'classroom':
                classroom = data.get('classroom', 'a')
                if subject and subject.strip():
                    # 插入或更新课程
                    query = """
                        INSERT INTO campus_schedule (month, campus, classroom, day_index, time_slot_index, day_label, time_slot, subject)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE 
                        subject = %s,
                        day_label = %s,
                        time_slot = %s,
                        updated_at = CURRENT_TIMESTAMP
                    """
                    cursor.execute(query, (month, campus, classroom, day_index, time_slot_index, day_label, time_slot, subject, subject, day_label, time_slot))
                else:
                    # 删除课程
                    query = "DELETE FROM campus_schedule WHERE month = %s AND campus = %s AND classroom = %s AND day_index = %s AND time_slot_index = %s"
                    cursor.execute(query, (month, campus, classroom, day_index, time_slot_index))
            else:  # student
                student_name = data.get('student_name')
                
                # 先检查是否已经存在这个学生的课程
                check_query = "SELECT subject FROM student_schedule WHERE month = %s AND campus = %s AND student_name = %s AND day_index = %s AND time_slot_index = %s"
                cursor.execute(check_query, (month, campus, student_name, day_index, time_slot_index))
                existing_course = cursor.fetchone()
                
                if subject and subject.strip():
                    # 插入或更新学生课程
                    query = """
                        INSERT INTO student_schedule (month, campus, student_name, day_index, time_slot_index, day_label, time_slot, subject)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE 
                        subject = %s,
                        day_label = %s,
                        time_slot = %s,
                        updated_at = CURRENT_TIMESTAMP
                    """
                    cursor.execute(query, (month, campus, student_name, day_index, time_slot_index, day_label, time_slot, subject, subject, day_label, time_slot))
                    
                    # 如果是新增课程（而不是更新），自动分配教室
                    if not existing_course:
                        # 定义校区对应的教室列表
                        campus_classrooms = {
                            'wendefu': ['a', 'b', 'c', 'd'],  # 文德福4个教室
                            'cuihai': ['a', 'b'],             # 翠海2个教室
                            'weipeng': ['a', 'b', 'c', 'd', 'e']  # 玮鹏5个教室
                        }
                        
                        classrooms = campus_classrooms.get(campus, ['a'])
                        assigned_classroom = None
                        
                        # 按a,b,c...顺序查找可用教室
                        for classroom in classrooms:
                            # 检查该教室在同一时间是否已被占用
                            check_classroom_query = """
                                SELECT subject FROM campus_schedule 
                                WHERE month = %s AND campus = %s AND classroom = %s 
                                AND day_index = %s AND time_slot_index = %s
                            """
                            cursor.execute(check_classroom_query, (month, campus, classroom, day_index, time_slot_index))
                            existing_classroom_course = cursor.fetchone()
                            
                            if not existing_classroom_course:
                                # 找到可用教室，分配给该课程
                                assigned_classroom = classroom
                                break
                        
                        # 如果找到可用教室，在教室课表中添加该课程
                        if assigned_classroom:
                            insert_classroom_query = """
                                INSERT INTO campus_schedule (month, campus, classroom, day_index, time_slot_index, day_label, time_slot, subject)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                            """
                            cursor.execute(insert_classroom_query, (month, campus, assigned_classroom, day_index, time_slot_index, day_label, time_slot, subject))
                else:
                    # 删除学生课程
                    query = "DELETE FROM student_schedule WHERE month = %s AND campus = %s AND student_name = %s AND day_index = %s AND time_slot_index = %s"
                    cursor.execute(query, (month, campus, student_name, day_index, time_slot_index))
                    
                    # 如果删除的是学生课程，也需要从教室课表中删除对应的课程
                    if existing_course:
                        old_subject = existing_course[0]
                        # 查找该课程在教室课表中的位置并删除
                        delete_classroom_query = """
                            DELETE FROM campus_schedule 
                            WHERE month = %s AND campus = %s AND day_index = %s AND time_slot_index = %s AND subject = %s
                            LIMIT 1
                        """
                        cursor.execute(delete_classroom_query, (month, campus, day_index, time_slot_index, old_subject))
            
            connection.commit()
            return jsonify({"success": True})
        except Exception as e:
            print(f"Error updating schedule: {str(e)}")
            return jsonify({"success": False, "message": str(e)}), 500
        finally:
            cursor.close()
            connection.close()
    
    # GET请求 - 从数据库读取数据
    connection = get_db_connection()
    if not connection:
        return render_template('campus_schedule.html', error="数据库连接错误")
    
    # 基础数据
    title = "暑假崇达数理化课程表"
    
    # 定义校区和对应的教室数量
    campus_classrooms = {
        'wendefu': ['a', 'b', 'c', 'd'],  # 文德福4个教室
        'cuihai': ['a', 'b'],             # 翠海2个教室
        'weipeng': ['a', 'b', 'c', 'd', 'e']  # 玮鹏5个教室
    }
    
    # 根据月份动态生成日期范围
    try:
        year, month_num = month.split('-')
        year = int(year)
        month_num = int(month_num)
        
        # 获取该月的第一天和最后一天
        first_day = datetime.date(year, month_num, 1)
        if month_num == 12:
            last_day = datetime.date(year + 1, 1, 1) - datetime.timedelta(days=1)
        else:
            last_day = datetime.date(year, month_num + 1, 1) - datetime.timedelta(days=1)
        
        # 生成该月的所有日期
        days = []
        current_date = first_day
        while current_date <= last_day:
            weekday_names = ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日']
            weekday = weekday_names[current_date.weekday()]
            days.append(f"{current_date.month}/{current_date.day} {weekday}")
            current_date += datetime.timedelta(days=1)
        
        date_range = f"{year}.{month_num}.{first_day.day}-{last_day.day}"
        
    except Exception as e:
        # 如果解析失败，使用默认值
        print(f"日期解析错误: {e}")
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
    
    cursor = connection.cursor(dictionary=True)
    cursor.close()
    connection.close()
    
    # 初始化空的课程表
    schedule = [["" for _ in range(len(days))] for _ in range(len(time_slots))]
    
    return render_template('campus_schedule.html', 
                         title=title, 
                         date_range=date_range, 
                         days=days, 
                         time_slots=time_slots, 
                         schedule=schedule,
                         current_month=month,
                         current_campus=campus,
                         current_type=schedule_type,
                         campus_classrooms=campus_classrooms)

@app.route('/add_student_schedule', methods=['POST'])
def add_student_schedule():
    """添加新的学生课表"""
    data = request.get_json()
    month = data.get('month')
    campus = data.get('campus')
    student_name = data.get('student_name')
    
    if not all([month, campus, student_name]):
        return jsonify({"success": False, "message": "缺少必要参数"}), 400
    
    connection = get_db_connection()
    if not connection:
        return jsonify({"success": False, "message": "数据库连接错误"}), 500
    
    cursor = connection.cursor()
    try:
        # 插入学生课表名称
        query = "INSERT INTO student_schedule_names (month, campus, student_name) VALUES (%s, %s, %s)"
        cursor.execute(query, (month, campus, student_name))
        connection.commit()
        return jsonify({"success": True})
    except Exception as e:
        print(f"Error adding student schedule: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        cursor.close()
        connection.close()

@app.route('/delete_student_schedule', methods=['POST'])
def delete_student_schedule():
    """删除学生课表"""
    data = request.get_json()
    month = data.get('month')
    campus = data.get('campus')
    student_name = data.get('student_name')
    
    if not all([month, campus, student_name]):
        return jsonify({"success": False, "message": "缺少必要参数"}), 400
    
    connection = get_db_connection()
    if not connection:
        return jsonify({"success": False, "message": "数据库连接错误"}), 500
    
    cursor = connection.cursor()
    try:
        # 删除学生课表数据
        query = "DELETE FROM student_schedule WHERE month = %s AND campus = %s AND student_name = %s"
        cursor.execute(query, (month, campus, student_name))
        # 删除学生课表名称
        query = "DELETE FROM student_schedule_names WHERE month = %s AND campus = %s AND student_name = %s"
        cursor.execute(query, (month, campus, student_name))
        connection.commit()
        return jsonify({"success": True})
    except Exception as e:
        print(f"Error deleting student schedule: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        cursor.close()
        connection.close()

@app.route('/campus_schedule_data', methods=['GET'])
def campus_schedule_data():
    # 获取参数
    month = request.args.get('month')
    campus = request.args.get('campus', 'wendefu')
    schedule_type = request.args.get('type', 'classroom')
    
    if not month:
        today = datetime.date.today()
        month = f"{today.year}-{today.month:02d}"
    
    connection = get_db_connection()
    if not connection:
        return jsonify({"success": False, "message": "数据库连接错误"}), 500
    
    # 基础数据 - 根据月份动态生成日期
    try:
        year, month_num = month.split('-')
        year = int(year)
        month_num = int(month_num)
        
        # 获取该月的第一天和最后一天
        first_day = datetime.date(year, month_num, 1)
        if month_num == 12:
            last_day = datetime.date(year + 1, 1, 1) - datetime.timedelta(days=1)
        else:
            last_day = datetime.date(year, month_num + 1, 1) - datetime.timedelta(days=1)
        
        # 生成该月的所有日期
        days = []
        current_date = first_day
        while current_date <= last_day:
            weekday_names = ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日']
            weekday = weekday_names[current_date.weekday()]
            days.append(f"{current_date.month}/{current_date.day} {weekday}")
            current_date += datetime.timedelta(days=1)
        
    except Exception as e:
        # 如果解析失败，使用默认值
        print(f"日期解析错误: {e}")
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
    
    cursor = connection.cursor(dictionary=True)
    all_schedules = {}
    schedules_list = []
    
    if schedule_type == 'classroom':
        # 定义校区和对应的教室数量
        campus_classrooms = {
            'wendefu': ['a', 'b', 'c', 'd'],  # 文德福4个教室
            'cuihai': ['a', 'b'],             # 翠海2个教室
            'weipeng': ['a', 'b', 'c', 'd', 'e']  # 玮鹏5个教室
        }
        
        classrooms = campus_classrooms.get(campus, ['a'])
        schedules_list = classrooms
        
        for classroom_name in classrooms:
            query = "SELECT day_index, time_slot_index, subject FROM campus_schedule WHERE month = %s AND campus = %s AND classroom = %s"
            cursor.execute(query, (month, campus, classroom_name))
            db_schedule = cursor.fetchall()
            
            # 初始化空的课程表
            schedule = [["" for _ in range(len(days))] for _ in range(len(time_slots))]
            
            # 填充从数据库读取的数据
            for entry in db_schedule:
                day_idx = entry['day_index']
                time_idx = entry['time_slot_index']
                subject = entry['subject']
                if 0 <= time_idx < len(time_slots) and 0 <= day_idx < len(days):
                    schedule[time_idx][day_idx] = subject
            
            all_schedules[classroom_name] = schedule
    else:  # student
        # 获取学生课表名称列表
        query = "SELECT student_name FROM student_schedule_names WHERE month = %s AND campus = %s ORDER BY created_at"
        cursor.execute(query, (month, campus))
        student_names = cursor.fetchall()
        schedules_list = [item['student_name'] for item in student_names]
        
        for student_name in schedules_list:
            query = "SELECT day_index, time_slot_index, subject FROM student_schedule WHERE month = %s AND campus = %s AND student_name = %s"
            cursor.execute(query, (month, campus, student_name))
            db_schedule = cursor.fetchall()
            
            # 初始化空的课程表
            schedule = [["" for _ in range(len(days))] for _ in range(len(time_slots))]
            
            # 填充从数据库读取的数据
            for entry in db_schedule:
                day_idx = entry['day_index']
                time_idx = entry['time_slot_index']
                subject = entry['subject']
                if 0 <= time_idx < len(time_slots) and 0 <= day_idx < len(days):
                    schedule[time_idx][day_idx] = subject
            
            all_schedules[student_name] = schedule
    
    cursor.close()
    connection.close()
    
    return jsonify({
        "success": True,
        "all_schedules": all_schedules,
        "schedules_list": schedules_list,
        "campus": campus,
        "month": month,
        "days": days,
        "time_slots": time_slots,
        "type": schedule_type
    })

if __name__ == '__main__':
    app.run(debug=True)
