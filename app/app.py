from flask import Flask
from flask import render_template, request, redirect, url_for
from flask import jsonify
from datetime import datetime, timedelta
import mysql.connector
import smtplib
from email.mime.text import MIMEText

app = Flask(__name__)

# SGBD configs
DB_HOST="localhost"
DB_USER="root"
DB_DATABASE="CHIP_FRIDGE"
DB_PORT = 3306
DB_PASSWORD=""
DB_CONNECTION_STRING = "host=%s dbname=%s user=%s password=%s" % (DB_HOST, DB_DATABASE, DB_USER, DB_PASSWORD)

# Query
QUERY_SELECT_PRODUCTS = "SELECT product_name, quantity, expiration_date FROM product;"
QUERY_SELECT_OLD_PRODUCTS = "SELECT product_name FROM old_product;"

FRIDGE_EMAIL = "chipthefridge@gmail.com"
EMAIL_PASSWORD = "lyuv pgnu wboz ewzj"

receiver_email = ''

def get_products():
    products = {
        "items": [],
        "quantities": [],
        "expiration_dates":[]
    }
    dbConn = None
    cursor = None

    try:
        dbConn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_DATABASE
        )
        cursor = dbConn.cursor()

        cursor.execute(QUERY_SELECT_PRODUCTS)
        rows = cursor.fetchall()

        for i in range(len(rows)):
            products['items'] += [rows[i][0]]
            products['quantities'] += [rows[i][1]]
            products['expiration_dates'] += [rows[i][2]]
            print("There's {} of {}".format(rows[i][1], rows[i][0]))
        
        return products

    except Exception as e:
        print("error: " + str(e))

    finally:
        cursor.close()
        dbConn.close()

def get_old_products():
    old_products = {
        "items": []
    }
    dbConn = None
    cursor = None

    try:
        dbConn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_DATABASE
        )
        cursor = dbConn.cursor()

        cursor.execute(QUERY_SELECT_OLD_PRODUCTS)
        rows = cursor.fetchall()

        old_products['items'] = [rows[i][0] for i in range(len(rows))]
        
        return old_products

    except Exception as e:
        print("error: " + str(e))

    finally:
        cursor.close()
        dbConn.close()


@app.route('/')
def home():
    shopping_list, notifications = fetch_data()
    return render_template('home.html', shopping_list=shopping_list, notifications=notifications)

@app.route('/data')
def fetch_data():
    products = get_products()
    shopping_list = create_shopping_list(products, get_old_products())
    notifications = fetch_notifications(products)
    return shopping_list, notifications
        
@app.route('/fetch_fridge_data')
def fetch_fridge_data():
    fridge_data = {
        "items": [],
        "quantities": []
    }

    dict_products = {}
    
    products = get_products()

    for i in range(len(products["items"])):
        if products["items"][i] not in dict_products:
            dict_products[products["items"][i]] = products["quantities"][i]
        else:
            dict_products[products["items"][i]] += products["quantities"][i]
    
    fridge_data['items'] = list(dict_products.keys())
    fridge_data['quantities'] = list(dict_products.values())
        
    return jsonify(fridge_data)

@app.route('/fetch_notifications')
def fetch_notifications(products):
        
    notifications = {
        "expiration_dates": [],
        "messages": []
    }
    
    for i in range(len(products["items"])):
        product_name = products["items"][i]
        quantity = products["quantities"][i]
        expiration_date = products["expiration_dates"][i]
        
        product_date = expiration_date
        if product_date!=None:
            current_date = datetime.now().date()
            if current_date < product_date:
                notifications['expiration_dates'] += [product_date]
                notifications['messages'] += ["{} {} is expired".format(quantity, product_name)]
                print("{} {} is expired".format(quantity, product_name))
                
            elif current_date - product_date <= timedelta(days=2):
                notifications['expiration_date'] += [product_date]
                notifications['message'] += ["{} {} is about to expire".format(quantity, product_name)]
                print("{} {} is expired".format(quantity, product_name))
            
    return notifications

def send_email(subject, message):
    # Email credentials
    msg = MIMEText(message)
    msg['Subject'] = subject
    msg['From'] = FRIDGE_EMAIL
    msg['To'] = receiver_email
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp_server:
       smtp_server.login(FRIDGE_EMAIL, EMAIL_PASSWORD)
       smtp_server.sendmail(FRIDGE_EMAIL, receiver_email, msg.as_string())
    print("Message sent!")
    
def create_shopping_list(products, old_products):
    dict_products = {}
    for i in range(len(products["items"])):
        if products["items"][i] not in dict_products:
            dict_products[products["items"][i]] = products["quantities"][i]
        else:
            dict_products[products["items"][i]] += products["quantities"][i]
            
    shopping_list = []
    for key in dict_products:
        if dict_products[key] < 2 and key != "unknown":
            shopping_list += [key]

    shopping_list += old_products["items"]
    
    return shopping_list

@app.route('/send_shopping_list')
def send_shopping_list():
    shopping_list = create_shopping_list(products=get_products(), old_products=get_old_products())
    subject = "Shopping List"
    message = ""
    for item in shopping_list:
        message += "- " + item + "\n"
    
    send_email(subject, message)
    return jsonify({'message': 'Shopping List sent successfully!'})

if __name__ == '__main__':
    # request email
    receiver_email = input("Please enter your email address: ")
    app.run(debug=False)