from app import app
from flask import render_template, request, redirect, url_for, session
from flask_mail import Mail, Message
from flask_mysqldb import MySQL
import random, string
import MySQLdb, MySQLdb.cursors, re

# Configuration for Flask-Mail
app.config['MYSQL_HOST'] = '127.0.0.1'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'testprintdb'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor' # Enable connection pooling

app.config['MAIL_SERVER'] = 'smtp.example.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'WebPrint@gmail.com'
app.config['MAIL_PASSWORD'] = 'admins'


# Initialize MySQL
mysql = MySQL(app)

# Initialize Flask-Mail
mail = Mail(app)

def get_db_connection():
    return MySQLdb.connect(host='127.0.0.1',
                           user='root',
                           passwd='',
                           db='testprintdb')
"""
def get_admin_emails():
    try:
        # Connect to the database
        cur = mysql.connection.cursor()

        # Fetch users with user_level set to "Admin"
        cur.execute("SELECT email FROM users WHERE user_level = 'Admin'")
        admin_emails = [row['email'] for row in cur.fetchall()]

        # Close cursor
        cur.close()

        return admin_emails
    except Exception as e:
        print("An error occurred:", e)
        return []

def generate_code():
    return ''.join(random.choices(string.digits, k=6))

@app.route('/send_codes', methods=['POST'])
def send_codes():
    admin_emails = get_admin_emails()
    for email in admin_emails:
        code = generate_code()
        # Send code to the user via email           #Change real
        msg = Message('Your Authentication Code', sender='WebPrint@gmail.com', recipients=[email])
        msg.body = f'Your authentication code is: {code}'
        mail.send(msg)
    return 'Authentication codes sent to admins.', 200
    """
@app.route("/admin/")
@app.route("/admin/sign_in", methods=['GET', 'POST'])
def admin_sign_in():
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        username = request.form['username']
        password = request.form['password']
        connection = get_db_connection()
        cursor = connection.cursor(MySQLdb.cursors.DictCursor)
        # Adjusted SQL query to include a condition for user_level being 'Printing Shop' or 'Customer'
        cursor.execute('SELECT * FROM user WHERE username = %s AND password = %s AND user_level IN ("Printing Shop", "Customer", "Admin")', (username, password, ))
        user = cursor.fetchone()
        if user:
            session['loggedin'] = True
            session['user_ID'] = user['user_ID']
            session['username'] = user['username']
            session['email'] = user['email']
            session['user_level'] = user['user_level'] # Store user_level in session
            if user['user_level'] == 'Admin':
                message = 'Logged in successfully as an Admin!'
                return redirect(url_for("admin_dashboard"))
        else:
            message = 'Please enter correct Username / Password or you are not authorized to access this level!'
    return render_template("level1/Login_Register.html")

@app.route('/admin/admin_logout', methods=['GET', 'POST'])
def admin_logout():
    session.pop('user_ID', None)
    session.clear()
    return redirect(url_for('admin_sign_in'))

@app.route("/admin/dashboard")
def admin_dashboard():
    return render_template("level1/Admin_Dashboard_Page.html")

@app.route("/admin/administration")
def admin_profile():
    return render_template("level1/Admin_Administration_Page.html")

@app.route("/admin/notification")
def admin_notification():
    return render_template("level1/Admin_Notification_Page.html")

@app.route("/admin/customer_service")
def admin_customer_service():
    return render_template("level1/Admin_Customer_Service_Page.html")

@app.route("/admin/accounts")
def admin_account():
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute('SELECT * FROM user')
    users = cursor.fetchall()
    connection.close()
    return render_template("level1/Admin_Administration_Page___Accounts.html", users=users)

@app.route("/admin/delete_user", methods=['DELETE'])
def admin_delete():
    try:
        user_id = request.json.get('userId')
        print(user_id)
        if user_id:
            connection = get_db_connection()
            cursor = connection.cursor()
            sql_delete_query = "DELETE FROM user WHERE user_ID = %s"
            cursor.execute(sql_delete_query, (user_id,))
            connection.commit()
            cursor.close()
            connection.close()
            return "User deleted successfully", 200
        else:
            return "No user ID provided", 400
    except Exception as e:
        return "Error deleting user: {}".format(e), 500

@app.route("/admin/my_account")
def admin_my_account():
    return render_template("level1/Admin_My_Account.html")

@app.route("/admin/change_password")
def admin_change_password():
    return render_template("level1/Admin_My_Account___Change_Password.html")

@app.route("/admin/change_email")
def admin_change_email():
    return render_template("level1/Admin_My_Account___Change_Email.html")

@app.route("/admin/people")
def admin_people():
    return render_template("level1/Admin_Administration_Page___People.html")

@app.route("/admin/image_slide")
def admin_page():
    return render_template("level1/Admin_Administration_Page___Image_Slide.html")

@app.route("/admin/shop_applicants", methods=["GET", "POST"])
def admin_shop():
    if request.method == 'POST':
        user_id = request.form.get('user_id')
        if user_id:
            try:
                connection = get_db_connection()
                cursor = connection.cursor()
                cursor.execute("UPDATE printingshops SET Approved = '1' WHERE user_ID = %s", (user_id,))
                connection.commit()
                cursor.close()
                connection.close()
                return redirect(url_for('admin_shop'))
            except Exception as e:
                print(f"Error updating database: {e}")
                return "Error updating database", 500

    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT ps.*, u.email, u.phone_number, c.category_name FROM printingshops ps LEFT JOIN user u ON ps.user_ID = u.user_ID LEFT JOIN category c ON ps.shop_ID = c.shop_ID WHERE ps.Approved = '0' OR ps.Approved = ''")
    printingshops = cursor.fetchall()
    cursor.close()
    connection.close()
    return render_template("level1/Admin_Administration_Page___Shop.html", printingshops=printingshops)

@app.route("/admin/reject_user", methods=["DELETE"])
def admin_reject():
    if request.method == 'DELETE':
        user_id = request.form.get('user_id')
        if user_id:
            try:
                connection = get_db_connection()
                cursor = connection.cursor()
                cursor.execute("DELETE FROM printingshops WHERE user_ID = %s", (user_id,))
                connection.commit()
                cursor.close()
                connection.close()
                return "User deleted successfully"
            except Exception as e:
                print(f"Error deleting from database: {e}")
                return "Error deleting from database", 500


@app.route("/admin/customer_service_reply")
def admin_reply():
    return render_template("level1/Admin_Customer_Service_Page___Reply.html")