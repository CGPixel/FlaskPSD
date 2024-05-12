from app import app
from flask import render_template, request, redirect, url_for, session, flash
import MySQLdb, MySQLdb.cursors, re, os
from flask_mysqldb import MySQL

app.secret_key = '\xd9\xdbg\x8f\x19q8l\x17\x9bD4D\x14\x9ff\xed\xd0\xb0\xf6!\xa3\x9dn'

app.config['MYSQL_HOST'] = '127.0.0.1'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'testprintdb'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor' # Enable connection pooling

mysql = MySQL(app)

def get_db_connection():
    return MySQLdb.connect(host='127.0.0.1',
                           user='root',
                           passwd='',
                           db='testprintdb')

def get_db():
    try:
        return mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    except MySQLdb.OperationalError:
        # Attempt to reconnect
        mysql.connection = mysql.connect()
        return mysql.connection.cursor(MySQLdb.cursors.DictCursor)

@app.route("/shop/")
def redirect_shop_register():
    return redirect(url_for("shop_register"))

@app.route("/shop/logout")
def shop_logout():
    session.pop('user_ID', None)
    session.clear()
    return redirect(url_for("shop_register"))

@app.route("/shop/register", methods=['GET', 'POST'])
def shop_register():
    message = ""
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form and 'email' in request.form:
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        user_level = 2 #admin = 1 ;Printing Shop= 2 ; custormer = 2
        if len(password) < 6:
            message = "Password must be at least 6 characters long!"
        else:
            connection = get_db_connection()
            cursor = connection.cursor()
            cursor.execute('SELECT * FROM user WHERE username = %s', (email,))
            account = cursor.fetchone()
            if account:
                message = "Account Already Exists!"
            elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
                message = "Invalid Email Address!"
            elif not username or not password or not email:
                message = "Please complete the Entry!"
            else:
                cursor.execute('INSERT INTO user (username, email, password, user_level) VALUES (%s, %s, %s, %s)', (username, email, password, user_level,))
                connection.commit()
                cursor.close()
                connection.close()
                message = "You have successfully Registered!"
                return redirect(url_for('shop_sign_in'))
    elif request.method == 'POST':
        message = "Please complete the Entry!"
    return render_template("level2/Register.html")

@app.route("/shop/sign_in", methods=['GET', 'POST'])
def shop_sign_in():
    message = ''
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        username = request.form['username']
        password = request.form['password']
        connection = get_db_connection()
        cursor = connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM user WHERE username = %s AND password = %s AND user_level IN ("Printing Shop", "Customer")', (username, password, ))
        user = cursor.fetchone()
        if user:
            session['loggedin'] = True
            session['user_ID'] = user['user_ID']
            session['username'] = user['username']
            session['email'] = user['email']
            session['user_level'] = user['user_level'] # Store user_level in session
            if user['user_level'] == 'Printing Shop':
                message = 'Logged in successfully as a Printing Shop!'
                return redirect(url_for("shop_dashboard")) # Redirect to Printing Shop Dashboard
            elif user['user_level'] == 'Customer':
                message = 'Logged in successfully as a Customer!'
                return redirect(url_for("Dashboard")) # Redirect to Customer Dashboard
        else:
            return redirect(url_for('shop_sign_in', incorrect=True))
    return render_template("level2/Login_Register.html", message=message)


@app.route("/shop/dashboard")
def shop_dashboard():
    if 'username' in session and session['user_level'] == 'Printing Shop':
        # Assuming you have a user_id stored in the session
        user_id = session['user_ID']
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT Approved FROM printingshops WHERE user_id = %s", (user_id,))
        result = cursor.fetchone()
        # Extract the approval status from the result tuple and convert it to boolean
        approval_status = result[0] == '1' if result else False
        return render_template('level2/Shop_Dashboard.html', approved=approval_status)
    return redirect(url_for('shop_sign_in'))

@app.route("/shop/register_service")
def shop_register_service():
    return render_template("level2/Print_Servicing___Register_1.html")

@app.route('/shop/register_shop', methods=['GET', 'POST'])
def shop_register_shop():
    if request.method == 'GET':
        user_id = session.get('user_ID')

        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM printingshops WHERE user_ID = %s", (user_id,))
        new_shop_data = cursor.fetchone()

        if new_shop_data:
            session["shop_ID"] = new_shop_data[0]
            session["Shop_Name"] = new_shop_data[2]
            session["Shop_Address"] = new_shop_data[3]
            session["Detail_Address"] = new_shop_data[4]
            session["Postal_Code"] = new_shop_data[5]
            session["Number"] = new_shop_data[6]
            session["Description"] = new_shop_data[7]

    if request.method == 'POST':
        user_id = session.get('user_ID')
        if user_id is None:
            return "User ID not found in session", 400

        shop_name = request.form.get('username')
        shop_address = request.form.get('pickupAddress')
        detail_address = request.form.get('detailAddress')  # Assuming you added a name attribute to this field
        postal_code = request.form.get('postalCode')
        phone_number = request.form.get('phone_Number')
        # Check if the user already has a shop
        connection = get_db_connection()
        if connection is None:
            return "Failed to connect to the database", 500

        try:
            cursor = connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute("SELECT * FROM printingshops WHERE user_ID = %s", (user_id,))
            existing_shop = cursor.fetchone()

            if existing_shop:
                cursor.close()
                connection.close()
                # User already has a shop, redirect to /register_profile
                return redirect('register_profile')

            # Insert new shop into database
            cursor.execute("INSERT INTO printingshops (user_ID, Shop_Name, Shop_Address, Detail_Address, Postal_Code, Number) VALUES (%s, %s, %s, %s, %s, %s)",
                           (session.get('user_ID'), shop_name, shop_address, detail_address, postal_code, phone_number))
            connection.commit()
            cursor.close()
            connection.close()
            return redirect('shop_register_profile')

        except Exception as e:
            # Rollback the transaction in case of an error
            connection.rollback()
            return f"Error inserting shop into database: {str(e)}", 500

    return render_template("level2/Print_Servicing___Register__2.html")

@app.route("/shop/register_profile")
def shop_register_profile():
    if request.method == "GET":
        user_id = session.get('user_ID')

        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM printingshops WHERE user_ID = %s", (user_id,))
        new_shop_data = cursor.fetchone()

        # Retrieve shop_ID from printingshops table based on user_ID
        cursor.execute("SELECT shop_ID FROM printingshops WHERE user_ID = %s", (user_id,))
        shop_data = cursor.fetchone()

        if new_shop_data:
            session["shop_ID"] = new_shop_data[0]
            session["Shop_Name"] = new_shop_data[2]
            session["Shop_Address"] = new_shop_data[3]
            session["Detail_Address"] = new_shop_data[4]
            session["Postal_Code"] = new_shop_data[5]
            session["Number"] = new_shop_data[6]
            session['Description'] = new_shop_data[7].replace('&#34;', '')

        if shop_data:
            shop_ID = shop_data[0]

            # Check if shop_ID exists in the category table
            cursor.execute("SELECT category_name FROM category WHERE shop_ID = %s", (shop_ID,))
            category_data = cursor.fetchone()

            if category_data:
                # Update category_name if shop_ID exists
                session["category_name"] = category_data[0]
                cursor.execute("UPDATE category SET category_name = %s WHERE shop_ID = %s", (session["category_name"], shop_ID))
                connection.commit()
            else:
                # Insert new record if shop_ID does not exist
                session["category_name"] = ""
                cursor.execute("INSERT INTO category (shop_ID, category_name) VALUES (%s, %s)", (shop_ID, session["category_name"]))
                connection.commit()

        # Check if category_data is not None and contains at least one element
        if category_data and category_data[0]:
            category_names = [tag.strip() for tag in category_data[0].split(',')]  # Remove leading and trailing spaces from each category
            category_names.sort(key=lambda x: x.split()[0].lower())  # Sort categories based on the first word of each category
            sorted_category_names = ', '.join(category_names)
            session["category_name"] = sorted_category_names
    return render_template("level2/Print_Servicing___Register__3.html")

@app.route('/save_form_data_shop', methods=['POST'])
def save_form_data_input():
    data = request.get_json()
    description = data.get('description')
    tags = data.get('tags')
    tags_list = [tag.strip() for tag in tags.split(',')]
    tags_list.sort(key=lambda x: x.split()[0].lower())
    sorted_tags_str = ','.join(tags_list)
    user_ID = session.get("user_ID")

    # Connect to the database
    db = get_db_connection()
    cursor = db.cursor()

    # Retrieve shop_ID associated with the user_ID
    cursor.execute("SELECT shop_ID FROM printingshops WHERE user_ID = %s", (user_ID,))
    shop_data = cursor.fetchone()

    if shop_data:
        shop_ID = shop_data[0]
        # Update 'Description' in 'printingshops' table
        cursor.execute("UPDATE printingshops SET Description = %s WHERE user_ID = %s", (description, user_ID))
    else:
        # If no shop found, insert a new row into the printingshops table
        cursor.execute("INSERT INTO printingshops (user_ID, Description) VALUES (%s, %s)", (user_ID, description))
        db.commit()  # Commit the transaction to get the auto-generated shop_ID
        shop_ID = cursor.lastrowid

    # Check if category exists for the shop_ID
    cursor.execute("SELECT * FROM category WHERE shop_ID = %s", (shop_ID,))
    category_data = cursor.fetchone()

    if category_data:
        # Update the category_name column with the new set of tags
        cursor.execute("UPDATE category SET category_name = %s WHERE shop_ID = %s", (sorted_tags_str, shop_ID))
        db.commit()  # Commit the changes
    else:
        # Insert a new category record for the shop_ID
        cursor.execute("INSERT INTO category (shop_ID, category_name) VALUES (%s, %s)", (shop_ID, sorted_tags_str))
        db.commit()  # Commit the changes

    cursor.close()
    db.close()

    return {"message": "Form data saved successfully"}, 200

@app.route("/shop/register_submitted")
def shop_register_submitted():
    return render_template("level2/Print_Servicing___Register__4.html")

@app.route("/shop/info")
def shop_info():
    if request.method == "GET":
        user_id = session.get('user_ID')

        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM printingshops WHERE user_ID = %s", (user_id,))
        new_shop_data = cursor.fetchone()

        if new_shop_data:
            session["shop_ID"] = new_shop_data[0]
            session["Shop_Name"] = new_shop_data[2]
            session["Shop_Address"] = new_shop_data[3]
            session["Detail_Address"] = new_shop_data[4]
            session["Postal_Code"] = new_shop_data[5]
            session["Number"] = new_shop_data[6]
            session['Description'] = new_shop_data[7].replace('&#34;', '"')

    return render_template("level2/Manage_Shop___Shop_Info.html", new_shop_data=new_shop_data   )

@app.route("/shop/profile_picture", methods=["POST"])
def upload_profile_picture():
    if 'image' not in request.files:
        return 'No file part'
    file = request.files['image']
    if file.filename == '':
        return 'No selected file'
    if file:
        # Construct the path to the static directory
        static_dir = app.static_folder
        profile_pictures_dir = os.path.join(static_dir, 'User_Profiles')

        # Ensure the Profile_Pictures directory exists
        if not os.path.exists(profile_pictures_dir):
            os.makedirs(profile_pictures_dir)

        # Save the file to the Profile_Pictures directory
        file_path = os.path.join(profile_pictures_dir, file.filename)
        file.save(file_path)

        # Return the URL of the uploaded file
        return url_for('static', filename='User_Profiles/' + file.filename)

@app.route("/shop/printing_services")
def shop_printing_services():
    return render_template("level2/Manage_Shop___Printing_Services.html")

@app.route("/shop/reviews")
def shop_review():
    return render_template("level2/Manage_Shop___Reviews.html")

@app.route("/shop/orders", methods=["GET", "POST"])
def shop_orders():
    return render_template("level2/Manage_Shop___Orders.html")