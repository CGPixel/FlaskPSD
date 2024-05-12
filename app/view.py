from app import app
from app import process
from flask import render_template, request, redirect, url_for, session, flash, jsonify
import MySQLdb, MySQLdb.cursors, re, os, pytz, datetime
from functools import wraps
from flask_mysqldb import MySQL
from werkzeug.utils import secure_filename
from flask_dropzone import Dropzone
from datetime import datetime
from flask_mysqldb import MySQL
basedir = os.path.abspath(os.path.dirname(__file__))

app.secret_key = '\xd9\xdbg\x8f\x19q8l\x17\x9bD4D\x14\x9ff\xed\xd0\xb0\xf6!\xa3\x9dn'

app.config['MYSQL_HOST'] = '127.0.0.1'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'testprintdb'
    
mysql = MySQL(app)

def get_db_connection():
    return MySQLdb.connect(host='127.0.0.1',
                           user='root',
                           passwd='',
                           db='testprintdb')

def get_user_addresses(user_id):
    connection = get_db_connection()
    cursor = connection.cursor(MySQLdb.cursors.DictCursor) # Ensure this returns dictionaries
    cursor.execute("SELECT * FROM address WHERE user_ID = %s", (user_id,))
    addresses = cursor.fetchall()
    cursor.close()
    return addresses

def get_user(user_id):
    connection = get_db_connection()
    cursor = connection.cursor(MySQLdb.cursors.DictCursor) # Ensure this returns dictionaries
    cursor.execute("SELECT * FROM user WHERE user_ID = %s", (user_id,))
    user = cursor.fetchone()  # Fetch only one row
    cursor.close()
    return user

def get_username():
    connection = get_db_connection()
    cursor = connection.cursor(MySQLdb.cursors.DictCursor) # Ensure this returns dictionaries
    cursor.execute("SELECT username, password FROM user")
    user = cursor.fetchall()  # Fetch only one row
    cursor.close()
    return user

def get_approved_shops():
    connection = get_db_connection()
    cursor = connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM printingshops WHERE Approved = '1'")
    shops = cursor.fetchall()  # Fetch all rows
    cursor.close()
    return shops

def get_orders(user_id):
    connection = get_db_connection()
    cursor = connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM orders WHERE user_ID = %s", (user_id,))
    orders = cursor.fetchone()
    cursor.close()
    return orders

def get_db():
    try:
        return mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    except MySQLdb.OperationalError:
        # Attempt to reconnect
        mysql.connection = mysql.connect()
        return mysql.connection.cursor(MySQLdb.cursors.DictCursor)
"""
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('sign_in'))
        return f(*args, **kwargs)
    return decorated_function
"""

@app.route("/")
def guest():
    if 'username' in session and 'email' in session and session['user_level'] == 'Customer':
        return redirect(url_for('dashboard'))
    else:
        session.clear  # Log out the user
        return redirect(url_for('show_guest_dashboard'))

@app.route('/guest_dashboard')
def show_guest_dashboard():
    session.clear
    return render_template('level3/Guest_Dashboard.html')

@app.route('/logout', methods=['GET', 'POST'])
def logout():
    session.pop('user_ID', None)
    session.clear()
    return render_template('level3/Guest_Dashboard.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        username = request.form['username']
        password = request.form['password']
        connection = get_db_connection()
        cursor = connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM user WHERE username = %s AND password = %s AND user_level IN ("Printing Shop", "Customer")', (username, password, ))
        user = cursor.fetchone()
        print(user)
        if user:
            session['loggedin'] = True
            session['user_ID'] = user['user_ID']
            session['username'] = user['username']
            session['email'] = user['email']
            session['user_level'] = user['user_level']
            if user['user_level'] == 'Printing Shop':
                cursor.close()
                connection.close()
                return redirect(url_for("shop_dashboard"))
            elif user['user_level'] == 'Customer':
                cursor.close()
                connection.close()
                return redirect(url_for("dashboard"))
        else:
            return redirect(url_for('login', incorrect=True))
    return render_template('level3/Login_Register.html')

@app.route("/dashboard")
def dashboard():
    # Get the current page number from the query parameters, default to 1
    page = int(request.args.get('page', 1))

    # Define the number of shops per page
    per_page = 6

    # Get the total number of shops
    total_shops = len(get_approved_shops())

    # Calculate the total number of pages
    total_pages = (total_shops + per_page - 1) // per_page

    # Get the shops for the current page
    start_index = (page - 1) * per_page
    end_index = start_index + per_page
    shops = get_approved_shops()[start_index:end_index]

    # Pass additional information to the template
    return render_template('level3/Dashboard.html', shops=shops, page=page, total_pages=total_pages)

@app.route("/register", methods=['GET', 'POST'])
def Register():
    message = ""
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form and 'email' in request.form:
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        user_level = 3 #admin = 1 ;user= 2 ; customer = 3
        connection = get_db_connection()
        cursor = connection.cursor()
        try:
            cursor.execute('SELECT * FROM user WHERE LOWER(username) = %s', (username.lower(),))
            account = cursor.fetchone()
            if account:
                message = "Username already exists!"
            else:
                cursor.execute('SELECT * FROM user WHERE email = %s', (email,))
                account = cursor.fetchone()
                if account:
                    message = "Account Already Exists!"
                elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
                    message = "Invalid Email Address!"
                elif len(password) < 6:
                    message = "Password must be at least 6 characters long!"
                else:
                    cursor.execute('INSERT INTO user (username, email, password, user_level) VALUES (%s, %s, %s, %s)', (username, email, password, user_level,))
                    connection.commit()
                    message = "You have successfully Registered!"
                    return redirect(url_for('login'))
        except MySQLdb.OperationalError as e:
            message = "Database error: " + str(e)
        finally:
            cursor.close()
            connection.close()
    elif request.method == 'POST':
        message = "Please complete the Entry!"
    return render_template("level3/Register.html", message=message)


"""
def valid_login(username, password):
    # Your validation logic here
    # For example, you might check if the username and password are valid
    return username == 'admin' and password == 'password'

def log_the_user_in(username):
    # Your login logic here
    # For example, you might set a session variable to indicate that the user is logged in
    # session['logged_in'] = True
    return redirect(url_for('dashboard'))  # Redirect the user to the dashboard page after successful login
"""
@app.route("/change_password", methods=["GET", "POST"])
def change_Password():
    users = get_username()

    if request.method == "POST":
        username = request.form.get('Username_Input')
        old_password = request.form.get('Old_Password_Input')
        new_password = request.form.get('New_Password_Input')
        confirm_new_password = request.form.get('Confirm_New_Password_Input')
        db = get_db_connection()
        cursor = db.cursor()

        # Check if the username and old password match
        cursor.execute("SELECT * FROM user WHERE username = %s AND password = %s", (username, old_password))
        update = cursor.fetchone()
        # Check if the username and old password match
        user = next((user for user in users if user['username'] == username and user['password'] == old_password), None)
        if user is None:
            return redirect(url_for('change_Password', NotMatch=True,
                                    Username_Input=username,
                                    Old_Password_Input=old_password,
                                    New_Password_Input=new_password,
                                    Confirm_New_Password_Input=confirm_new_password))

        # Check if the new password and confirm new password match and are greater than 6 characters
        if new_password != confirm_new_password or len(new_password) < 6:
            return redirect(url_for('change_Password', PasswordNotMatch=True,
                                    Username_Input=username,
                                    Old_Password_Input=old_password,
                                    New_Password_Input=new_password,
                                    Confirm_New_Password_Input=confirm_new_password))

        # Check if either the new password or confirm password is the same as the old password
        if old_password == new_password or old_password == confirm_new_password:
            return redirect(url_for('change_Password', PasswordSameAsOld=True,
                                    Username_Input=username,
                                    Old_Password_Input=old_password,
                                    New_Password_Input=new_password,
                                    Confirm_New_Password_Input=confirm_new_password))

        # Update the password
        cursor.execute("UPDATE user SET password = %s WHERE username = %s", (new_password, username))
        db.commit()
        cursor.close()
        db.close()

        return redirect(url_for('login',
            Username_Input='',
            Old_Password_Input='',
            New_Password_Input='',
            Confirm_New_Password_Input=''))
    return render_template("level3/Change_Password.html", users=users)

@app.route("/pick_a_product/<Shop_Name>")
def store_Front_Pick_a_Product(Shop_Name):
    if request.method == "GET":
        user_id = session.get('user_ID')
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM printingshops WHERE Shop_Name = %s", (Shop_Name,))
        new_shop_data = cursor.fetchone()

        if new_shop_data is not None:  # Check if data is fetched
            session['Shop_Name'] = new_shop_data[2]
            session['Description'] = "\"" + new_shop_data[7] + "\"" if new_shop_data[7] else None

            # Get shop_ID from new_shop_data
            shop_ID = new_shop_data[0]
            # Retrieve category data based on shop_ID
            cursor.execute("SELECT * FROM category WHERE shop_ID = %s", (shop_ID,))
            category_data = cursor.fetchone()
            if category_data:  # Check if category data is fetched
                # Store category data in session
                category_names = ', '.join([name.strip() for name in category_data[2].split(',')])
                session['category_data'] = category_names
            else:
                # Clear the category_data session variable if category data is not fetched
                session.pop('category_data', None)

    user_id = session.get('user_ID')
    if Shop_Name.lower() == "dashboard":
        return redirect(url_for("dashboard"))
    if Shop_Name == "my_Address":
        session['came_from_pick_a_product'] = True
        return redirect(url_for("my_Address"))
    if Shop_Name == "my_Account":
        session['came_from_pick_a_product'] = False
        return redirect(url_for("my_Account"))
    if Shop_Name.lower() == "upload":
        session['came_from_pick_a_product'] = False
        return redirect(url_for("upload"))
    if Shop_Name == "chat":
        session['came_from_pick_a_product'] = False
        return redirect(url_for("chat_none"))
    if user_id:
        user = get_user(user_id)
        if user:
            session['username'] = user['username']
            session['phone_number'] = user['phone_number']
            session['address_user'] = user['address_user']
            return render_template("level3/Storefront___Pick_a_Product.html", Shop_Name=Shop_Name, shop_ID=shop_ID)
    return redirect(url_for("Register"))

basedir = os.path.abspath(os.path.dirname(__file__))

app.config.update(
    UPLOADED_PATH=os.path.join(basedir, 'static', 'User_Upload'),
    DROPZONE_MAX_FILE_SIZE=1024,
    DROPZONE_TIMEOUT=5*60*1000)

dropzone = Dropzone(app)
@app.route('/upload', methods=['POST', 'GET'])
def upload():
    if request.method == 'POST':
        # Check if a file was uploaded
        if 'file' not in request.files:
            return "No file uploaded.", 400

        f = request.files.get('file')
        if f.filename == '':
            return "No file selected.", 400

        filename = f.filename
        filepath = '/static/User_Upload/' + filename
        f.save(os.path.join(app.config['UPLOADED_PATH'], filename))

        conn = get_db_connection()
        cursor = conn.cursor()

        # Step 1: Insert the document into the documents table
        cursor.execute("INSERT INTO documents (user_ID, filename, file_url) VALUES (%s, %s, %s)",
                       (session.get('user_ID'), filename, filepath))
        conn.commit()

        # Step 2: Find the corresponding order_ID for the user_ID
        cursor.execute("SELECT MAX(order_ID) AS latest_order_id FROM orders WHERE user_ID = %s", (session.get('user_ID'),))
        order_id_result = cursor.fetchone()
        if order_id_result:
            order_id = order_id_result[0]
        else:
            # Handle the case where no order is found for the user_ID
            return "Error: No order found for the user.", 404

        # Step 3: Update the document with the found order_ID as its info_ID
        cursor.execute("UPDATE documents SET info_ID = %s WHERE user_ID = %s AND filename = %s",
                       (order_id, session.get('user_ID'), filename))
        conn.commit()
        cursor.close()
        return 'File uploaded successfully and updated with order information.'

    return render_template('level3/Storefront___Upload.html')

@app.route('/save_form_data', methods=['POST'])
def save_form_data():
    # Retrieve form data from the request
    data = request.get_json()

    # Extract data from the JSON object
    user_id = session.get('user_ID')  # Use.get() to avoid KeyError if 'user_ID' is not in session
    paper_size = data.get('paperSize')
    print_pages = data.get('printPages')
    print_sides = data.get('printSides')
    orientation = data.get('orientation')
    paper_type = data.get('paperType')
    copies = data.get('copies')
    grayscale = data.get('grayscale', '0')  # Default value is '0' if grayscale is not present in data

    # Insert data into the orderinfo table
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO orderinfo (user_ID, Papersize, Print_Pages, Print_Sides, Orientation, Paper_Type, Copies, Grayscale) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                   (user_id, paper_size, print_pages, print_sides, orientation, paper_type, copies, grayscale))
    conn.commit()

    # Retrieve the info_ID of the last inserted record
    cursor.execute("SELECT LAST_INSERT_ID()")
    info_id = cursor.fetchone()[0]

    # Prepare data for the orders table
    shop_ID = data.get('shop_ID')
    delivery_address = session.get('address_user', '')  # Assuming 'address_user' is stored in session
    quantity = copies
    subtotal = 45  # Fixed value
    total = 385  # Fixed value
    status = "Pending"
    order_date = datetime.now(pytz.timezone('Asia/Manila')).strftime('%Y-%m-%d %H:%M:%S')

    # Insert data into the orders table
    cursor.execute("""
    INSERT INTO orders (user_ID, info_ID, shop_ID, order_date, delivery_address, quantity, subtotal, total, status) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                       (user_id, info_id, shop_ID, order_date, delivery_address, quantity, subtotal, total, status))
    conn.commit()

    cursor.close()
    return "Form data received and saved successfully!", 200

@app.route("/approval")
def store_Front_Approval():
    user_id = session.get('user_ID')
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # Query to retrieve the latest order information
            sql_order = """
            SELECT o.shop_ID, o.order_ID, o.order_date, o.delivery_address, o.quantity, o.subtotal, o.total, o.status,
            oi.Papersize, oi.Print_Pages, oi.Print_Sides, oi.Orientation, oi.Paper_Type, oi.Copies, oi.Grayscale
            FROM orders o
            JOIN orderinfo oi ON o.info_ID = oi.Info_ID
            WHERE o.user_ID = %s
            ORDER BY o.order_date DESC
            LIMIT 1
            """
            cursor.execute(sql_order, (user_id,))

            result_order = cursor.fetchone() # Fetch one row from orders
            if result_order:
                # Extracting order details
                shop_id, order_id, order_date, delivery_address, quantity, subtotal, total, status, papersize, print_pages, print_sides, orientation, paper_type, copies, grayscale = result_order
                # Convert grayscale value to "Yes" or "No"
                grayscale_text = "Yes" if grayscale == "1" else "No"

                # Query to count the number of documents associated with the latest order_ID
                sql_document_count = """
                SELECT COUNT(*)
                FROM documents
                WHERE info_ID = %s
                """
                cursor.execute(sql_document_count, (order_id,))
                result_document_count = cursor.fetchone()
                if result_document_count:
                    filecount = result_document_count[0]
                else:
                    filecount = 0  # Default to 0 if no documents are found

                # Render the template with order details and filecount
                return render_template("level3/Storefront___Approval___Waiting.html",
                                       papersize=papersize,
                                       print_pages=print_pages,
                                       print_sides=print_sides,
                                       orientation=orientation,
                                       paper_type=paper_type,
                                       copies=copies,
                                       grayscale=grayscale_text,
                                       filecount=filecount,
                                       shop_ID=shop_id)
            else:
                return "No order found."
    except Exception as e:
        # Log the exception message for debugging
        return "An error occurred."
    finally:
        cursor.close()
        connection.close()


@app.route("/approved")
def store_Front_Approved():
    user_id = session.get('user_ID')
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # Query to retrieve the latest order information
            sql_order = """
            SELECT o.shop_ID, o.order_ID, o.order_date, o.delivery_address, o.quantity, o.subtotal, o.total, o.status,
            oi.Papersize, oi.Print_Pages, oi.Print_Sides, oi.Orientation, oi.Paper_Type, oi.Copies, oi.Grayscale
            FROM orders o
            JOIN orderinfo oi ON o.info_ID = oi.Info_ID
            WHERE o.user_ID = %s
            ORDER BY o.order_date DESC
            LIMIT 1
            """
            cursor.execute(sql_order, (user_id,))

            result_order = cursor.fetchone() # Fetch one row from orders
            if result_order:
                # Extracting order details
                shop_id, order_id, order_date, delivery_address, quantity, subtotal, total, status, papersize, print_pages, print_sides, orientation, paper_type, copies, grayscale = result_order
                # Convert grayscale value to "Yes" or "No"
                print(type(grayscale))
                grayscale_text = "Yes" if grayscale == "1" else "No"

                # Query to count the number of documents associated with the latest order_ID
                sql_document_count = """
                SELECT COUNT(*)
                FROM documents
                WHERE info_ID = %s
                """
                cursor.execute(sql_document_count, (order_id,))
                result_document_count = cursor.fetchone()
                if result_document_count:
                    filecount = result_document_count[0]
                else:
                    filecount = 0  # Default to 0 if no documents are found

                    # Render the template with order details and filename
                return render_template("level3/Storefront___Approval___Approved.html",
                                        papersize=papersize,
                                        print_pages=print_pages,
                                        print_sides=print_sides,
                                        orientation=orientation,
                                        paper_type=paper_type,
                                        copies=copies,
                                        grayscale=grayscale_text,
                                        filecount=filecount)
            else:
                return render_template("error.html", message="No order information found.")
    except Exception:
        # Log the exception message for debugging
        return "An error occurred."
    finally:
        cursor.close()
        connection.close()

@app.route("/payment")
def store_Front_Payment():
    user_id = session.get('user_ID')
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # Query to retrieve the latest order information
            sql_order = """
            SELECT o.shop_ID, o.order_ID, o.order_date, o.delivery_address, o.quantity, o.subtotal, o.total, o.status,
            oi.Papersize, oi.Print_Pages, oi.Print_Sides, oi.Orientation, oi.Paper_Type, oi.Copies, oi.Grayscale
            FROM orders o
            JOIN orderinfo oi ON o.info_ID = oi.Info_ID
            WHERE o.user_ID = %s
            ORDER BY o.order_date DESC
            LIMIT 1
            """
            cursor.execute(sql_order, (user_id,))

            result_order = cursor.fetchone() # Fetch one row from orders
            if result_order:
                # Extracting order details
                shop_id, order_id, order_date, delivery_address, quantity, subtotal, total, status, papersize, print_pages, print_sides, orientation, paper_type, copies, grayscale = result_order
                # Convert grayscale value to "Yes" or "No"
                grayscale_text = "Yes" if grayscale == "1" else "No"

                # Query to count the number of documents associated with the latest order_ID
                sql_document_count = """
                SELECT COUNT(*)
                FROM documents
                WHERE info_ID = %s
                """
                cursor.execute(sql_document_count, (order_id,))
                result_document_count = cursor.fetchone()
                if result_document_count:
                    filecount = result_document_count[0]
                else:
                    filecount = 0  # Default to 0 if no documents are found

                    # Render the template with order details and filename
                return render_template("level3/Storefront___Payment.html",
                                        papersize=papersize,
                                        print_pages=print_pages,
                                        print_sides=print_sides,
                                        orientation=orientation,
                                        paper_type=paper_type,
                                        copies=copies,
                                        grayscale=grayscale_text,
                                        filecount=filecount)
            else:
                return render_template("error.html", message="No order information found.")
    except Exception:
        # Log the exception message for debugging
        return "An error occurred."
    finally:
        cursor.close()
        connection.close()

@app.route('/update_order_status', methods=['POST'])
def update_order_status():
    # Get the user ID from the request data
    user_id = request.json.get('userID')

    # Connect to the database
    db = get_db_connection()

    # Create a cursor object
    cursor = db.cursor()

    # Query to find the latest order ID for the given user ID
    query = "SELECT MAX(order_ID) AS latest_order_id FROM orders WHERE user_ID = %s"
    cursor.execute(query, (user_id,))

    # Fetch the result
    result = cursor.fetchone()

    # Check if an order was found
    if result:
        latest_order_id = result[0]

        # Insert a new transaction record with status 'To Receive'
        insert_query = "INSERT INTO transactions (user_ID, Order_ID, Status) VALUES (%s, %s, 'To Receive')"
        cursor.execute(insert_query, (user_id, latest_order_id))
        # Commit the changes
        db.commit()
        cursor.close()
        db.close()
        print("END")
        return redirect(url_for('store_Front_Success'))
    else:
        return "No orders found for this user", 404

@app.route("/get_gcash_reference", methods=["GET", "POST"])
def get_gcash():
    app.config['Gcash_Payments'] = os.path.join(app.root_path, 'static', 'Gcash_Payments')
    if request.method == "POST":
        print("POST")
        conn = get_db_connection() # Assuming you have a function to get the database connection
        cursor = conn.cursor()

        # Get order_ID from session data
        user_ID = session["user_ID"] # Assuming you have session handling set up
        cursor.execute("SELECT order_ID FROM orders WHERE user_ID = %s ORDER BY order_ID DESC LIMIT 1", (user_ID,))
        order = cursor.fetchone()
        if order:
            order_ID = order[0]
        else:
            return "No orders found for the user."

        payment_method = "Gcash" # Default payment method

        # Upload image
        file_url = '' # Initialize file_url as empty
        if payment_method == "Gcash" and "filename" in request.files:
            file = request.files["filename"]
            if file.filename != '':
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['Gcash_Payments'], filename)
                file.save(file_path)
                file_url = os.path.join('static', 'Gcash_Payments', filename)


        # Process form submission
        if not file_url:
            payment_method = "COD" # Update payment method if Gcash checkbox is checked
        # Insert data into payments table
        payment_status = "Pending"

        # Get the current time in UTC
        now_utc = datetime.utcnow()

        # Convert UTC time to Philippine time
        ph_tz = pytz.timezone('Asia/Manila')
        now_ph = now_utc.astimezone(ph_tz)

        # Format the Philippine time as a timestamp
        payment_date = now_ph.strftime('%Y-%m-%d %H:%M:%S')

        cursor.execute("INSERT INTO payments (order_ID, payment_method, payment_status, payment_date, receipt) VALUES (%s, %s, %s, %s, %s)",
                       (order_ID, payment_method, payment_status, payment_date, file_url))
        conn.commit()

        cursor.close()
        conn.close()

        return "Payment information inserted successfully."
    return "Gcash"

@app.route("/success")
def store_Front_Success():
    return render_template("level3/Storefront___Success.html")

@app.route("/my_Purchase")
def my_Purchases():
    return render_template("level3/My_Purchase___All.html")

@app.route("/my_Print")
def my_Prints():
    return render_template("level3/My_Purchase___To_Print.html")

@app.route("/my_Ship")
def my_Ship():
    return render_template("level3/My_Purchase___To_Ship.html")

@app.route("/my_Purchase_Completed")
def my_Purchase_Completed():
    return render_template("level3/My_Purchase___Completed.html")

@app.route("/my_Account", methods=['GET', 'POST'])
def my_Account():
    session['came_from_pick_a_product'] = False
    user_id = session.get('user_ID')
    #if 'user_ID' not in session:
        #return redirect(url_for('login'))

    # Use a single cursor creation and ensure it's properly managed
    try:
        connection = get_db_connection()
        cursor = connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM user WHERE user_ID = %s', (user_id, ))
        user = cursor.fetchone()
        if user:
            session['phone_number'] = user['phone_number']
    except Exception as e:
        # Log the error for debugging
        return "An error occurred while fetching user details."
    finally:
        # Ensure the cursor and connection are closed properly
        cursor.close()
        connection.close()

    if request.method == 'POST':
        new_username = request.form.get('username')
        if new_username and new_username.lower() != 'username':
            user_id = session.get('user_ID')
            try:
                connection = get_db_connection()
                cursor = connection.cursor()
                sql_update_query = "UPDATE user SET username = %s WHERE user_ID = %s"
                cursor.execute(sql_update_query, (new_username, user_id))
                connection.commit()
                cursor.close()
                connection.close()

                session['username'] = new_username
                return redirect(url_for('my_Account'))
            except Exception as e:
                return f"An error occurred: {str(e)}"
        else:
            return "Error: Invalid username"

    return render_template("level3/My_Account.html")

@app.route("/delete_address/<int:address_id>", methods=['DELETE'])
def delete_address(address_id):
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        sql_delete_query = "DELETE FROM address WHERE address_ID = %s"
        cursor.execute(sql_delete_query, (address_id,))
        connection.commit()
        cursor.close()
        connection.close()

        return 'Address deleted successfully', 200
    except Exception as e:
        return f"An error occurred: {str(e)}", 500

@app.route("/set_default_address", methods=['POST'])
def set_default_address():
    data = request.get_json()
    address_id = data['addressId']
    user_id = session.get('user_ID')

    # Connect to the database
    connection = get_db_connection()
    cursor = connection.cursor()

    # Reset default_address for all addresses belonging to the user
    sql_reset_query = """
        UPDATE address
        SET default_address = CAST(0 AS INT)
        WHERE user_ID = %s
    """
    cursor.execute(sql_reset_query, (user_id,))

    # Set the default_address for the clicked address to 1
    sql_update_query = """
        UPDATE address
        SET default_address = %s
        WHERE address_ID = %s
    """
    cursor.execute(sql_update_query, (1, address_id))

    # Fetch address details for the default address
    sql_address_query = """
    SELECT
        a.address_user,
        a.phone_number
    FROM
        address a
    WHERE
        a.default_address = 1 AND a.user_ID = %s
    """
    cursor.execute(sql_address_query, (user_id,))
    address_data = cursor.fetchone()

    if address_data:
        address_user, phone_number = address_data

        # Update user table with new address details
        sql_user_update_query = """
        UPDATE user
        SET phone_number = %s, address_user = %s
        WHERE user_ID = %s
        """
        cursor.execute(sql_user_update_query, (phone_number, address_user, user_id))
        connection.commit()
        cursor.close()

        return {'message': 'Default address updated successfully'}, 200
    else:
        cursor.close()
        return {'error': 'Default address not found'}, 404

@app.route("/my_Address", methods=['GET', 'POST'])
def my_Address():
    if request.method == 'POST':
        data = request.get_json()
        user_id = data['user_ID']
        new_phone_number = "0" # Temporary number
        new_address = "Address" # Temporary address
        default_address = "" # Not default

        connection = get_db_connection()
        cursor = connection.cursor()
        sql_insert_query = """
            INSERT INTO address (user_ID, phone_number, address_user, default_address)
            VALUES (%s, %s, %s, %s)
        """
        cursor.execute(sql_insert_query, (user_id, new_phone_number, new_address, default_address, ))
        connection.commit()
        cursor.close()

        return {'message': 'New address added successfully'}, 201
    else:
        user_id = session.get('user_ID')
        addresses = get_user_addresses(user_id)
        # Sort addresses by address_ID to ensure a consistent order
        addresses = sorted(addresses, key=lambda x: x['address_ID'])

        came_from_pick_a_product = session.get('came_from_pick_a_product', False)

        if addresses:
            # Set the first address in the session
            session['address'] = addresses[0]

            # Alternatively, set specific fields in the session
            session['address_ID'] = addresses[0]['address_ID']
            session['address_user'] = addresses[0]['address_user']
            session['phone_number'] = addresses[0]['phone_number']

        return render_template("level3/My_Addresses.html", addresses=addresses, came_from_pick_a_product=came_from_pick_a_product)


@app.route("/edit_address/<int:address_id>", methods=['GET', 'POST'])
def edit_Address(address_id):
    if request.method == 'GET':
        user_id = session.get('user_ID')
        addresses = get_user_addresses(user_id)
        # Sort addresses by address_ID to ensure a consistent order
        addresses = sorted(addresses, key=lambda x: x['address_ID'])

        # Find the address with the specified address_id
        address_to_edit = None
        for address in addresses:
            if address['address_ID'] == address_id:
                address_to_edit = address
                break

        if address_to_edit:
            # Set the found address in the session
            session['address'] = address_to_edit

            # Alternatively, set specific fields in the session
            session['address_ID'] = address_to_edit['address_ID']
            session['address_user'] = address_to_edit['address_user']
            session['phone_number'] = address_to_edit['phone_number']
            session['address_name'] = address_to_edit['address_name']
        else:
            # Handle the case where no address with the given ID is found
            # You might want to redirect to an error page or display a message
            return "Address not found", 404

    if request.method == 'POST':
        # Get user_id from the session
        user_id = session.get('user_ID')
        if user_id is None:
            # Handle the case where user_ID is not found in the session
            return "User not logged in", 401

        # Extract form data
        phone_number = request.form.get('phone_number')
        address_name = request.form.get('address_name')
        address2 = request.form.get('address2')
        address3 = request.form.get('address3')
        address1 = request.form.get('address1')
        full_address = ", ".join(filter(None, [address2, address3, address1]))

        # Determine the value of default_address based on whether the checkbox is checked
        default_address = 1 if request.form.get('set_default') == '1' else ""

        # Connect to the database
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute("UPDATE address SET default_address = 0 WHERE user_ID = %s", (user_id,))
        # Prepare the SQL update query
        sql_update_query = """UPDATE address SET address_name = %s, phone_number = %s, address_user = %s, default_address = %s WHERE address_ID = %s"""
        input_data = (address_name, phone_number, full_address, default_address, address_id)

        # Execute the update query
        cursor.execute(sql_update_query, input_data)

        # Commit the changes
        connection.commit()

        # Fetch address details for the default address
        sql_address_query = """
        SELECT
            a.address_user,
            a.phone_number
        FROM
            address a
        WHERE
            a.default_address = 1 AND a.user_ID = %s
        """
        cursor.execute(sql_address_query, (user_id,))
        address_data = cursor.fetchone()

        if address_data:
            address_user, phone_number = address_data

            # Update user table with new address details
            sql_user_update_query = """
            UPDATE user
            SET phone_number = %s, address_user = %s
            WHERE user_ID = %s
            """
            cursor.execute(sql_user_update_query, (phone_number, address_user, user_id))
            connection.commit()

        # Close the cursor and connection
        cursor.close()
        connection.close()

        # Redirect back to the edit address page
        return redirect(url_for('edit_Address', address_id=address_id))

    return render_template("level3/Edit_Addresses.html", address_id=address_id)


@app.route("/my_Pending_Approval", methods=['GET', 'POST'])
def my_Pending_Approval():
    # Connect to the database
    connection = get_db_connection()
    cursor = connection.cursor()

    # Fetch data from the "orderinfo" table for the current user
    user_id = session.get('user_ID')  # Assuming session contains user_ID
    cursor.execute("SELECT * FROM orderinfo WHERE user_ID = %s", (user_id,))
    orders = cursor.fetchall()

    # Close cursor and connection
    cursor.close()
    connection.close()

    # Render template with orders data
    return render_template("level3/Checkouts___1.html", orders=orders)

@app.route("/my_Checkout")
def my_Checkout():
    return render_template("level3/Checkouts.html")

@app.route("/rating")
def my_rating():
    return render_template("level3/Rating.html")

@app.route("/chat")
def chat_none():
    return render_template("level3/Chat_Page.html")

@app.route("/chat/<shop_id>")
def chat(shop_id):
    user_id = session.get('user_ID')
    connection = get_db_connection()
    cursor = connection.cursor()

    # Query the database for shop details
    cursor.execute("SELECT * FROM printingshops WHERE Shop_ID = %s", (shop_id,))
    shop_details = cursor.fetchone()
    """
    cursor.execute("SELECT order_ID FROM orders WHERE user_ID = %s ORDER BY order_ID DESC LIMIT 1", (user_id,))
    order_row = cursor.fetchone()
    print(order_row)
    if order_row:
        order_id = order_row[0]
        print("orderID", order_id)
        # Now that you have the order_ID, you can use it to fetch documents
        cursor.execute("SELECT filename FROM documents WHERE info_ID IN (SELECT order_ID FROM orders WHERE order_ID = %s)", (order_id,))
        documents = cursor.fetchall()
        print("Docs:",documents)
    else:
        return "Order not found."
    """
    # Store shop details in the session
    session['shop_details'] = {
        'shop_ID': shop_details[0],
        'user_ID': shop_details[1],
        'Shop_Name': shop_details[2],
        'Shop_Address': shop_details[3],
        'Detail_Address': shop_details[4],
        'Postal_Code': shop_details[5],
        'Number': shop_details[6],
        'Description': shop_details[7],
        'Approved': shop_details[8]
    }
    # Fetch all messages for the given shop and user
    cursor.execute("SELECT * FROM messages WHERE Shop_ID = %s AND user_ID = %s ORDER BY TimeStamp ASC", (shop_id, session.get('user_ID')))
    messages = cursor.fetchall()

    # Filter out messages with different shop_ID
    filtered_messages = [message for message in messages if message[2] == session['shop_details']['shop_ID']]

    # Fetch all messages for the given shop and user
    cursor.execute("SELECT * FROM messages WHERE Shop_ID = %s AND user_ID = %s ORDER BY TimeStamp DESC", (shop_id, session.get('user_ID')))
    last_messages = cursor.fetchone()
    # Close database connection
    connection.close()
    # Render the template with messages and shop details
    return render_template("level3/Chat_Page.html", last_messages=last_messages, shop_id=shop_id, messages=filtered_messages) #, documents=documents

@app.route('/submit_message', methods=['POST'])
def submit_message():
    data = request.get_json()
    # Extract data from the request
    user_level = data.get('user_level')
    timestamp = data.get('timestamp')
    message = data.get('message')
    user_ID = data.get('user_ID')
    Shop_ID = data.get('Shop_ID')
    # Insert the message into the database
    # This is a simplified example; you should handle errors and use parameterized queries
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("INSERT INTO messages (user_level, timestamp, message, user_ID, Shop_ID) VALUES (%s, %s, %s, %s, %s)",
                    (user_level, timestamp, message, user_ID, Shop_ID))
        connection.commit()
    except Exception as e:
        print(f"Error inserting message: {e}")
        connection.rollback()
    finally:
        connection.close()

@app.route("/chat_follow")
def chat_follow():
    return render_template("level3/Chat_Page___Following.html")

@app.route("/chat_unread")
def chat_unread():
    return render_template("level3/Chat_Page___Unread.html")

@app.route("/helloworld")
def hello_world():
    return "<b style='font-size: 40px'>Hello World!</b>"
@app.route("/fontanilla")
def backend_frontend():
    return "<b style='font-size: 40px'>Fontanilla, Jairus Vincent L.</b>"