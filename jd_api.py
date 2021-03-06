from flask import Flask, request, render_template, url_for, redirect
from flask_restful import Resource, Api
from flask_mail import Mail, Message  # used for email
# used for serializer email and error handling
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadTimeSignature
from flask_cors import CORS

from werkzeug.exceptions import BadRequest, NotFound

from dateutil.relativedelta import *
from decimal import Decimal
from datetime import datetime, date, timedelta
from hashlib import sha512
from math import ceil
# from google.oauth2 import id_token
# from google.auth.transport import requests as reqs

import string
import decimal
import sys
import json
import pymysql
import requests
import jwt
import traceback
import os
import boto3

from solution import *
from bing_api import *
from kmeans import Kmeans
import pandas as pd
import numpy as np
from shapely.geometry import Point
from shapely.geometry.polygon import Polygon


RDS_HOST = 'io-mysqldb8.cxjnrciilyjq.us-west-1.rds.amazonaws.com'
#RDS_HOST = 'localhost'
RDS_PORT = 3306
#RDS_USER = 'root'
RDS_USER = 'admin'
RDS_DB = 'sf'

ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg'])

app = Flask(__name__)

# Allow cross-origin resource sharing
cors = CORS(app, resources={r'/api/*': {'origins': '*'}})

# Set this to false when deploying to live application
app.config['DEBUG'] = True

# Adding for email testing
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = 'fthtesting@gmail.com'
app.config['MAIL_PASSWORD'] = 'infiniteoptions0422'
app.config['MAIL_DEFAULT_SENDER'] = 'fthtesting@gmail.com'
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
# app.config['MAIL_DEBUG'] = True
# app.config['MAIL_SUPPRESS_SEND'] = False
# app.config['TESTING'] = False

mail = Mail(app)
s = URLSafeTimedSerializer('thisisaverysecretkey')
# API
api = Api(app)

s3 = boto3.client('s3')
# Get RDS password from command line argument
isDebug = False
NOTIFICATION_HUB_KEY = os.environ.get('NOTIFICATION_HUB_KEY')
NOTIFICATION_HUB_NAME = os.environ.get('NOTIFICATION_HUB_NAME')

def RdsPw():
    if len(sys.argv) == 2:
        return str(sys.argv[1])
    return ""


# RDS PASSWORD
# When deploying to Zappa, set RDS_PW equal to the password as a string
# When pushing to GitHub, set RDS_PW equal to RdsPw()
RDS_PW = 'prashant'
# RDS_PW = RdsPw()


def getToday(): return datetime.strftime(date.today(), "%Y-%m-%d")
def getNow(): return datetime.strftime(datetime.now(), "%Y-%m-%d %H:%M:%S")

# Connect to RDS


def getRdsConn(RDS_PW):
    global RDS_HOST
    global RDS_PORT
    global RDS_USER
    global RDS_DB

    print("Trying to connect to RDS...")
    try:
        conn = pymysql.connect(RDS_HOST,
                               user=RDS_USER,
                               port=RDS_PORT,
                               passwd=RDS_PW,
                               db=RDS_DB)
        cur = conn.cursor()
        print("Successfully connected to RDS.")
        return [conn, cur]
    except:
        print("Could not connect to RDS.")
        raise Exception("RDS Connection failed.")

# Connect to MySQL database (API v2)


def connect():
    global RDS_PW
    global RDS_HOST
    global RDS_PORT
    global RDS_USER
    global RDS_DB

    print("Trying to connect to RDS (API v2)...")
    try:
        conn = pymysql.connect(host=RDS_HOST,
                               user=RDS_USER,
                               port=RDS_PORT,
                               passwd=RDS_PW,
                               db=RDS_DB,
                               cursorclass=pymysql.cursors.DictCursor)
        print("Successfully connected to RDS. (API v2)")
        return conn
    except:
        print("Could not connect to RDS. (API v2)")
        raise Exception("RDS Connection failed. (API v2)")

# Disconnect from MySQL database (API v2)


def disconnect(conn):
    try:
        conn.close()
        print("Successfully disconnected from MySQL database. (API v2)")
    except:
        print("Could not properly disconnect from MySQL database. (API v2)")
        raise Exception("Failure disconnecting from MySQL database. (API v2)")

# Serialize JSON


def serializeResponse(response):
    try:
        for row in response:
            for key in row:
                if type(row[key]) is Decimal:
                    row[key] = float(row[key])
                elif type(row[key]) is date or type(row[key]) is datetime:
                    row[key] = row[key].strftime("%Y-%m-%d")
        return response
    except:
        raise Exception("Bad query JSON")

# Execute an SQL command (API v2)
# Set cmd parameter to 'get' or 'post'
# Set conn parameter to connection object
# OPTIONAL: Set skipSerialization to True to skip default JSON response serialization


def execute(sql, cmd, conn, skipSerialization=False):
    response = {}
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            if cmd is 'get':
                result = cur.fetchall()
                response['message'] = 'Successfully executed SQL query.'
                # Return status code of 280 for successful GET request
                response['code'] = 280
                if not skipSerialization:
                    result = serializeResponse(result)
                response['result'] = result
            elif cmd in 'post':
                conn.commit()
                response['message'] = 'Successfully committed SQL command.'
                # Return status code of 281 for successful POST request
                response['code'] = 281
            else:
                response['message'] = 'Request failed. Unknown or ambiguous instruction given for MySQL command.'
                # Return status code of 480 for unknown HTTP method
                response['code'] = 480
    except:
        response['message'] = 'Request failed, could not execute MySQL command.'
        # Return status code of 490 for unsuccessful HTTP request
        response['code'] = 490
    finally:
        response['sql'] = sql
        return response

# Close RDS connection


def closeRdsConn(cur, conn):
    try:
        cur.close()
        conn.close()
        print("Successfully closed RDS connection.")
    except:
        print("Could not close RDS connection.")

# Runs a select query with the SQL query string and pymysql cursor as arguments
# Returns a list of Python tuples


def runSelectQuery(query, cur):
    try:
        cur.execute(query)
        queriedData = cur.fetchall()
        return queriedData
    except:
        raise Exception("Could not run select query and/or return data")

def allowed_file(filename):
    """Checks if the file is allowed to upload"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def helper_upload_img(file, key):
    bucket = 'just-delivered'
    
    filename = 'https://s3-us-west-1.amazonaws.com/' \
                + str(bucket) + '/' + str(key)
    print(filename)
    upload_file = s3.put_object(
                        Bucket=bucket,
                        Body=file,
                        Key=key,
                        ACL='public-read',
                        ContentType='image/jpeg'
                    )
    return filename
    

# -- Queries start here -------------------------------------------------------------------------------
class SignUp(Resource):
    def post(self):
        response = {}
        items = []
        try:
            conn = connect()
            #missing driver uid in carlos' input
            first_name = request.form.get('first_name') if request.form.get('first_name') is not None else 'NULL'
            last_name = request.form.get('last_name') if request.form.get('last_name') is not None else 'NULL'
            business_uid = request.form.get('business_uid') if request.form.get('business_uid') is not None else 'NULL'
            referral_source = request.form.get('referral_source') if request.form.get('referral_source') is not None else 'NULL'
            driver_hours = request.form.get('driver_hours') if request.form.get('driver_hours') is not None else '[]'
            street = request.form.get('street') if request.form.get('street') is not None else 'NULL'
            unit = request.form.get('unit') if request.form.get('unit') is not None else 'NULL'
            city = request.form.get('city') if request.form.get('city') is not None else 'NULL'
            state = request.form.get('state') if request.form.get('state') is not None else 'NULL'
            zipcode = request.form.get('zipcode') if request.form.get('zipcode') is not None else 'NULL'
            longitude = request.form.get('longitude') if request.form.get('longitude') is not None else 'NULL'
            latitude = request.form.get('latitude') if request.form.get('latitude') is not None else 'NULL'
            email = request.form.get('email') if request.form.get('email') is not None else 'NULL'
            phone = request.form.get('phone') if request.form.get('phone') is not None else 'NULL'
            ssn = request.form.get('ssn') if request.form.get('ssn') is not None else 'NULL'
            license_num = request.form.get('license_num') if request.form.get('license_num') is not None else 'NULL'
            license_exp = request.form.get('license_exp') if request.form.get('license_exp') is not None else 'NULL'
            driver_car_year = request.form.get('driver_car_year') if request.form.get('driver_car_year') is not None else 'NULL'
            driver_car_model = request.form.get('driver_car_model') if request.form.get('driver_car_model') is not None else 'NULL'
            driver_car_make = request.form.get('driver_car_make') if request.form.get('driver_car_make') is not None else 'NULL'
            driver_insurance_carrier = request.form.get('driver_insurance_carrier') if request.form.get('driver_insurance_carrier') is not None else 'NULL'
            driver_insurance_num = request.form.get('driver_insurance_num') if request.form.get('driver_insurance_num') is not None else 'NULL'
            driver_insurance_exp_date = request.form.get('driver_insurance_exp_date') if request.form.get('driver_insurance_exp_date') is not None else 'NULL'
            driver_insurance_picture = request.files.get('driver_insurance_picture') if request.files.get('driver_insurance_picture') is not None else 'NULL'
            contact_name = request.form.get('contact_name') if request.form.get('contact_name') is not None else 'NULL'
            contact_phone = request.form.get('contact_phone') if request.form.get('contact_phone') is not None else 'NULL'
            contact_relation = request.form.get('contact_relation') if request.form.get('contact_relation') is not None else 'NULL'
            bank_acc_info = request.form.get('bank_acc_info') if request.form.get('bank_acc_info') is not None else 'NULL'
            bank_routing_info = request.form.get('bank_routing_info') if request.form.get('bank_routing_info') is not None else 'NULL'
            password = request.form.get('password') if request.form.get('password') is not None else 'NULL'
            driver_uid = request.form.get('driver_uid') if request.form.get('driver_uid') is not None else 'NULL'
            social_id = request.form.get('social_id') if request.form.get('social_id') is not None else 'NULL'

            print('part 1 done',first_name,last_name,email,password)
            if request.form.get('social') is None or request.form.get('social') == "FALSE" or request.form.get('social') == False or request.form.get('social') == "NULL":
                social_signup = False
                print('Part 1.1')
            else:
                social_signup = True
            
            print('part 2 done')
            get_driver_id_query = "CALL jd.get_driver_id();"
            NewUserIDresponse = execute(get_driver_id_query, 'get', conn)
            #print(NewUserIDresponse)
            if NewUserIDresponse['code'] == 490:
                string = " Cannot get new driver id. "
                print("*" * (len(string) + 10))
                print(string.center(len(string) + 10, "*"))
                print("*" * (len(string) + 10))
                response['message'] = "Internal Server Error."
                return response, 500
            NewUserID = NewUserIDresponse['result'][0]['new_id']
            
            # upload image to s3
            print("initial",driver_insurance_picture)
            if driver_insurance_picture != 'NULL':
                key = "driver_insurance/" + str(NewUserID) + "_" + datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
                print(key)
                driver_insurance_picture = helper_upload_img(driver_insurance_picture, key)
            print("driver pic",driver_insurance_picture)


            if social_signup == False:

                salt = (datetime.now()).strftime("%Y-%m-%d %H:%M:%S")
                print("in")
                password = sha512((password + salt).encode()).hexdigest()
                print('password------', password)
                algorithm = "SHA512"
                mobile_access_token = 'NULL'
                mobile_refresh_token = 'NULL'
                user_access_token = 'NULL'
                user_refresh_token = 'NULL'
                user_social_signup = 'NULL'
            else:

                mobile_access_token = request.form.get('mobile_access_token')
                mobile_refresh_token = request.form.get('mobile_refresh_token')
                user_access_token = request.form.get('user_access_token')
                user_refresh_token = request.form.get('user_refresh_token')
                salt = 'NULL'   
                password = 'NULL'
                algorithm = 'NULL'
                user_social_signup = request.form.get('social')
            
            if driver_uid != 'NULL' and driver_uid:
                print("IN IF")
                NewUserID = driver_uid 

                query = '''
                            SELECT user_access_token, user_refresh_token,mobile_access_token,mobile_refresh_token
                            FROM jd.drivers 
                            WHERE driver_uid = \'''' + driver_uid + '''\';
                       '''
                it = execute(query, 'get', conn)
                if it['result'] == ():
                    return "driver does not exists"
                print('query executed')
                print('it-------', it)

                if it['result'][0]['user_access_token'] != 'FALSE':
                    user_access_token = it['result'][0]['user_access_token']

                if it['result'][0]['user_refresh_token'] != 'FALSE':
                    user_refresh_token = it['result'][0]['user_refresh_token']

                if it['result'][0]['mobile_access_token'] != 'FALSE':
                    mobile_access_token = it['result'][0]['mobile_access_token']

                if it['result'][0]['mobile_refresh_token'] != 'FALSE':
                    mobile_refresh_token = it['result'][0]['mobile_refresh_token']


                driver_insert_query =  '''
                                    UPDATE jd.drivers
                                    SET 
                                    driver_created_at = \'''' + (datetime.now()).strftime("%Y-%m-%d %H:%M:%S") + '''\',
                                    driver_first_name = \'''' + first_name + '''\',
                                    driver_last_name = \'''' + last_name + '''\',
                                    business_id = \'''' + business_uid + '''\',
                                    referral_source = \'''' + referral_source + '''\',
                                    driver_available_hours = \'''' + driver_hours + '''\',
                                    driver_street = \'''' + street + '''\',
                                    driver_unit = \'''' + unit + '''\',
                                    driver_city = \'''' + city + '''\',
                                    driver_state = \'''' + state + '''\',
                                    driver_zip = \'''' + zipcode + '''\',
                                    driver_latitude = \'''' + latitude + '''\',
                                    driver_longitude = \'''' + longitude + '''\',
                                    driver_phone_num = \'''' + phone + '''\',
                                    driver_email = \'''' + email + '''\',
                                    driver_ssn = \'''' + ssn + '''\',
                                    driver_license = \'''' + license_num + '''\',
                                    driver_license_exp = \'''' + license_exp + '''\',
                                    driver_car_year = \'''' + driver_car_year + '''\',
                                    driver_car_model = \'''' + driver_car_model + '''\',
                                    driver_car_make = \'''' + driver_car_make + '''\',
                                    driver_insurance_carrier = \'''' + driver_insurance_carrier + '''\',
                                    driver_insurance_num = \'''' + driver_insurance_num + '''\',
                                    driver_insurance_exp_date = \'''' + driver_insurance_exp_date + '''\',
                                    driver_insurance_picture = \'''' + driver_insurance_picture + '''\',
                                    emergency_contact_name = \'''' + contact_name + '''\',
                                    emergency_contact_phone = \'''' + contact_phone + '''\',
                                    emergency_contact_relationship = \'''' + contact_relation + '''\',
                                    bank_account_info = \'''' + bank_acc_info + '''\',
                                    bank_routing_info = \'''' + bank_routing_info + '''\',
                                    password_salt = \'''' + salt + '''\',
                                    password_hashed = \'''' + password + '''\',
                                    password_algorithm = \'''' + algorithm + '''\',
                                    user_social_media = \'''' + user_social_signup + '''\',
                                    user_access_token = \'''' + user_access_token + '''\',
                                    social_timestamp = DATE_ADD(now() , INTERVAL 14 DAY),
                                    user_refresh_token = \'''' + user_refresh_token + '''\',
                                    mobile_access_token = \'''' + mobile_access_token + '''\',
                                    mobile_refresh_token = \'''' + mobile_refresh_token + '''\',
                                    social_id = \'''' + social_id + '''\'
                                    WHERE driver_uid = \'''' + driver_uid + '''\';
                                    ''' 


            else:

                # check if there is a same driver_id existing
                query = """
                        SELECT driver_email FROM jd.drivers
                        WHERE driver_email = \'""" + email + "\';"
                print('email---------' + email)
                items = execute(query, 'get', conn)
                if items['result']:

                    items['result'] = ""
                    items['code'] = 409
                    items['message'] = "Email address has already been taken."

                    return items

                if items['code'] == 480:

                    items['result'] = ""
                    items['code'] = 480
                    items['message'] = "Internal Server Error."
                    return items

                print("inserting to db")
                print(license_num,license_exp)
                # write everything to database

                driver_insert_query =  '''
                                    INSERT INTO jd.drivers
                                    SET 
                                    driver_uid = \'''' + NewUserID + '''\',
                                    driver_created_at = \'''' + (datetime.now()).strftime("%Y-%m-%d %H:%M:%S") + '''\',
                                    driver_first_name = \'''' + first_name + '''\',
                                    driver_last_name = \'''' + last_name + '''\',
                                    business_id = \'''' + business_uid + '''\',
                                    referral_source = \'''' + referral_source + '''\',
                                    driver_available_hours = \'''' + driver_hours + '''\',
                                    driver_street = \'''' + street + '''\',
                                    driver_unit = \'''' + unit + '''\',
                                    driver_city = \'''' + city + '''\',
                                    driver_state = \'''' + state + '''\',
                                    driver_zip = \'''' + zipcode + '''\',
                                    driver_latitude = \'''' + latitude + '''\',
                                    driver_longitude = \'''' + longitude + '''\',
                                    driver_phone_num = \'''' + phone + '''\',
                                    driver_email = \'''' + email + '''\',
                                    driver_ssn = \'''' + ssn + '''\',
                                    driver_license = \'''' + license_num + '''\',
                                    driver_license_exp = \'''' + license_exp + '''\',
                                    driver_car_year = \'''' + driver_car_year + '''\',
                                    driver_car_model = \'''' + driver_car_model + '''\',
                                    driver_car_make = \'''' + driver_car_make + '''\',
                                    driver_insurance_carrier = \'''' + driver_insurance_carrier + '''\',
                                    driver_insurance_num = \'''' + driver_insurance_num + '''\',
                                    driver_insurance_exp_date = \'''' + driver_insurance_exp_date + '''\',
                                    driver_insurance_picture = \'''' + driver_insurance_picture + '''\',
                                    emergency_contact_name = \'''' + contact_name + '''\',
                                    emergency_contact_phone = \'''' + contact_phone + '''\',
                                    emergency_contact_relationship = \'''' + contact_relation + '''\',
                                    bank_account_info = \'''' + bank_acc_info + '''\',
                                    bank_routing_info = \'''' + bank_routing_info + '''\',
                                    password_salt = \'''' + salt + '''\',
                                    password_hashed = \'''' + password + '''\',
                                    password_algorithm = \'''' + algorithm + '''\',
                                    user_social_media = \'''' + user_social_signup + '''\',
                                    user_access_token = \'''' + user_access_token + '''\',
                                    social_timestamp = DATE_ADD(now() , INTERVAL 14 DAY),
                                    user_refresh_token = \'''' + user_refresh_token + '''\',
                                    mobile_access_token = \'''' + mobile_access_token + '''\',
                                    mobile_refresh_token = \'''' + mobile_refresh_token + '''\',
                                    social_id = \'''' + social_id + '''\';
                                    ''' 

            
            print(driver_insert_query)
            
            items = execute(driver_insert_query, 'post', conn)
            print(items)
            if items['code'] != 281:
                items['result'] = ""
                items['code'] = 480
                items['message'] = "Error while inserting values in database"

                return items


            items['result'] = {
                'first_name': first_name,
                'last_name': last_name,
                'driver_uid': NewUserID,
                'access_token': user_access_token,
                'refresh_token': user_refresh_token
            }
            items['message'] = 'Signup successful'
            items['code'] = 200


            return items
        except:
            print("Error happened while Sign Up")
            if "NewUserID" in locals():
                execute("""DELETE FROM users WHERE user_uid = '""" + NewUserID + """';""", 'post', conn)
            raise BadRequest('Request failed, please try again later.')
        finally:
            disconnect(conn)

# {
#     "first_name":"test",
#     "last_name":"ing",
#     "business_uid":"tesing uid",
#     "driver_hours":"{\"Friday\": [\"09:00:00\", \"23:59:59\"], \"Monday\": [\"09:00:00\", \"23:59:59\"], \"Sunday\": [\"09:00:00\", \"23:59:59\"], \"Tuesday\": [\"09:00:00\", \"23:59:59\"], \"Saturday\": [\"09:00:00\", \"21:00:00\"], \"Thursday\": [\"09:00:00\", \"23:59:59\"], \"Wednesday\": [\"09:00:00\", \"23:00:00\"]}",
#     "street":"123 testing",
#     "city":"testing",
#     "state":"test",
#     "zipcode":"test",
#     "email":"test12334123123@test.com",
#     "phone":"1923812903",
#     "ssn":"1823918301289",
#     "license_num":"8123918901389201",
#     "license_exp":"128938102039",
#     "insurance":"18239020189",
#     "contact_name":"test",
#     "contact_phone":"12312312",
#     "contact_relation":"testing",
#     "bank_acc_info":"1293808129",
#     "bank_routing_info":"29183091",
#     "password":"xyz123",
#     "mobile_access_token" : "FALSE",
#     "mobile_refresh_token" : "FALSE",
#     "user_access_token" : "FALSE",
#     "user_refresh_token" : "FALSE",
#     "social_id": "NULL",
#     "social" : "NULL"
# }












# confirmation page
@app.route('/api/v2/confirm', methods=['GET'])
def confirm():
    try:
        token = request.args['token']
        hashed = request.args['hashed']
        print("hased: ", hashed)
        email = s.loads(token)  # max_age = 86400 = 1 day

        # marking email confirmed in database, then...
        conn = connect()
        query = """UPDATE jd.drivers SET email_verified = 1 WHERE driver_email = \'""" + email + """\';"""
        update = execute(query, 'post', conn)
        if update.get('code') == 281:
            # redirect to login page
            # only for testing on localhost
            return redirect('http://localhost:4000/login?email={}&hashed={}'.format(email, hashed))
            #return redirect('https://infinitebooks.me/login?email={}&hashed={}'.format(email, hashed))
        else:
            print("Error happened while confirming an email address.")
            error = "Confirm error."
            err_code = 401  # Verification code is incorrect
            return error, err_code
    except (SignatureExpired, BadTimeSignature) as err:
        status = 403  # forbidden
        return str(err), status
    finally:
        disconnect(conn)

class AccountSalt(Resource):
    def post(self):
        response = {}
        try:
            conn = connect()

            data = request.get_json(force=True)
            print(data)
            email = data['email']
            query = """
                    SELECT password_algorithm, 
                            password_salt 
                    FROM jd.drivers
                    WHERE driver_email = \'""" + email + """\';
                    """
            items = execute(query, 'get', conn)
            if not items['result']:
                items['message'] = "Email doesn't exists"
                items['code'] = 404
            return items
            items['message'] = 'SALT sent successfully'
            items['code'] = 200
            return items
        except:
            raise BadRequest('Request failed, please try again later.')
        finally:
            disconnect(conn)

# {
#     "email":"test12334@test.com"
# }


class UpdateSocialProfile(Resource):
    def post(self):
        response = {}
        items = []
        try:
            conn = connect()
            #missing driver uid in carlos' input
            # first_name = request.form.get('first_name') if request.form.get('first_name') is not None else 'NULL'
            # last_name = request.form.get('last_name') if request.form.get('last_name') is not None else 'NULL'
            business_uid = request.form.get('business_uid') if request.form.get('business_uid') is not None else 'NULL'
            referral_source = request.form.get('referral_source') if request.form.get('referral_source') is not None else 'NULL'
            driver_hours = request.form.get('driver_hours') if request.form.get('driver_hours') is not None else '[]'
            street = request.form.get('street') if request.form.get('street') is not None else 'NULL'
            unit = request.form.get('unit') if request.form.get('unit') is not None else 'NULL'
            city = request.form.get('city') if request.form.get('city') is not None else 'NULL'
            state = request.form.get('state') if request.form.get('state') is not None else 'NULL'
            zipcode = request.form.get('zipcode') if request.form.get('zipcode') is not None else 'NULL'
            longitude = request.form.get('longitude') if request.form.get('longitude') is not None else 'NULL'
            latitude = request.form.get('latitude') if request.form.get('latitude') is not None else 'NULL'
            # email = request.form.get('email') if request.form.get('email') is not None else 'NULL'
            phone = request.form.get('phone') if request.form.get('phone') is not None else 'NULL'
            ssn = request.form.get('ssn') if request.form.get('ssn') is not None else 'NULL'
            license_num = request.form.get('license_num') if request.form.get('license_num') is not None else 'NULL'
            license_exp = request.form.get('license_exp') if request.form.get('license_exp') is not None else 'NULL'
            driver_car_year = request.form.get('driver_car_year') if request.form.get('driver_car_year') is not None else 'NULL'
            driver_car_model = request.form.get('driver_car_model') if request.form.get('driver_car_model') is not None else 'NULL'
            driver_car_make = request.form.get('driver_car_make') if request.form.get('driver_car_make') is not None else 'NULL'
            driver_insurance_carrier = request.form.get('driver_insurance_carrier') if request.form.get('driver_insurance_carrier') is not None else 'NULL'
            driver_insurance_num = request.form.get('driver_insurance_num') if request.form.get('driver_insurance_num') is not None else 'NULL'
            driver_insurance_exp_date = request.form.get('driver_insurance_exp_date') if request.form.get('driver_insurance_exp_date') is not None else 'NULL'
            driver_insurance_picture = request.files.get('driver_insurance_picture') if request.files.get('driver_insurance_picture') is not None else 'NULL'
            contact_name = request.form.get('contact_name') if request.form.get('contact_name') is not None else 'NULL'
            contact_phone = request.form.get('contact_phone') if request.form.get('contact_phone') is not None else 'NULL'
            contact_relation = request.form.get('contact_relation') if request.form.get('contact_relation') is not None else 'NULL'
            bank_acc_info = request.form.get('bank_acc_info') if request.form.get('bank_acc_info') is not None else 'NULL'
            bank_routing_info = request.form.get('bank_routing_info') if request.form.get('bank_routing_info') is not None else 'NULL'
            # password = request.form.get('password') if request.form.get('password') is not None else 'NULL'
            driver_uid = request.form.get('driver_uid') if request.form.get('driver_uid') is not None else 'NULL'
            # social_id = request.form.get('social_id') if request.form.get('social_id') is not None else 'NULL'

            # print('part 1 done',first_name,last_name,email,password)
            # if request.form.get('social') is None or request.form.get('social') == "FALSE" or request.form.get('social') == False or request.form.get('social') == "NULL":
            #     social_signup = False
            #     print('Part 1.1')
            # else:
            #   social_signup = True
            
            # print('part 2 done')
            # get_driver_id_query = "CALL jd.get_driver_id();"
            # NewUserIDresponse = execute(get_driver_id_query, 'get', conn)
            # #print(NewUserIDresponse)
            # if NewUserIDresponse['code'] == 490:
            #     string = " Cannot get new driver id. "
            #     print("*" * (len(string) + 10))
            #     print(string.center(len(string) + 10, "*"))
            #     print("*" * (len(string) + 10))
            #     response['message'] = "Internal Server Error."
            #     return response, 500
            # NewUserID = NewUserIDresponse['result'][0]['new_id']
            
            # upload image to s3
            print("initial",driver_insurance_picture)
            if driver_insurance_picture != 'NULL':
                key = "driver_insurance/" + str(driver_uid) + "_" + datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
                print(key)
                driver_insurance_picture = helper_upload_img(driver_insurance_picture, key)
            print("driver pic",driver_insurance_picture)


            # if social_signup == False:

            #     salt = (datetime.now()).strftime("%Y-%m-%d %H:%M:%S")
            #     print("in")
            #     password = sha512((password + salt).encode()).hexdigest()
            #     print('password------', password)
            #     algorithm = "SHA512"
            #     mobile_access_token = 'NULL'
            #     mobile_refresh_token = 'NULL'
            #     user_access_token = 'NULL'
            #     user_refresh_token = 'NULL'
            #     user_social_signup = 'NULL'
            # else:

            #     mobile_access_token = request.form.get('mobile_access_token')
            #     mobile_refresh_token = request.form.get('mobile_refresh_token')
            #     user_access_token = request.form.get('user_access_token')
            #     user_refresh_token = request.form.get('user_refresh_token')
            #     salt = 'NULL'   
            #     password = 'NULL'
            #     algorithm = 'NULL'
            #     user_social_signup = request.form.get('social')
            
            # if driver_uid != 'NULL' and driver_uid:
            #     print("IN IF")
            #     NewUserID = driver_uid 

            #     query = '''
            #                 SELECT user_access_token, user_refresh_token,mobile_access_token,mobile_refresh_token
            #                 FROM jd.drivers 
            #                 WHERE driver_uid = \'''' + driver_uid + '''\';
            #            '''
            #     it = execute(query, 'get', conn)
            #     if it['result'] == ():
            #         return "driver does not exists"
            #     print('query executed')
            #     print('it-------', it)

            #     if it['result'][0]['user_access_token'] != 'FALSE':
            #         user_access_token = it['result'][0]['user_access_token']

            #     if it['result'][0]['user_refresh_token'] != 'FALSE':
            #         user_refresh_token = it['result'][0]['user_refresh_token']

            #     if it['result'][0]['mobile_access_token'] != 'FALSE':
            #         mobile_access_token = it['result'][0]['mobile_access_token']

            #     if it['result'][0]['mobile_refresh_token'] != 'FALSE':
            #         mobile_refresh_token = it['result'][0]['mobile_refresh_token']


            driver_insert_query =  '''
                                UPDATE jd.drivers
                                SET 
                                driver_created_at = \'''' + (datetime.now()).strftime("%Y-%m-%d %H:%M:%S") + '''\',
                                business_id = \'''' + business_uid + '''\',
                                driver_street = \'''' + street + '''\',
                                driver_unit = \'''' + unit + '''\',
                                driver_city = \'''' + city + '''\',
                                driver_state = \'''' + state + '''\',
                                driver_zip = \'''' + zipcode + '''\',
                                driver_latitude = \'''' + latitude + '''\',
                                driver_longitude = \'''' + longitude + '''\',
                                driver_phone_num = \'''' + phone + '''\',
                                driver_ssn = \'''' + ssn + '''\',
                                driver_license = \'''' + license_num + '''\',
                                driver_license_exp = \'''' + license_exp + '''\',
                                driver_car_year = \'''' + driver_car_year + '''\',
                                driver_car_model = \'''' + driver_car_model + '''\',
                                driver_car_make = \'''' + driver_car_make + '''\',
                                driver_insurance_carrier = \'''' + driver_insurance_carrier + '''\',
                                driver_insurance_num = \'''' + driver_insurance_num + '''\',
                                driver_insurance_exp_date = \'''' + driver_insurance_exp_date + '''\',
                                driver_insurance_picture = \'''' + driver_insurance_picture + '''\',
                                emergency_contact_name = \'''' + contact_name + '''\',
                                emergency_contact_phone = \'''' + contact_phone + '''\',
                                emergency_contact_relationship = \'''' + contact_relation + '''\',
                                bank_account_info = \'''' + bank_acc_info + '''\',
                                bank_routing_info = \'''' + bank_routing_info + '''\'
                                WHERE driver_uid = \'''' + driver_uid + '''\';
                                ''' 


            # else:

            #     # check if there is a same driver_id existing
            #     query = """
            #             SELECT driver_email FROM jd.drivers
            #             WHERE driver_email = \'""" + email + "\';"
            #     print('email---------' + email)
            #     items = execute(query, 'get', conn)
            #     if items['result']:

            #         items['result'] = ""
            #         items['code'] = 409
            #         items['message'] = "Email address has already been taken."

            #         return items

            #     if items['code'] == 480:

            #         items['result'] = ""
            #         items['code'] = 480
            #         items['message'] = "Internal Server Error."
            #         return items

            print("inserting to db")
            # print(license_num,license_exp)
                # write everything to database

                # driver_insert_query =  '''
                #                     INSERT INTO jd.drivers
                #                     SET 
                #                     driver_uid = \'''' + NewUserID + '''\',
                #                     driver_created_at = \'''' + (datetime.now()).strftime("%Y-%m-%d %H:%M:%S") + '''\',
                #                     driver_first_name = \'''' + first_name + '''\',
                #                     driver_last_name = \'''' + last_name + '''\',
                #                     business_id = \'''' + business_uid + '''\',
                #                     referral_source = \'''' + referral_source + '''\',
                #                     driver_available_hours = \'''' + driver_hours + '''\',
                #                     driver_street = \'''' + street + '''\',
                #                     driver_unit = \'''' + unit + '''\',
                #                     driver_city = \'''' + city + '''\',
                #                     driver_state = \'''' + state + '''\',
                #                     driver_zip = \'''' + zipcode + '''\',
                #                     driver_latitude = \'''' + latitude + '''\',
                #                     driver_longitude = \'''' + longitude + '''\',
                #                     driver_phone_num = \'''' + phone + '''\',
                #                     driver_email = \'''' + email + '''\',
                #                     driver_ssn = \'''' + ssn + '''\',
                #                     driver_license = \'''' + license_num + '''\',
                #                     driver_license_exp = \'''' + license_exp + '''\',
                #                     driver_car_year = \'''' + driver_car_year + '''\',
                #                     driver_car_model = \'''' + driver_car_model + '''\',
                #                     driver_car_make = \'''' + driver_car_make + '''\',
                #                     driver_insurance_carrier = \'''' + driver_insurance_carrier + '''\',
                #                     driver_insurance_num = \'''' + driver_insurance_num + '''\',
                #                     driver_insurance_exp_date = \'''' + driver_insurance_exp_date + '''\',
                #                     driver_insurance_picture = \'''' + driver_insurance_picture + '''\',
                #                     emergency_contact_name = \'''' + contact_name + '''\',
                #                     emergency_contact_phone = \'''' + contact_phone + '''\',
                #                     emergency_contact_relationship = \'''' + contact_relation + '''\',
                #                     bank_account_info = \'''' + bank_acc_info + '''\',
                #                     bank_routing_info = \'''' + bank_routing_info + '''\',
                #                     password_salt = \'''' + salt + '''\',
                #                     password_hashed = \'''' + password + '''\',
                #                     password_algorithm = \'''' + algorithm + '''\',
                #                     user_social_media = \'''' + user_social_signup + '''\',
                #                     user_access_token = \'''' + user_access_token + '''\',
                #                     social_timestamp = DATE_ADD(now() , INTERVAL 14 DAY),
                #                     user_refresh_token = \'''' + user_refresh_token + '''\',
                #                     mobile_access_token = \'''' + mobile_access_token + '''\',
                #                     mobile_refresh_token = \'''' + mobile_refresh_token + '''\',
                #                     social_id = \'''' + social_id + '''\';
                #                     ''' 

            
            print(driver_insert_query)
            
            items = execute(driver_insert_query, 'post', conn)
            print(items)
            if items['code'] != 281:
                items['result'] = ""
                items['code'] = 480
                items['message'] = "Error while inserting values in database"

                return items


            items['result'] = {
                'first_name': first_name,
                'last_name': last_name,
                'driver_uid': NewUserID,
                'access_token': user_access_token,
                'refresh_token': user_refresh_token
            }
            items['message'] = 'Signup successful'
            items['code'] = 200


            return items
        except:
            print("Error happened while Sign Up")
            # if "NewUserID" in locals():
            #     execute("""DELETE FROM users WHERE user_uid = '""" + NewUserID + """';""", 'post', conn)
            # raise BadRequest('Request failed, please try again later.')
        finally:
            disconnect(conn)




class UpdateDirectProfile(Resource):
    def post(self):
        response = {}
        items = []
        try:
            conn = connect()
            #missing driver uid in carlos' input
            first_name = request.form.get('first_name') if request.form.get('first_name') is not None else 'NULL'
            last_name = request.form.get('last_name') if request.form.get('last_name') is not None else 'NULL'
            business_uid = request.form.get('business_uid') if request.form.get('business_uid') is not None else 'NULL'
            referral_source = request.form.get('referral_source') if request.form.get('referral_source') is not None else 'NULL'
            driver_hours = request.form.get('driver_hours') if request.form.get('driver_hours') is not None else '[]'
            street = request.form.get('street') if request.form.get('street') is not None else 'NULL'
            unit = request.form.get('unit') if request.form.get('unit') is not None else 'NULL'
            city = request.form.get('city') if request.form.get('city') is not None else 'NULL'
            state = request.form.get('state') if request.form.get('state') is not None else 'NULL'
            zipcode = request.form.get('zipcode') if request.form.get('zipcode') is not None else 'NULL'
            longitude = request.form.get('longitude') if request.form.get('longitude') is not None else 'NULL'
            latitude = request.form.get('latitude') if request.form.get('latitude') is not None else 'NULL'
            # email = request.form.get('email') if request.form.get('email') is not None else 'NULL'
            phone = request.form.get('phone') if request.form.get('phone') is not None else 'NULL'
            ssn = request.form.get('ssn') if request.form.get('ssn') is not None else 'NULL'
            license_num = request.form.get('license_num') if request.form.get('license_num') is not None else 'NULL'
            license_exp = request.form.get('license_exp') if request.form.get('license_exp') is not None else 'NULL'
            driver_car_year = request.form.get('driver_car_year') if request.form.get('driver_car_year') is not None else 'NULL'
            driver_car_model = request.form.get('driver_car_model') if request.form.get('driver_car_model') is not None else 'NULL'
            driver_car_make = request.form.get('driver_car_make') if request.form.get('driver_car_make') is not None else 'NULL'
            driver_insurance_carrier = request.form.get('driver_insurance_carrier') if request.form.get('driver_insurance_carrier') is not None else 'NULL'
            driver_insurance_num = request.form.get('driver_insurance_num') if request.form.get('driver_insurance_num') is not None else 'NULL'
            driver_insurance_exp_date = request.form.get('driver_insurance_exp_date') if request.form.get('driver_insurance_exp_date') is not None else 'NULL'
            driver_insurance_picture = request.files.get('driver_insurance_picture') if request.files.get('driver_insurance_picture') is not None else 'NULL'
            contact_name = request.form.get('contact_name') if request.form.get('contact_name') is not None else 'NULL'
            contact_phone = request.form.get('contact_phone') if request.form.get('contact_phone') is not None else 'NULL'
            contact_relation = request.form.get('contact_relation') if request.form.get('contact_relation') is not None else 'NULL'
            bank_acc_info = request.form.get('bank_acc_info') if request.form.get('bank_acc_info') is not None else 'NULL'
            bank_routing_info = request.form.get('bank_routing_info') if request.form.get('bank_routing_info') is not None else 'NULL'
            # password = request.form.get('password') if request.form.get('password') is not None else 'NULL'
            driver_uid = request.form.get('driver_uid') if request.form.get('driver_uid') is not None else 'NULL'
            # social_id = request.form.get('social_id') if request.form.get('social_id') is not None else 'NULL'

            # print('part 1 done',first_name,last_name,email,password)
            # if request.form.get('social') is None or request.form.get('social') == "FALSE" or request.form.get('social') == False or request.form.get('social') == "NULL":
            #     social_signup = False
            #     print('Part 1.1')
            # else:
            #     social_signup = True
            
            # print('part 2 done')
            # get_driver_id_query = "CALL jd.get_driver_id();"
            # NewUserIDresponse = execute(get_driver_id_query, 'get', conn)
            # #print(NewUserIDresponse)
            # if NewUserIDresponse['code'] == 490:
            #     string = " Cannot get new driver id. "
            #     print("*" * (len(string) + 10))
            #     print(string.center(len(string) + 10, "*"))
            #     print("*" * (len(string) + 10))
            #     response['message'] = "Internal Server Error."
            #     return response, 500
            # NewUserID = NewUserIDresponse['result'][0]['new_id']
            
            # upload image to s3
            print("initial",driver_insurance_picture)
            if driver_insurance_picture != 'NULL':
                key = "driver_insurance/" + str(driver_uid) + "_" + datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
                print(key)
                driver_insurance_picture = helper_upload_img(driver_insurance_picture, key)
            print("driver pic",driver_insurance_picture)


            # if social_signup == False:

            #     salt = (datetime.now()).strftime("%Y-%m-%d %H:%M:%S")
            #     print("in")
            #     password = sha512((password + salt).encode()).hexdigest()
            #     print('password------', password)
            #     algorithm = "SHA512"
            #     mobile_access_token = 'NULL'
            #     mobile_refresh_token = 'NULL'
            #     user_access_token = 'NULL'
            #     user_refresh_token = 'NULL'
            #     user_social_signup = 'NULL'
            # else:

            #     mobile_access_token = request.form.get('mobile_access_token')
            #     mobile_refresh_token = request.form.get('mobile_refresh_token')
            #     user_access_token = request.form.get('user_access_token')
            #     user_refresh_token = request.form.get('user_refresh_token')
            #     salt = 'NULL'   
            #     password = 'NULL'
            #     algorithm = 'NULL'
            #     user_social_signup = request.form.get('social')
            
            # if driver_uid != 'NULL' and driver_uid:
            #     print("IN IF")
            #     NewUserID = driver_uid 

            #     query = '''
            #                 SELECT user_access_token, user_refresh_token,mobile_access_token,mobile_refresh_token
            #                 FROM jd.drivers 
            #                 WHERE driver_uid = \'''' + driver_uid + '''\';
            #            '''
            #     it = execute(query, 'get', conn)
            #     if it['result'] == ():
            #         return "driver does not exists"
            #     print('query executed')
            #     print('it-------', it)

            #     if it['result'][0]['user_access_token'] != 'FALSE':
            #         user_access_token = it['result'][0]['user_access_token']

            #     if it['result'][0]['user_refresh_token'] != 'FALSE':
            #         user_refresh_token = it['result'][0]['user_refresh_token']

            #     if it['result'][0]['mobile_access_token'] != 'FALSE':
            #         mobile_access_token = it['result'][0]['mobile_access_token']

            #     if it['result'][0]['mobile_refresh_token'] != 'FALSE':
            #         mobile_refresh_token = it['result'][0]['mobile_refresh_token']

            print("Before query")
            driver_insert_query =  '''
                                UPDATE jd.drivers
                                SET 
                                driver_created_at = \'''' + (datetime.now()).strftime("%Y-%m-%d %H:%M:%S") + '''\',
                                driver_first_name = \'''' + first_name + '''\',
                                driver_last_name = \'''' + last_name + '''\',
                                business_id = \'''' + business_uid + '''\',
                                driver_street = \'''' + street + '''\',
                                driver_unit = \'''' + unit + '''\',
                                driver_city = \'''' + city + '''\',
                                driver_state = \'''' + state + '''\',
                                driver_zip = \'''' + zipcode + '''\',
                                driver_latitude = \'''' + latitude + '''\',
                                driver_longitude = \'''' + longitude + '''\',
                                driver_phone_num = \'''' + phone + '''\',
                                driver_ssn = \'''' + ssn + '''\',
                                driver_license = \'''' + license_num + '''\',
                                driver_license_exp = \'''' + license_exp + '''\',
                                driver_car_year = \'''' + driver_car_year + '''\',
                                driver_car_model = \'''' + driver_car_model + '''\',
                                driver_car_make = \'''' + driver_car_make + '''\',
                                driver_insurance_carrier = \'''' + driver_insurance_carrier + '''\',
                                driver_insurance_num = \'''' + driver_insurance_num + '''\',
                                driver_insurance_exp_date = \'''' + driver_insurance_exp_date + '''\',
                                driver_insurance_picture = \'''' + driver_insurance_picture + '''\',
                                emergency_contact_name = \'''' + contact_name + '''\',
                                emergency_contact_phone = \'''' + contact_phone + '''\',
                                emergency_contact_relationship = \'''' + contact_relation + '''\',
                                bank_account_info = \'''' + bank_acc_info + '''\',
                                bank_routing_info = \'''' + bank_routing_info + '''\'
                                WHERE driver_uid = \'''' + driver_uid + '''\';
                                ''' 
            print("after query")

            # else:

            #     # check if there is a same driver_id existing
            #     query = """
            #             SELECT driver_email FROM jd.drivers
            #             WHERE driver_email = \'""" + email + "\';"
            #     print('email---------' + email)
            #     items = execute(query, 'get', conn)
            #     if items['result']:

            #         items['result'] = ""
            #         items['code'] = 409
            #         items['message'] = "Email address has already been taken."

            #         return items

            #     if items['code'] == 480:

            #         items['result'] = ""
            #         items['code'] = 480
            #         items['message'] = "Internal Server Error."
            #         return items

            #     print("inserting to db")
            #     print(license_num,license_exp)
            #     # write everything to database

            #     driver_insert_query =  '''
            #                         INSERT INTO jd.drivers
            #                         SET 
            #                         driver_uid = \'''' + NewUserID + '''\',
            #                         driver_created_at = \'''' + (datetime.now()).strftime("%Y-%m-%d %H:%M:%S") + '''\',
            #                         driver_first_name = \'''' + first_name + '''\',
            #                         driver_last_name = \'''' + last_name + '''\',
            #                         business_id = \'''' + business_uid + '''\',
            #                         referral_source = \'''' + referral_source + '''\',
            #                         driver_available_hours = \'''' + driver_hours + '''\',
            #                         driver_street = \'''' + street + '''\',
            #                         driver_unit = \'''' + unit + '''\',
            #                         driver_city = \'''' + city + '''\',
            #                         driver_state = \'''' + state + '''\',
            #                         driver_zip = \'''' + zipcode + '''\',
            #                         driver_latitude = \'''' + latitude + '''\',
            #                         driver_longitude = \'''' + longitude + '''\',
            #                         driver_phone_num = \'''' + phone + '''\',
            #                         driver_email = \'''' + email + '''\',
            #                         driver_ssn = \'''' + ssn + '''\',
            #                         driver_license = \'''' + license_num + '''\',
            #                         driver_license_exp = \'''' + license_exp + '''\',
            #                         driver_car_year = \'''' + driver_car_year + '''\',
            #                         driver_car_model = \'''' + driver_car_model + '''\',
            #                         driver_car_make = \'''' + driver_car_make + '''\',
            #                         driver_insurance_carrier = \'''' + driver_insurance_carrier + '''\',
            #                         driver_insurance_num = \'''' + driver_insurance_num + '''\',
            #                         driver_insurance_exp_date = \'''' + driver_insurance_exp_date + '''\',
            #                         driver_insurance_picture = \'''' + driver_insurance_picture + '''\',
            #                         emergency_contact_name = \'''' + contact_name + '''\',
            #                         emergency_contact_phone = \'''' + contact_phone + '''\',
            #                         emergency_contact_relationship = \'''' + contact_relation + '''\',
            #                         bank_account_info = \'''' + bank_acc_info + '''\',
            #                         bank_routing_info = \'''' + bank_routing_info + '''\',
            #                         password_salt = \'''' + salt + '''\',
            #                         password_hashed = \'''' + password + '''\',
            #                         password_algorithm = \'''' + algorithm + '''\',
            #                         user_social_media = \'''' + user_social_signup + '''\',
            #                         user_access_token = \'''' + user_access_token + '''\',
            #                         social_timestamp = DATE_ADD(now() , INTERVAL 14 DAY),
            #                         user_refresh_token = \'''' + user_refresh_token + '''\',
            #                         mobile_access_token = \'''' + mobile_access_token + '''\',
            #                         mobile_refresh_token = \'''' + mobile_refresh_token + '''\',
            #                         social_id = \'''' + social_id + '''\';
            #                         ''' 

            
            print(driver_insert_query)
            
            items = execute(driver_insert_query, 'post', conn)
            print(items)
            if items['code'] != 281:
                items['result'] = ""
                items['code'] = 480
                items['message'] = "Error while inserting values in database"

                return items


            items['result'] = {
                'first_name': first_name,
                'last_name': last_name
                # ,
                # 'driver_uid': NewUserID,
                # 'access_token': user_access_token,
                # 'refresh_token': user_refresh_token
            }
            items['message'] = 'Signup successful'
            items['code'] = 200


            return items
        except:
            print("Error happened while Sign Up")
            # if "NewUserID" in locals():
            #     execute("""DELETE FROM users WHERE user_uid = '""" + NewUserID + """';""", 'post', conn)
            # raise BadRequest('Request failed, please try again later.')
        finally:
            disconnect(conn)







class Login(Resource):
    def post(self):
        response = {}
        try:
            conn = connect()
            print('IN')
            data = request.get_json(force=True)
            email = data['email']
            password = data.get('password')
            social_id = data.get('social_id')
            signup_platform = data.get('signup_platform')
            
            #delivery_date = data['delivery_date']
            query = """
                    # CUSTOMER QUERY 1: LOGIN
                    SELECT driver_uid,
                        driver_last_name,
                        driver_first_name,
                        driver_email,
                        password_hashed,
                        email_verified,
                        user_social_media,
                        user_access_token,
                        user_refresh_token,
                        user_access_token,
                        user_refresh_token,
                        social_id
                    FROM jd.drivers
                    WHERE driver_email = \'""" + email + """\';
                    """
            items = execute(query, 'get', conn)
            if items['code'] != 280:
                response['message'] = "Internal Server Error."
                response['code'] = 500
                return response
            elif not items['result']:
                items['message'] = 'Email Not Found. Please signup'
                items['result'] = ''
                items['code'] = 404
                return items
            else:
                print(items['result'])
                print('sc: ', items['result'][0]['user_social_media'])


                # checks if login was by social media
                if password and items['result'][0]['user_social_media'] != 'NULL' and items['result'][0]['user_social_media'] != None:
                    response['message'] = "Need to login by Social Media"
                    response['code'] = 401
                    return response

               # nothing to check
                elif (password is None and social_id is None) or (password is None and items['result'][0]['user_social_media'] == 'NULL'):
                    response['message'] = "Enter password else login from social media"
                    response['code'] = 405
                    return response

                # compare passwords if user_social_media is false
                elif (items['result'][0]['user_social_media'] == 'NULL' or items['result'][0]['user_social_media'] == None) and password is not None:
                    print('comparing passwords')
                    if items['result'][0]['password_hashed'] != password:
                        items['message'] = "Wrong password"
                        items['result'] = ''
                        items['code'] = 406
                        return items

                    if ((items['result'][0]['email_verified']) == '0') or (items['result'][0]['email_verified'] == "FALSE"):
                        response['message'] = "Account need to be verified by email."
                        response['code'] = 407
                        return response

                # compare the social_id because it never expire.
                elif (items['result'][0]['user_social_media']) != 'NULL':
                    print(signup_platform)
                    print(signup_platform == items['result'][0]['user_social_media'])
                    if signup_platform != items['result'][0]['user_social_media']:
                        items['message'] = "Wrong social media used for signup. Use \'" + items['result'][0]['user_social_media'] + "\'."
                        items['result'] = ''
                        items['code'] = 411
                        return items

                    if (items['result'][0]['social_id'] != social_id):
                        print(items['result'][0]['social_id'])

                        items['message'] = "Cannot Authenticated. Social_id is invalid"
                        items['result'] = ''
                        items['code'] = 408
                        return items

                else:
                    string = " Cannot compare the password or social_id while log in. "
                    print("*" * (len(string) + 10))
                    print(string.center(len(string) + 10, "*"))
                    print("*" * (len(string) + 10))
                    response['message'] = string
                    response['code'] = 500
                    return response
                del items['result'][0]['password_hashed']
                del items['result'][0]['email_verified']

                query = """
                        SELECT driver_uid, driver_first_name, driver_last_name, business_id, driver_available_hours, driver_scheduled_hours, driver_street, driver_city, driver_state, driver_zip, driver_latitude, driver_longitude, driver_phone_num, driver_email, driver_phone_num2, driver_ssn, driver_license, driver_license_exp, driver_insurance_carrier, driver_insurance_num, driver_insurance_exp_date, driver_insurance_picture, emergency_contact_name, emergency_contact_phone, emergency_contact_relationship
                        FROM jd.drivers
                        WHERE driver_email = \'""" + email + """\' ;
                        """
                '''
                query = """SELECT temp.driver_uid
                               , temp.driver_first_name
                               , temp.driver_last_name
                               , temp.driver_email
							   , temp.route_id
                               , temp.route_option
                               , temp.route_business_id
                               , temp.num_deliveries
                               , temp.route_distance
                               , temp.route_time
                               , temp.shipment_date
                               , tt.delivery_first_name
                               , tt.delivery_last_name
                               , tt.delivery_email
                               , tt.delivery_phone
                               , tt.delivery_coordinates
                               , tt.delivery_street
                               , tt.delivery_city
                               , tt.delivery_state
                               , tt.delivery_zip
                               , tt.delivery_instructions
                               , tt.delivery_status
                               , tt.purchase_uid
                               , tt.customer_uid
                               , tt.start_delivery_date
                               , tt.delivery_items
                        FROM (SELECT rr.route_id,
									d.driver_uid,
                                    d.driver_first_name,
                                    d.driver_last_name,
                                    d.driver_email,
					                rr.route_option,
					                rr.business_id AS route_business_id,
					                rr.driver_num AS route_driver_id,
					                TRIM(BOTH '"' FROM (CAST(JSON_EXTRACT(rr.route,val) AS CHAR))) AS route_delivery_info,
					                rr.num_deliveries,
					                rr.distance AS route_distance,
					                rr.route_time,
					                rr.shipment_date
				                FROM 
					                jd.drivers d, (SELECT * FROM jd.routes WHERE business_id = 'sf' ORDER BY timestamp DESC LIMIT 1) as rr 
                                    JOIN numbers ON JSON_LENGTH(route) >= n WHERE d.driver_email = \'""" + email + """\' 
                                    AND rr.shipment_date = \'""" + delivery_date + """\' AND  d.driver_uid = rr.driver_num) AS temp,
                        JSON_TABLE(CONVERT(route_delivery_info, JSON), '$[*]' COLUMNS(
				                delivery_first_name VARCHAR(255) PATH '$.delivery_first_name',
				                delivery_last_name VARCHAR(255) PATH '$.delivery_last_name',
                                delivery_email VARCHAR(255) PATH '$.email',
                                delivery_phone VARCHAR(255) PATH '$.phone',
                                delivery_coordinates JSON PATH '$.coordinates',
                                delivery_street VARCHAR(255) PATH '$.delivery_street',
                                delivery_city VARCHAR(255) PATH '$.delivery_city',
                                delivery_state VARCHAR(255) PATH '$.delivery_state',
                                delivery_zip VARCHAR(255) PATH '$.delivery_zip',
                                delivery_instructions VARCHAR(255) PATH '$.delivery_instructions',
                                delivery_status VARCHAR(255) PATH '$.delivery_status',
                                purchase_uid VARCHAR(255) PATH '$.purchase_uid',
                                customer_uid VARCHAR(255) PATH '$.customer_uid',
                                start_delivery_date VARCHAR(255) PATH '$.start_delivery_date',
                                delivery_items JSON PATH '$.items')
                                ) as tt;"""
                '''
                items = execute(query, 'get', conn)
                items['message'] = "Authenticated successfully."
                items['code'] = 200
                return items

        except:
            raise BadRequest('Request failed, please try again later.')
        finally:
            disconnect(conn)


#DIRECT LOGIN
# {
#     "email":"test12334@test.com",
#     "password":"92a9f0948eec82b306cabdf4caaecb62fa123d5625942435acb96dad027c31fabbdb3a238e0e288853bcbc8fccc3e934504a1819eb3d09d544cc960a8df8e56a",
#     "refresh_token":"",
#     "signup_platform":""
# }

#GOOGLE LOGIN
# {
# "email" : "pmarathay@gmail.com",
# "password" : "",
# "social_id" : "117240672996349246664",
# "signup_platform" : "GOOGLE",
# "delivery_date":"2021-02-28 10:00:00"
# }

class AppleLogin(Resource):
    def post(self):
        response = {}
        items = {}
        try:
            conn = connect()
            token = request.form.get('id_token')
            print(token)
            if token:
                print('Starting decode')
                data = jwt.decode(token, verify=False)
                print('data-----', data)
                email = data.get('email')

                print(data, email)
                if email is not None:
                    sub = data['sub']
                    query = """
                    SELECT driver_uid,
                        driver_first_name,
                        driver_last_name,
                        driver_email,
                        password_hashed,
                        email_verified,
                        user_social_media,
                        user_access_token,
                        user_refresh_token
                    FROM jd.drivers 
                    WHERE driver_email = \'""" + email + """\';
                    """
                    items = execute(query, 'get', conn)
                    print(items)

                    if items['code'] != 280:
                        items['message'] = "Internal error"
                        return items


                    # new customer
                    if not items['result']:
                        items['message'] = "Email doesn't exists Please go to the signup page"
                        get_user_id_query = "CALL get_driver_id();"
                        NewUserIDresponse = execute(get_user_id_query, 'get', conn)

                        if NewUserIDresponse['code'] == 490:
                            string = " Cannot get new User id. "
                            print("*" * (len(string) + 10))
                            print(string.center(len(string) + 10, "*"))
                            print("*" * (len(string) + 10))
                            response['message'] = "Internal Server Error."
                            response['code'] = 500
                            return response

                        NewUserID = NewUserIDresponse['result'][0]['new_id']
                        user_social_signup = 'APPLE'
                        print('NewUserID', NewUserID)

                        driver_insert_query = """
                                    INSERT INTO jd.drivers
                                    (
                                        driver_uid,
                                        driver_created_at,
                                        driver_email,
                                        user_social_media,
                                        user_refresh_token
                                    )
                                    VALUES
                                    (
                                    
                                        \'""" + NewUserID + """\',
                                        \'""" + (datetime.now()).strftime("%Y-%m-%d %H:%M:%S") + """\',
                                        \'""" + email + """\',
                                        \'""" + user_social_signup + """\',
                                        \'""" + sub + """\'
                                    );"""

                        item = execute(driver_insert_query, 'post', conn)

                        print('INSERT')

                        if item['code'] != 281:
                            item['message'] = 'Check insert sql query'
                            return item

                        return redirect("http://localhost:3000/socialsignup?id=" + NewUserID)

                    # Existing customer

                    if items['result'][0]['user_refresh_token']:
                        print('user_refresh_token')
                        print(items['result'][0]['user_social_media'], items['result'][0]['user_refresh_token'])

                        if items['result'][0]['user_social_media'] != "APPLE":
                            print('Wrong sign up method')
                            items['message'] = "Wrong social media used for signup. Use \'" + items['result'][0]['user_social_media'] + "\'."
                            items['code'] = 400
                            return redirect("http://localhost:3000/?media=" + items['result'][0]['user_social_media'])

                        elif items['result'][0]['user_refresh_token'] != sub:
                            print('token mismatch')
                            items['message'] = "Token mismatch"
                            items['code'] = 400
                            return redirect("http://localhost:3000/")

                        else:
                            print('successfully login with apple redirecting......')
                            return redirect("http://localhost:3000/users?id=" + items['result'][0]['user_uid'])

                else:
                    items['message'] = "Email not returned by Apple LOGIN"
                    items['code'] = 400
                    return items


            else:
                response = {
                    "message": "Token not found in Apple's Response",
                    "code": 400
                }
                return response
        except:
            traceback.print_exc()
            raise BadRequest("Request failed, please try again later.")
        finally:
            disconnect(conn)

'''
class GoogleLogin(Resource):
    def post(self):
        response = {}
        items = {}
        try:
            conn = connect()
            token = request.form.get('id_token')
            print(token)
            if token:
                try: 
                    data = id_token.verify_oauth2_token(token, reqs.Request(), '407408718192.apps.googleusercontent.com')
                except ValueError:
                    print('Invalid token')
                    response['message'] = 'Invalid token'
                    response['code'] = 401
                    return response, 401

                print('valid token')
                email = data['email']
                if email is not None:
                    sub = data['sub']
                    query = """
                    SELECT driver_uid,
                        driver_first_name,
                        driver_last_name,
                        driver_email,
                        password_hashed,
                        email_verified,
                        user_social_media,
                        user_access_token,
                        user_refresh_token
                    FROM jd.drivers
                    WHERE driver_email = \'""" + email + """\';
                    """
                    items = execute(query, 'get', conn)
                    print(items)

                    if items['code'] != 280:
                        items['message'] = "Internal error"
                        return items


                    # new customer
                    if not items['result']:
                        items['message'] = "Email doesn't exists Please go to the signup page"
                        get_user_id_query = "CALL get_driver_id();"
                        NewUserIDresponse = execute(get_user_id_query, 'get', conn)

                        if NewUserIDresponse['code'] == 490:
                            string = " Cannot get new User id. "
                            print("*" * (len(string) + 10))
                            print(string.center(len(string) + 10, "*"))
                            print("*" * (len(string) + 10))
                            response['message'] = "Internal Server Error."
                            response['code'] = 500
                            return response

                        NewUserID = NewUserIDresponse['result'][0]['new_id']
                        user_social_signup = 'GOOGLE'
                        print('NewUserID', NewUserID)


                        driver_insert_query = """
                                    INSERT INTO jd.drivers
                                    (
                                        driver_uid,
                                        driver_created_at,
                                        driver_email,
                                        email_verified,
                                        user_social_media,
                                        user_refresh_token
                                    )
                                    VALUES
                                    (
                                    
                                        \'""" + NewUserID + """\',
                                        \'""" + (datetime.now()).strftime("%Y-%m-%d %H:%M:%S") + """\',
                                        \'""" + email + """\',
                                        \'""" + '1' + """\',
                                        \'""" + user_social_signup + """\',
                                        \'""" + sub + """\'
                                    );"""

                        item = execute(driver_insert_query, 'post', conn)

                        print('INSERT')

                        if item['code'] != 281:
                            item['message'] = 'Check insert sql query'
                            return item

                        return redirect("http://localhost:3000/socialsignup?id=" + NewUserID)

                    # Existing customer

                    if items['result'][0]['user_refresh_token']:
                        print('user_refresh_token')
                        print(items['result'][0]['user_social_media'], items['result'][0]['user_refresh_token'])

                        if items['result'][0]['user_social_media'] != "GOOGLE":
                            print('Wrong sign up method')
                            items['message'] = "Wrong social media used for signup. Use \'" + items['result'][0]['user_social_media'] + "\'."
                            items['code'] = 400
                            return redirect("http://localhost:3000/?media=" + items['result'][0]['user_social_media'])

                        elif items['result'][0]['user_refresh_token'] != sub:
                            print('ID mismatch')
                            items['message'] = "ID mismatch"
                            items['code'] = 400
                            return redirect("http://localhost:3000/")

                        else:
                            print('Successfully authenticated with google redirecting.......')
                            return redirect("http://localhost:3000/users?id=" + items['result'][0]['user_uid'])

                else:
                    items['message'] = "Email not returned by GOOGLE LOGIN"
                    items['code'] = 400
                    return items


            else:
                response = {
                    "message": "Google ID token does not exist",
                    "code": 400
                }
                return response
        except:
            raise BadRequest("Request failed, please try again later.")
        finally:
            disconnect(conn)
'''

# {
#     "uid":"930-000027",
#     "delivery_date":"2021-06-06 10:00:00"
#  }
class driver_route_day(Resource):
    def post(self):
        try:
            data = request.get_json(force=True)
            conn = connect()
            uid = data['uid']
            delivery_date = data['delivery_date']

            query = """
                    SELECT temp.driver_uid
                    , temp.driver_first_name
                    , temp.driver_last_name
                    , temp.driver_email
                    , temp.route_id
                    , temp.route_option
                    , temp.route_business_id
                    , temp.num_deliveries
                    , temp.route_distance
                    , temp.route_time
                    , temp.shipment_date
                    , tt.delivery_first_name
                    , tt.delivery_last_name
                    , tt.delivery_email
                    , tt.delivery_phone
                    , tt.delivery_coordinates
                    , tt.delivery_street
                    , tt.delivery_city
                    , tt.delivery_state
                    , tt.delivery_zip
                    , tt.delivery_instructions
                    , tt.delivery_status
                    , tt.purchase_uid
                    , tt.customer_uid
                    , tt.start_delivery_date
                    , tt.delivery_items
                    , tt.delivery_unit
                    FROM (SELECT rr.route_id,
                        d.driver_uid,
                        d.driver_first_name,
                        d.driver_last_name,
                        d.driver_email,
                        rr.route_option,
                        rr.business_id AS route_business_id,
                        rr.driver_num AS route_driver_id,
                        TRIM(BOTH '"' FROM (CAST(JSON_EXTRACT(rr.route,val) AS CHAR))) AS route_delivery_info,
                        rr.num_deliveries,
                        rr.distance AS route_distance,
                        rr.route_time,
                        rr.shipment_date
                    FROM 
                        jd.drivers d, (SELECT * FROM jd.routes WHERE business_id = 'sf' AND driver_num=\'""" + uid + """\' AND shipment_date LIKE \'""" + delivery_date[:10] + '%' + """\' ORDER BY timestamp DESC LIMIT 1) as rr 
                        JOIN numbers ON JSON_LENGTH(route) >= n WHERE d.driver_uid = \'""" + uid + """\'
                        AND rr.shipment_date LIKE \'""" + delivery_date[:10] + '%' + """\' AND  d.driver_uid = rr.driver_num) AS temp,
                    JSON_TABLE(CONVERT(route_delivery_info, JSON), '$[*]' COLUMNS(
                    delivery_first_name VARCHAR(255) PATH '$.delivery_first_name',
                    delivery_last_name VARCHAR(255) PATH '$.delivery_last_name',
                    delivery_email VARCHAR(255) PATH '$.email',
                    delivery_phone VARCHAR(255) PATH '$.phone',
                    delivery_coordinates JSON PATH '$.coordinates',
                    delivery_street VARCHAR(255) PATH '$.delivery_street',
                    delivery_city VARCHAR(255) PATH '$.delivery_city',
                    delivery_state VARCHAR(255) PATH '$.delivery_state',
                    delivery_zip VARCHAR(255) PATH '$.delivery_zip',
                    delivery_instructions VARCHAR(255) PATH '$.delivery_instructions',
                    delivery_status VARCHAR(255) PATH '$.delivery_status',
                    purchase_uid VARCHAR(255) PATH '$.purchase_uid',
                    customer_uid VARCHAR(255) PATH '$.customer_uid',
                    start_delivery_date VARCHAR(255) PATH '$.start_delivery_date',
                    delivery_unit VARCHAR(255) PATH '$.delivery_unit',
                    delivery_items JSON PATH '$.items')
                    ) as tt;
                """
            
            items = execute(query, 'get',conn)
            if items['code'] != '280':
                items['message'] = 'check sql query'
            return items
        except:
             raise BadRequest("Request failed, please try again later.")
        finally:
             disconnect(conn)
# Customer Queries
class Customers(Resource):
    def get(self):
        response = {}
        items = {}
        try:
            conn = connect()

            items = execute("""SELECT * FROM jd.customers;""", 'get', conn)
            response['message'] = 'Successful'
            response['result'] = items

            return response, 200
        except:
            raise BadRequest('Bad request, error while retrieving customers')
        finally:
            disconnect(conn)
        # http://127.0.0.1:4000/api/v2/Customers
        # https://rqiber37a4.execute-api.us-west-1.amazonaws.com/dev/api/v2/Customers

# Purchases Queries
class Purchases(Resource):
    def get(self):
        response = {}
        items = {}
        try:
            conn = connect()

            items = execute("""SELECT * FROM jd.purchases;""", 'get', conn)
            response['message'] = 'Successful'
            response['result'] = items

            return response, 200
        except:
            raise BadRequest('Bad request, error while retrieving purchases')
        finally:
            disconnect(conn)
        # http://127.0.0.1:4000/api/v2/Purchases
        # https://rqiber37a4.execute-api.us-west-1.amazonaws.com/dev/api/v2/Purchases

# Business Queries
class Businesses(Resource):
    # Get Businesses
    def get(self):
        response = {}
        items = {}
        try:
            conn = connect()
            items = execute("""SELECT * FROM jd.businesses""", 'get', conn)
            response['message'] = 'Successful getting businesses'
            response['result'] = items

            return response, 200
        except:
            raise BadRequest('Request failed, error in GET for Businesses.')
        finally:
            disconnect(conn)
        # http://127.0.0.1:4000/api/v2/Businesses
        # https://rqiber37a4.execute-api.us-west-1.amazonaws.com/dev/api/v2/Businesses

    # Update business info
    def post(self):
        response = {}
        items = {}
        try:
            conn = connect()

            data = request.get_json(force=True)

            business_uid = data['business_uid']
            new_data = data['new_data']
            inner_query = ''
            print(data)
            for i in new_data:
                if new_data[i] == '':
                    continue
                if i == list(new_data.keys())[-1]:
                    inner_query += i + ' = \'' + new_data[i] + '\' '
                else:
                    inner_query += i + ' = \'' + new_data[i] + '\', '

            query = """UPDATE jd.businesses
                       SET """ + inner_query + """
                       WHERE business_uid = \'""" + business_uid + """\';"""

            items = execute(query, 'post', conn)
            response['message'] = 'Successfully updated business'
            response['result'] = items

            return response, 200
        except:
            raise BadRequest('Request failed, error while updating business')
        finally:
            disconnect(conn)
        # http://127.0.0.1:4000/api/v2/Businesses
        # https://rqiber37a4.execute-api.us-west-1.amazonaws.com/dev/api/v2/Businesses
        # UPDATE MUST BE IN THIS FORMAT
        # {
        #     "business_uid":"200-000003",
        #     "new_data":{"business_type":"test"}
        # }

# Insert new business
class InsertNewBusiness(Resource):
    def post(self):
        response = {}
        items = {}
        try:
            conn = connect()
            data = request.get_json(force=True)

            business_created_at = data['business_created_at']
            business_name = data['business_name']
            business_type = data['business_type']
            business_desc = data['business_desc']
            business_contact_first_name = data['business_contact_first_name']
            business_contact_last_name = data['business_contact_last_name']
            business_phone_num = data['business_phone_num']
            business_phone_num2 = data['business_phone_num2']
            business_email = data['business_email']
            business_hours = data['business_hours']
            business_accepting_hours = data['business_accepting_hours']
            business_delivery_hours = data['business_delivery_hours']
            business_address = data['business_address']
            business_unit = data['business_unit']
            business_city = data['business_city']
            business_state = data['business_state']
            business_zip = data['business_zip']
            business_longitude = data['business_longitude']
            business_latitude = data['business_latitude']
            business_EIN = data['business_EIN']
            business_WAUBI = data['business_WAUBI']
            business_license = data['business_license']
            business_USDOT = data['business_USDOT']
            notification_approval = data['notification_approval']
            notification_device_id = data['notification_device_id']
            can_cancel = data['can_cancel']
            delivery = data['delivery']
            reusable = data['reusable']
            business_image = data['business_image']
            business_password = data['business_password']

            #print(data)
            print(type(business_hours))
            NewBusinessIDQuery = execute(
                'CALL jd.new_business_uid;', 'get', conn)
            NewBusinessID = NewBusinessIDQuery['result'][0]['new_id']
            print('creating query')

            #query =  '''INSERT INTO  jd.businesses SET business_uid   =        \'''' + NewBusinessID + '''\';'''
            #query =  '''INSERT INTO  jd.businesses (   business_uid)   VALUES( \'''' + NewBusinessID + '''\');'''

            #query =  """INSERT INTO  jd.businesses (   business_uid)   VALUES( \'""" + NewBusinessID + """\');"""
            #query =  '''INSERT INTO  jd.refunds    SET refund_uid     = \'''' + NewID         + '''\';'''

            #query = """INSERT INTO jd.businesses (      business_uid) VALUES(   \'""" + NewBusinessID + """\');"""
            query = """INSERT INTO jd.businesses (
                                                 business_uid
                                                 , business_created_at
                                                 , business_name
                                                 , business_type
                                                 , business_desc
                                                 , business_contact_first_name
                                                 , business_contact_last_name
                                                 , business_phone_num
                                                 , business_phone_num2
                                                 , business_email
                                                 , business_hours
                                                 , business_accepting_hours
                                                 , business_delivery_hours
                                                 , business_address
                                                 , business_unit
                                                 , business_city
                                                 , business_state
                                                 , business_zip
                                                 , business_longitude
                                                 , business_latitude
                                                 , business_EIN
                                                 , business_WAUBI
                                                 , business_license
                                                 , business_USDOT
                                                 , notification_approval
                                                 , notification_device_id
                                                 , can_cancel
                                                 , delivery
                                                 , reusable
                                                 , business_image
                                                 , business_password)
                                                
                                                 VALUES(
                                                 \'""" + NewBusinessID + """\'
                                                 , \'""" + business_created_at + """\'
                                                 , \'""" + business_name + """\'
                                                 , \'""" + business_type + """\'
                                                 , \'""" + business_desc + """\'
                                                 , \'""" + business_contact_first_name + """\'
                                                 , \'""" + business_contact_last_name + """\'
                                                 , \'""" + business_phone_num + """\'
                                                 , \'""" + business_phone_num2 + """\'      
                                                 , \'""" + business_email + """\'
                                                 , \'""" + business_hours + """\'
                                                 , \'""" + business_accepting_hours + """\'
                                                 , \'""" + business_delivery_hours + """\'
                                                 , \'""" + business_address + """\'
                                                 , \'""" + business_unit + """\'
                                                 , \'""" + business_city + """\'
                                                 , \'""" + business_state + """\'
                                                 , \'""" + business_zip + """\'
                                                 , \'""" + business_longitude + """\'
                                                 , \'""" + business_latitude + """\'
                                                 , \'""" + business_EIN + """\'
                                                 , \'""" + business_WAUBI + """\'
                                                 , \'""" + business_license + """\'
                                                 , \'""" + business_USDOT + """\'
                                                 , \'""" + notification_approval + """\'
                                                 , \'""" + notification_device_id + """\'
                                                 , \'""" + can_cancel + """\'
                                                 , \'""" + delivery + """\'
                                                 , \'""" + reusable + """\'
                                                 , \'""" + business_image + """\'
                                                 , \'""" + business_password + """\');"""

            print('finished creating query')
            print(query)
            print('executing query')
            items = execute(query, 'post', conn)
            response['message'] = 'Successfully inserted new Business'
            response['result'] = items

            return response, 200
        except:
            raise BadRequest('Bad request, error inserting new business')
        finally:
            disconnect(conn)

        # http://127.0.0.1:4000/api/v2/insertNewBusiness
        # https://rqiber37a4.execute-api.us-west-1.amazonaws.com/dev/api/v2/insertNewBusiness
        #     {
        #         "business_created_at": "2020-09-10T17:34:48",
        #         "business_name": "test",
        #         "business_type": "test",
        #         "business_desc": "test",
        #         "business_contact_first_name": "test",
        #         "business_contact_last_name": "test",
        #         "business_phone_num": "test",
        #         "business_phone_num2": "test",
        #         "business_email": "test",
        #         "business_hours": "{\"Friday\": [\"09:00:00\", \"23:59:59\"], \"Monday\": [\"09:00:00\", \"23:59:59\"], \"Sunday\": [\"09:00:00\", \"23:59:59\"], \"Tuesday\": [\"09:00:00\", \"23:59:59\"], \"Saturday\": [\"09:00:00\", \"21:00:00\"], \"Thursday\": [\"09:00:00\", \"23:59:59\"], \"Wednesday\": [\"09:00:00\", \"23:00:00\"]}",
        #         "business_accepting_hours": "{\"Friday\": [\"09:00:00\", \"23:59:59\"], \"Monday\": [\"09:00:00\", \"23:59:59\"], \"Sunday\": [\"09:00:00\", \"23:59:59\"], \"Tuesday\": [\"09:00:00\", \"23:59:59\"], \"Saturday\": [\"09:00:00\", \"21:00:00\"], \"Thursday\": [\"09:00:00\", \"23:59:59\"], \"Wednesday\": [\"09:00:00\", \"23:00:00\"]}",
        #         "business_delivery_hours": "{\"Friday\": [\"09:00:00\", \"23:59:59\"], \"Monday\": [\"09:00:00\", \"23:59:59\"], \"Sunday\": [\"09:00:00\", \"23:59:59\"], \"Tuesday\": [\"09:00:00\", \"23:59:59\"], \"Saturday\": [\"09:00:00\", \"21:00:00\"], \"Thursday\": [\"09:00:00\", \"23:59:59\"], \"Wednesday\": [\"09:00:00\", \"23:00:00\"]}",
        #         "business_address": "blah",
        #         "business_unit": "",
        #         "business_city": "blah",
        #         "business_state": "blah",
        #         "business_zip": "blah",
        #         "business_longitude": "blah",
        #         "business_latitude": "blah",
        #         "business_EIN": "blah",
        #         "business_WAUBI": "blah",
        #         "business_license": "blah",
        #         "business_USDOT": "blah",
        #         "notification_approval": "blah",
        #         "notification_device_id": "blah",
        #         "can_cancel": "0",
        #         "delivery": "0",
        #         "reusable": "0",
        #         "business_image": "https://servingnow.s3-us-west-1.amazonaws.com/kitchen_imgs/landing-logo.png",
        #         "business_password": "pbkdf2:sha256:150000$zMHfn0jt$29cef351d84456b5f6b665bc2bbab8ae3c6e42bd0e4a4e8967041a9455a24798"
        # }

# Get Constraints by Business
class GetBusinessConstraints(Resource):
    def get(self, business_uid):
        response = {}
        items = {}
        try:
            conn = connect()
            query = """SELECT * FROM jd.constraints WHERE business_uid = %s"""
            bus_uid = "\'" + business_uid + "\'"
            constraints_query = query % bus_uid
            items = execute(constraints_query, 'get', conn)

            response['message'] = 'Successful get constraints by business'
            response['result'] = items

            return response, 200
        except:
            raise BadRequest(
                'Request failed, error in GetBusinessConstraints.')
        finally:
            disconnect(conn)

        # http://127.0.0.1:4000/api/v2/getBusinessConstraints/<string:business_uid>
        # https://rqiber37a4.execute-api.us-west-1.amazonaws.com/dev/api/v2/getBusinessConstraints/<string:business_uid>


# Driver Queries
class SpecificDriver(Resource):
    def post(self):
        response = {}
        items = {}
        try:
            conn = connect()
            data = request.get_json(force=True)
            print(data)
            driver_uid = data['driver_uid']
            print(driver_uid)
            items = execute("""SELECT * FROM jd.drivers WHERE driver_uid = \'""" + driver_uid + """\';""", 'get', conn)
            response['message'] = 'Successful getting drivers'
            response['result'] = items

            return items, 200

        except:
            raise BadRequest('Request failed, error in SpecificDrivers.')

        finally:
            disconnect(conn)

class Drivers(Resource):
    def get(self):
        response = {}
        items = {}
        try:
            conn = connect()
            items = execute("""SELECT * FROM jd.drivers""", 'get', conn)
            response['message'] = 'Successful getting drivers'
            response['result'] = items

            return response, 200
        except:
            raise BadRequest('Request failed, error in GetDrivers.')
        finally:
            disconnect(conn)

        # http://127.0.0.1:4000/api/v2/Drivers
        # https://rqiber37a4.execute-api.us-west-1.amazonaws.com/dev/api/v2/Drivers

    def post(self):
        response = {}
        items = {}
        try:
            conn = connect()

            data = request.get_json(force=True)

            driver_uid = data['driver_uid']
            new_data = data['new_data']

            inner_query = ''

            for i in new_data:
                if new_data[i] == '':
                    continue
                if i == list(new_data.keys())[-1]:
                    inner_query += i + ' = \'' + new_data[i] + '\' '
                else:
                    inner_query += i + ' = \'' + new_data[i] + '\', '

            query = """UPDATE jd.drivers
                       SET """ + inner_query + """
                       WHERE driver_uid = \'""" + driver_uid + """\';"""

            items = execute(query, 'post', conn)
            response['message'] = 'Successfully updated drivers'
            response['result'] = items

            return response, 200
        except:
            raise BadRequest('Request failed, error while updating drivers')
        finally:
            disconnect(conn)

        # http://127.0.0.1:4000/api/v2/Drivers
        # https://uqu7qejuee.execute-api.us-west-1.amazonaws.com/api/v2/Drivers

# Update Driver_ID by route
class UpdateDriverID(Resource):
    def get(self, driver_id, route_id):
        response = {}
        items = {}
        try:
            conn = connect()
            new_driver_id = "\'" + driver_id + "\'"
            route_id = "\'" + route_id + "\'"
            query = 'UPDATE jd.routes SET driver_num = %s WHERE route_id = %s' % (
                new_driver_id, route_id)
            print(query)
            items = execute(query, 'post', conn)
            response['message'] = 'Successfully updated Driver ID'
            response['result'] = items

            return response, 200
        except:
            raise BadRequest('Request failed, error in updating Driver ID.')
        finally:
            disconnect(conn)

        # http://127.0.0.1:4000'/api/v2/updateDriverID/<string:driver_id>/<string:route_id>'
        # https://uqu7qejuee.execute-api.us-west-1.amazonaws.com'/api/v2/updateDriverID/<string:driver_id>/<string:route_id>

# Get Customers by Business
class GetCustomersByBusiness(Resource):
    def get(self, business_uid):
        response = {}
        items = {}
        try:
            conn = connect()
            query = """SELECT * 
                        FROM (SELECT pur_driver_uid, pur_business_uid FROM jd.purchases WHERE pur_business_uid = %s) AS temp
                    JOIN customers c ON temp.pur_driver_uid = c.driver_uid GROUP BY c.driver_uid;"""
            bus_uid = "\'" + business_uid + "\'"
            constraints_query = query % bus_uid
            items = execute(constraints_query, 'get', conn)

            response['message'] = 'Successful getting customers for business'
            response['result'] = items

            return response, 200
        except:
            raise BadRequest('Request failed, error in GetCustomerByBusiness.')
        finally:
            disconnect(conn)

        # http://127.0.0.1:4000/api/v2/getCustomersByBusiness/<string:business_uid>
        # https://rqiber37a4.execute-api.us-west-1.amazonaws.com/dev/api/v2/getCustomersByBusiness/<string:business_uid>

# Get Vehicles
class GetVehicles(Resource):
    def get(self):
        response = {}
        items = {}
        try:
            conn = connect()
            items = execute("""SELECT * FROM jd.vehicles;""", 'get', conn)
            response['message'] = 'Successful getting vehicles'
            response['result'] = items

            return response, 200
        except:
            raise BadRequest('Request failed, error in GetVehicles.')
        finally:
            disconnect(conn)

        # http://127.0.0.1:4000/api/v2/insertNewBusiness
        # https://rqiber37a4.execute-api.us-west-1.amazonaws.com/dev/api/v2/GetVehicles

# Get Customers that have not ordered from a business
class GetCustomersNotOrderFromBusiness(Resource):
    def get(self, business_uid):
        response = {}
        items = {}
        try:
            conn = connect()
            query = """SELECT * 
                        FROM (SELECT pur_driver_uid FROM jd.purchases WHERE pur_business_uid NOT IN (%s)) AS temp
                    JOIN customers c ON temp.pur_driver_uid = c.driver_uid GROUP BY c.driver_uid;"""
            bus_uid = "\'" + business_uid + "\'"
            constraints_query = query % bus_uid
            items = execute(constraints_query, 'get', conn)

            response['message'] = 'Successful getting customers not order from business'
            response['result'] = items

            return response, 200
        except:
            raise BadRequest(
                'Request failed, error in GetCustomerNotOrderFromBusiness.')
        finally:
            disconnect(conn)

        # http://127.0.0.1:4000/api/v2/getCustomersNotOrderFromBusiness/<string:business_uid>
        # https://rqiber37a4.execute-api.us-west-1.amazonaws.com/dev/api/v2/getCustomersNotOrderFromBusiness/<string:business_uid>

# Insert new Driver
class NewDriver(Resource):
    def post(self):
        response = {}
        items = {}
        try:
            conn = connect()
            data = request.get_json(force=True)
            print("getting data")

            driver_first_name = data['driver_first_name']
            driver_last_name = data['driver_last_name']
            business_id = data['business_id']
            driver_available_hours = data['driver_available_hours']
            driver_scheduled_hours = data['driver_scheduled_hours']
            driver_street = data['driver_street']
            driver_city = data['driver_city']
            driver_state = data['driver_state']
            driver_zip = data['driver_zip']
            driver_phone_num = data['driver_phone_num']
            driver_email = data['driver_email']
            driver_phone_num2 = data['driver_phone_num2']
            driver_ssn = data['driver_ssn']
            driver_license = data['driver_license']
            driver_license_exp = data['driver_license_exp']
            driver_insurance_num = data['driver_insurance_num']
            driver_password = data['driver_password']
            emergency_contact_name = data['emergency_contact_name']
            emergency_contact_phone = data['emergency_contact_phone']
            emergency_contact_relationship = data['emergency_contact_relationship']
            bank_routing_info = data['bank_routing_info']
            bank_account_info = data['bank_account_info']

            print(data)

            resp = execute('CALL get_driver_id;', 'get', conn)
            NewDriverID = resp['result'][0]['new_id']

            print("creating query")

            query = """INSERT INTO jd.drivers (driver_uid, 
                                                driver_first_name, 
                                                driver_last_name, 
                                                business_id, 
                                                driver_available_hours,
                                                driver_scheduled_hours,
                                                driver_street, 
                                                driver_city,
                                                driver_state,
                                                driver_zip,
                                                driver_phone_num,
                                                driver_email,
                                                driver_phone_num2,
                                                driver_ssn,
                                                driver_license,
                                                driver_license_exp,
                                                driver_insurance_num,
                                                driver_password,
                                                emergency_contact_name,
                                                emergency_contact_phone,
                                                emergency_contact_relationship,
                                                bank_routing_info,
                                                bank_account_info) 
                                                
                                            VALUES(
                                                \'""" + NewDriverID + """\'
                                                 , \'""" + driver_first_name + """\'
                                                 , \'""" + driver_last_name + """\'
                                                 , \'""" + business_id + """\'
                                                 , \'""" + driver_available_hours + """\'
                                                 , \'""" + driver_scheduled_hours + """\'
                                                 , \'""" + driver_street + """\'
                                                 , \'""" + driver_city + """\'
                                                 , \'""" + driver_state + """\'
                                                 , \'""" + driver_zip + """\'
                                                 , \'""" + driver_phone_num + """\'
                                                 , \'""" + driver_email + """\'
                                                 , \'""" + driver_phone_num2 + """\'
                                                 , \'""" + driver_ssn + """\'
                                                 , \'""" + driver_license + """\'
                                                 , \'""" + driver_license_exp + """\'
                                                 , \'""" + driver_insurance_num + """\'
                                                 , \'""" + driver_password + """\'
                                                 , \'""" + emergency_contact_name + """\'
                                                 , \'""" + emergency_contact_phone + """\'
                                                 , \'""" + emergency_contact_relationship + """\'
                                                 , \'""" + bank_routing_info + """\'
                                                 , \'""" + bank_account_info + """\');"""

            items = execute(query, 'post', conn)
            response['message'] = 'Successful'
            response['result'] = items

            return response, 200
        except:
            raise BadRequest('Bad request, failed to insert new driver')
        finally:
            disconnect(conn)

        # http://127.0.0.1:4000/api/v2/insertNewDriver
        # https://rqiber37a4.execute-api.us-west-1.amazonaws.com/dev/api/v2/insertNewDriver
        # {
        #   "driver_first_name":"Avatar",
        #   "driver_last_name":"Korra",
        #   "business_id":"200-000001",
        #   "driver_available_hours":"{\"Friday\": [\"09:00:00\", \"23:59:59\"], \"Monday\": [\"09:00:00\", \"23:59:59\"], \"Sunday\": [\"09:00:00\", \"23:59:59\"], \"Tuesday\": [\"09:00:00\", \"23:59:59\"], \"Saturday\": [\"09:00:00\", \"21:00:00\"], \"Thursday\": [\"09:00:00\", \"23:59:59\"], \"Wednesday\": [\"09:00:00\", \"23:00:00\"]}",
        #   "driver_scheduled_hours":"{\"Friday\": [\"09:00:00\", \"23:59:59\"], \"Monday\": [\"09:00:00\", \"23:59:59\"], \"Sunday\": [\"09:00:00\", \"23:59:59\"], \"Tuesday\": [\"09:00:00\", \"23:59:59\"], \"Saturday\": [\"09:00:00\", \"21:00:00\"], \"Thursday\": [\"09:00:00\", \"23:59:59\"], \"Wednesday\": [\"09:00:00\", \"23:00:00\"]}",
        #   "driver_street":"blah",
        #   "driver_city":"b",
        #   "driver_state":"blah",
        #   "driver_zip":"94856",
        #   "driver_phone_num":"4859203965",
        #   "driver_email":"blah",
        #   "driver_phone_num2":"384598569",
        #   "driver_ssn":"34959650",
        #   "driver_license":"4895696",
        #   "driver_license_exp":"4859697690",
        #   "driver_insurance_num":"48965969",
        #   "driver_password":"sha",
        #   "emergency_contact_name":"mary",
        #   "emergency_contact_phone":"349549906",
        #   "emergency_contact_relationship":"mom",
        #   "bank_routing_info":"48569967",
        #   "bank_account_info":"48597607893"
        # }
        # {"driver_first_name":"a","driver_last_name":"a","business_id":"a","driver_available_hours":"{\"Friday\": [\"09:00:00\", \"23:59:59\"], \"Monday\": [\"09:00:00\", \"23:59:59\"], \"Sunday\": [\"09:00:00\", \"23:59:59\"], \"Tuesday\": [\"09:00:00\", \"23:59:59\"], \"Saturday\": [\"09:00:00\", \"21:00:00\"], \"Thursday\": [\"09:00:00\", \"23:59:59\"], \"Wednesday\": [\"09:00:00\", \"23:00:00\"]}","driver_scheduled_hours":"{\"Friday\": [\"09:00:00\", \"23:59:59\"], \"Monday\": [\"09:00:00\", \"23:59:59\"], \"Sunday\": [\"09:00:00\", \"23:59:59\"], \"Tuesday\": [\"09:00:00\", \"23:59:59\"], \"Saturday\": [\"09:00:00\", \"21:00:00\"], \"Thursday\": [\"09:00:00\", \"23:59:59\"], \"Wednesday\": [\"09:00:00\", \"23:00:00\"]}","driver_street":"a","driver_city":"a","driver_state":"a","driver_zip":"a","driver_phone_num":"a","driver_email":"a","driver_phone_num2":"a","driver_ssn":"a","driver_license":"a","driver_license_exp":"a","driver_insurance_num":"a","driver_password":"a","emergency_contact_name":"a","emergency_contact_phone":"a","emergency_contact_relationship":"a","bank_routing_info":"a","bank_account_info":"a"}

# Get Routes
class GetRoutes(Resource):
    def post(self):
        response = {}
        try:
            conn = connect()
            cur = conn.cursor()

            data = request.get_json(force=True)
            farm_address = data['farm_address']
            farm_city = data['farm_city']
            farm_state = data['farm_state']
            farm_zip = data['farm_zip']
            delivery_start_date = data['delivery_date']
            db_name = data['db']

            #Get business_id for each purchase
            get_orders = """SELECT * FROM """ + db_name +""".payments pa, """ + db_name +""".purchases pu 
                            WHERE pa.pay_purchase_uid = pu.purchase_uid  
                            AND pu.delivery_status = \'FALSE\' 
                            AND pu.purchase_status = \'ACTIVE\' 
                            AND CAST(pa.start_delivery_date AS DATETIME) LIKE \'""" + delivery_start_date[:10] + '%' + """\';"""
            print(get_orders)
            
            cur.execute(get_orders)
            purchases = cur.fetchall()
            if purchases == ():
                response['message'] = 'Deliveries for ' + delivery_start_date + ' have already been delivered or there are no deliveries for this day'
                response['code'] = 404
                return response, 500
            
            # get zones
            zone_uids = str(tuple(data['zones']))
            query_zone = """
                    SELECT * from sf.zones
                    WHERE zone_uid IN """ + zone_uids + """;
                  """
            items_zone = execute(query_zone, 'get', conn)
            if items_zone['code'] != 280:
                items_zone['message'] = 'check sql query'
                return items_zone
            purchases_temp = []
            for purchase_val in purchases:
                print(purchase_val['delivery_first_name'],purchase_val['delivery_longitude'],purchase_val['delivery_latitude'])
                for vals in items_zone['result']:
                    LT_long = vals['LT_long']
                    LT_lat = vals['LT_lat']
                    LB_long = vals['LB_long']
                    LB_lat = vals['LB_lat']
                    RT_long = vals['RT_long']
                    RT_lat = vals['RT_lat']
                    RB_long = vals['RB_long']
                    RB_lat = vals['RB_lat']

                    point = Point(float(purchase_val['delivery_longitude']),float(purchase_val['delivery_latitude']))
                    print([(LB_long, LB_lat), (LT_long, LT_lat), (RT_long, RT_lat), (RB_long, RB_lat)])
                    polygon = Polygon([(LB_long, LB_lat), (LT_long, LT_lat), (RT_long, RT_lat), (RB_long, RB_lat)])
                    res = polygon.contains(point)
                    print(res)
                    
                    if res:
                        print("GOT THE DATA")
                        purchases_temp.append(purchase_val)
                        break
            
            print([val['purchase_uid'] for val in purchases])
            print([val['purchase_uid'] for val in purchases_temp])
            
            purchases = purchases_temp
            
            
           
            res = {}
            uids = set()
            for vals in purchases:
                varAd = vals['delivery_address'] + vals['delivery_unit'] + vals['delivery_first_name'] + vals['delivery_last_name']
                print(varAd)
                if varAd not in uids:
                    print("in if")
                    uids.add(varAd)
                    # print("printing",type(vals['items']))
                    # print("printing",vals['items'])
                    res[varAd] = vals
                    print(res[varAd]['purchase_uid'])

                else:
                    print("in else")
                    itemsInitDict = {initVal['item_uid']:initVal for initVal in json.loads(res[varAd]['items'])}
                    itemsCurrDict = {initVal['item_uid']:initVal for initVal in json.loads(vals['items'])}
                    for key, values in itemsCurrDict.items():
                        if key in itemsInitDict:
                            itemsInitDict[key]['qty'] += values['qty']
                        else:
                            itemsInitDict[key] = values
                    #print("frag", itemsInitDict)
                    res[varAd]['items'] = str([its for  key,its in itemsInitDict.items()]).replace("'",'"')
                    print(vals['purchase_uid'])
                    res[varAd]['purchase_uid'] = res[varAd]['purchase_uid'] + "," + vals['purchase_uid']
                    print("in else", type(res[varAd]['items']))
                    #print(res[varAd]['items'])
            
            purchases = [its for  key,its in res.items()]
            
            #Add customers and addresses for each business
            addresses = []
            first = []
            last = []
            street = []
            city = []
            zipcode = []
            delivery_instructions = []
            email = []
            phone = []
            items = []
            delivery_status = []
            purchase_uid = []
            customer_uid = []
            start_delivery_date = []
            state = []
            unit = []
            print('purchases',purchases)
            for purchase in purchases:
                address = purchase['delivery_address'] + ', ' + purchase['delivery_unit'] + ', ' + purchase['delivery_city'] + ', ' + purchase['delivery_state'] + ', ' + purchase['delivery_zip']
                first.append(purchase['delivery_first_name'])
                last.append(purchase['delivery_last_name'])
                addresses.append(address)
                street.append(purchase['delivery_address'])
                unit.append(purchase['delivery_unit'])
                city.append(purchase['delivery_city'])
                state.append(purchase['delivery_state'])
                zipcode.append(purchase['delivery_zip'])
                delivery_instructions.append(purchase['delivery_instructions'])
                email.append(purchase['delivery_email'])
                phone.append(purchase['delivery_phone_num'])
                print(purchase['items'])
                items.append(json.loads(purchase['items']))
                delivery_status.append(purchase['delivery_status'])
                purchase_uid.append(purchase['purchase_uid'])
                customer_uid.append(purchase['pur_customer_uid'])
                start_delivery_date.append(purchase['start_delivery_date'])

            print("@@@@Address",addresses,first)
            business_name = db_name
            business_start_address = farm_address + ' ' + farm_city + ', ' + farm_state + ' ' + farm_zip
            business_start_coordinates = Coordinates([business_start_address]).calculateFromLocations()[0]
            coordinates = Coordinates(addresses).calculateFromLocations()

            areas = {business_start_address+"-Farmer's Market":[business_start_coordinates, business_name, '', '', '', '', farm_address, farm_city, farm_state, farm_zip, '', '', '','', '','','false']}
            for i in range(len(coordinates)):
                areas[addresses[i]+'-'+first[i]+last[i]] = [coordinates[i], first[i], last[i], delivery_instructions[i], 
                    email[i], phone[i], street[i], city[i], state[i], zipcode[i], items[i], delivery_status[i], purchase_uid[i], customer_uid[i], start_delivery_date[i],unit[i],'false']

            coords_dict = {'latitude':[], 'longitude':[]}
            for i in coordinates:
                coords_dict['latitude'].append(i['latitude'])
                coords_dict['longitude'].append(i['longitude'])
            
            print("###coors is",coords_dict)

            #Create np array for coordinates
            df = pd.DataFrame.from_dict(coords_dict)
            coords_array = df.to_numpy()

            drivers = 1
            option = 1
            num_drivers = 1

            #Cluster coordinates and find routes
            while drivers <= num_drivers:
                if drivers > len(coords_array):
                    break
                routes = Kmeans(drivers)
                routes.fit(coords_array)
                driver_num = 1

                #Find route for each driver
                for route in routes.labels:
                    count = 1
                    coords = []
                    route_dict = {} 
                    coords.append(business_start_coordinates)
                    for locations in routes.labels[route]:
                        coords.append({'latitude':locations[0], 'longitude':locations[1]})

                    dmat = DistanceMatrix(coords).calculateFromCoordinates()
                    solution = DistanceConstraintSolution(dmat, 1).solve()

                    num_deliveries = len(solution['result'][0]) - 2
                    route_distance = solution['route_dist'][0]
                    route_time = round(route_distance/96.65, 2)
                    print("**********************solution",solution)
                    print("))))))))))))))))) areas are",[key for key,val in areas.items()])
                    for place in solution['result']:
                        for loc in place:
                            print("--------------------loc",loc)
                            customer_coords = ''
                            street = ''
                            customer_first = ''
                            customer_last = ''
                            cust_email = ''
                            cust_phone = ''
                            deli_instruc = ''
                            cust_street = ''
                            cust_city = ''
                            cust_state = ''
                            cust_zip = ''
                            cust_items = ''
                            deli_status = ''
                            pur_uid = ''
                            cust_uid = ''
                            start = ''
                            unit = ''
                            for i in areas:
                                
                                if (coords[loc]['latitude'],coords[loc]['longitude']) == (areas[i][0]['latitude'],areas[i][0]['longitude']) and areas[i][-1] == 'false':
                                    print('printing areas',areas[i][1],areas[i][-1])
                                    street = i
                                    customer_coords = areas[i][0]
                                    customer_first = areas[i][1]
                                    customer_last = areas[i][2]
                                    deli_instruc = areas[i][3]
                                    cust_email = areas[i][4]
                                    cust_phone = areas[i][5]
                                    cust_street = areas[i][6]
                                    cust_city = areas[i][7]
                                    cust_state = areas[i][8]
                                    cust_zip = areas[i][9]
                                    cust_items = areas[i][10]
                                    deli_status = areas[i][11]
                                    pur_uid = areas[i][12]
                                    cust_uid = areas[i][13]
                                    start = areas[i][14]
                                    unit = areas[i][15]
                                    areas[i][-1] = 'true'
                                    

                                    print(count, "   ", street, "    ")
                                    #print(cust_items)
                                    route_dict[count] = [{'coordinates':customer_coords, 'delivery_street':cust_street, 'delivery_unit':unit,'delivery_city':cust_city, 'delivery_state':cust_state, 
                                                        'delivery_zip':cust_zip,'delivery_first_name':customer_first, 'delivery_last_name':customer_last,
                                                        'delivery_instructions':deli_instruc, 'email':cust_email, 'phone':cust_phone, 
                                                        'items':cust_items, 'delivery_status':deli_status, 'purchase_uid':pur_uid, 'customer_uid':cust_uid, 'start_delivery_date':str(start)}]
                                    #route_dict[count] = customer_coords
                                    #print(route_dict[count])
                                    count += 1

                    
                    # route_dict.popitem()
                    loaded_route = json.dumps(route_dict)

                    #Get new route id
                    cur.execute('CALL jd.get_routes_id;')
                    old_route_id = cur.fetchall()
                    new_route_id = old_route_id[0]['new_id']
                
                    #Insert info for route into database
                    #change driver_num in future but right now default to prashant's uid
                    driver_num_temp = '930-000001'
                    val = (new_route_id, business_name, option, driver_num_temp, loaded_route, route_distance, num_deliveries, route_time, delivery_start_date, datetime.now(), '[]')
                    query = 'INSERT INTO jd.routes (route_id, business_id, route_option, driver_num, route, distance, num_deliveries, route_time, shipment_date, timestamp, route_directions) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s,%s)'
                    #print(query)
                    cur.execute(query, val)
                    conn.commit()
                    
                    driver_num += 1

                drivers += 1
                option += 1
                
            cur.close()
            response['message'] = 'Successfully generated new routes for ' + delivery_start_date
            response['code'] = 280

            return response, 200
        except:
            traceback.print_exc()
            raise BadRequest('Request failed, error in GetRoutes.')
        finally:
            disconnect(conn)

        # http://127.0.0.1:4000/api/v2/GetRoutes
        # https://rqiber37a4.execute-api.us-west-1.amazonaws.com/dev/api/v2/GetRoutes

class GetRouteInfo(Resource):
    def get(self):
        response = {}
        try:
            conn = connect()

            query = """#GET ROUTES
                        SELECT temp.route_id
                               , temp.route_option
                               , temp.route_business_id
                               , temp.route_driver_id
                               , temp.num_deliveries
                               , temp.route_distance
                               , temp.route_time
                               , temp.shipment_date
                               , tt.delivery_first_name
                               , tt.delivery_last_name
                               , tt.delivery_email
                               , tt.delivery_phone
                               , tt.delivery_coordinates
                               , tt.delivery_street
                               , tt.delivery_city
                               , tt.delivery_state
                               , tt.delivery_zip
                               , tt.delivery_instructions
                               , tt.delivery_items
                        FROM (SELECT route_id,
					                            route_option,
					                            business_id AS route_business_id,
					                            driver_num AS route_driver_id,
					                            TRIM(BOTH '"' FROM (CAST(JSON_EXTRACT(route,val) AS CHAR))) AS route_delivery_info,
					                            num_deliveries,
					                            distance AS route_distance,
					                            route_time,
					                            shipment_date
				                FROM 
					                            jd.routes JOIN numbers ON JSON_LENGTH(route) >= n) AS temp,
                    JSON_TABLE(CONVERT(route_delivery_info, JSON), '$[*]' COLUMNS(
				                        delivery_first_name VARCHAR(255) PATH '$.delivery_first_name',
				                        delivery_last_name VARCHAR(255) PATH '$.delivery_last_name',
                                        delivery_email VARCHAR(255) PATH '$.email',
                                        delivery_phone VARCHAR(255) PATH '$.phone',
                                        delivery_coordinates JSON PATH '$.coordinates',
                                        delivery_street VARCHAR(255) PATH '$.delivery_street',
                                        delivery_city VARCHAR(255) PATH '$.delivery_city',
                                        delivery_state VARCHAR(255) PATH '$.delivery_state',
                                        delivery_zip VARCHAR(255) PATH '$.delivery_zip',
                                        delivery_instructions VARCHAR(255) PATH '$.delivery_instructions',
                                        delivery_items JSON PATH '$.items')
                                        ) as tt;"""

            items = execute(query, 'get', conn)

            response['message'] = 'Sucessfully returned route info'
            response['items'] = items['result']

            return response, 200
        except:
            raise BadRequest('Bad request, failed while getting route info')
        finally:
            disconnect(conn)

# Get All Coupons
class GetCoupons(Resource):
    def get(self):
        response = {}
        items = {}
        try:
            conn = connect()

            items = execute('SELECT * FROM jd.coupons;', 'get', conn)

            response['message'] = 'Successful'
            response['result'] = items

            return response, 200

        except:
            raise BadRequest('Request failed, error in retriving coupons')
        finally:
            disconnect(conn)

        # http://127.0.0.1:4000/api/v2/getCoupons
        # https://rqiber37a4.execute-api.us-west-1.amazonaws.com/dev/api/v2/getCoupons

# Inserts new coupon
class InsertNewCoupon(Resource):
    def post(self):
        response = {}
        items = {}
        try:
            conn = connect()

            data = request.get_json(force=True)

            coupon_id = data['coupon_id']
            valid = data['valid']
            discount_percent = data['discount_percent']
            discount_amount = data['discount_amount']
            discount_shipping = data['discount_shipping']
            expire_date = data['expire_date']
            limits = data['limits']
            notes = data['notes']
            num_used = data['num_used']
            recurring = data['recurring']
            email_id = data['email_id']
            cup_business_uid = data['cup_business_uid']

            NewCouponsIDQuery = execute('CALL new_coupons_uid', 'get', conn)
            NewCouponsID = NewCouponsIDQuery['result'][0]['new_id']

            query = """INSERT INTO jd.coupons(coupon_uid
                                              , coupon_id
                                              , valid
                                              , discount_percent
                                              , discount_amount
                                              , discount_shipping
                                              , expire_date
                                              , limits
                                              , notes
                                              , num_used
                                              , recurring
                                              , email_id
                                              , cup_business_uid
                                              )
                                            VALUES(\'""" + NewCouponsID + """\'
                                              , \'""" + coupon_id + """\'
                                               , \'""" + valid + """\'
                                               , \'""" + discount_percent + """\'
                                               , \'""" + discount_amount + """\'
                                               , \'""" + discount_shipping + """\'
                                               , \'""" + expire_date + """\'
                                               , \'""" + limits + """\'
                                               , \'""" + notes + """\'
                                               , \'""" + num_used + """\'
                                               , \'""" + recurring + """\'
                                               , \'""" + email_id + """\'
                                               , \'""" + cup_business_uid + """\');"""

            items = execute(query, 'post', conn)

            response['message'] = 'Successful'
            response['result'] = items

            return response, 200

        except:
            raise BadRequest(
                'Request failed, error while inserting new coupon.')
        finally:
            disconnect(conn)

        # http://127.0.0.1:4000/api/v2/insertNewCoupon
        # https://rqiber37a4.execute-api.us-west-1.amazonaws.com/dev/api/v2/insertNewCoupon
        # {
        #     "coupon_id": "tester",
        #     "valid": "TRUE",
        #     "discount_percent": "10000000000000.0",
        #     "discount_amount": "1000000000000.0",
        #     "discount_shipping": "10000000000000000000.0",
        #     "expire_date": "2099-08-23",
        #     "limits": "10000000",
        #     "notes": "test",
        #     "num_used": "10",
        #     "recurring": "TRUE",
        #     "email_id": "test",
        #     "cup_business_uid": "200-000003"
        # }

# Increase coupon usage
class IncreaseNumCouponUsed(Resource):
    def post(self):
        response = {}
        items = {}
        try:
            conn = connect()

            data = request.get_json(force=True)

            coupon_uid = data['coupon_uid']
            coupon_uid = "\'" + coupon_uid + "\'"

            query = """UPDATE jd.coupons SET num_used = num_used + 1 WHERE coupon_uid = %s""" % coupon_uid

            items = execute(query, 'post', conn)

            response['message'] = 'Successful'
            response['result'] = items

            return response, 200
        except:
            raise BadRequest(
                'Bad request, error while incrementing coupon usage number.')
        finally:
            disconnect(conn)

        # http://127.0.0.1:4000/api/v2/increaseCouponNum
        # https://rqiber37a4.execute-api.us-west-1.amazonaws.com/dev/api/v2/increaseCouponNum
        # {
        #     "coupon_uid":"600-000002"
        # }

class DisableCoupon(Resource):
    def post(self):
        response = {}
        items = {}
        try:
            conn = connect()

            data = request.get_json(force=True)

            coupon_uid = data['coupon_uid']

            query = """UPDATE jd.coupons SET valid = 'FALSE' WHERE coupon_uid = \'""" + \
                coupon_uid + """\';"""
            items = execute(query, 'post', conn)

            response['message'] = 'Successful'
            response['result'] = items

            return response, 200
        except:
            raise BadRequest('Bad request, error while disabling coupon.')
        finally:
            disconnect(conn)
        # http://127.0.0.1:4000/api/v2/disableCoupon
        # https://rqiber37a4.execute-api.us-west-1.amazonaws.com/dev/api/v2/disableCoupon
        # {
        #     "coupon_uid":"600-000024"
        # }

# Get refunds
class GetRefunds(Resource):
    def get(self):
        response = {}
        items = {}
        try:
            conn = connect()

            items = execute('SELECT * FROM jd.refunds;', 'get', conn)

            response['message'] = 'Successful'
            response['result'] = items

            return response, 200
        except:
            raise BadRequest('Request failed, error in retreving refunds.')
        finally:
            disconnect(conn)

        # http://127.0.0.1:4000/api/v2/getRefunds
        # https://rqiber37a4.execute-api.us-west-1.amazonaws.com/dev/api/v2/getRefunds

# Insert new refund
class NewRefund(Resource):
    def post(self):
        response = {}
        items = {}
        try:
            conn = connect()

            data = request.get_json(force=True)

            created_at = data['created_at']
            email_id = data['email_id']
            phone_num = data['phone_num']
            image_url = data['image_url']
            driver_note = data['driver_note']
            admin_note = data['admin_note']
            refund_amount = data['refund_amount']
            ref_coupon_id = data['ref_coupon_id']

            NewRefundIDQuery = execute('CALL new_refund_uid', 'get', conn)
            NewRefundID = NewRefundIDQuery['result'][0]['new_id']

            query = """INSERT INTO jd.refunds(refund_uid
                                              , created_at
                                              , email_id
                                              , phone_num
                                              , image_url
                                              , driver_note
                                              , admin_note
                                              , refund_amount
                                              , ref_coupon_id
                                              )
                                            VALUES(\'""" + NewRefundID + """\'
                                            , \'""" + created_at + """\'
                                            , \'""" + email_id + """\'
                                            , \'""" + phone_num + """\'
                                            , \'""" + image_url + """\'
                                            , \'""" + driver_note + """\'
                                            , \'""" + admin_note + """\'
                                            , \'""" + refund_amount + """\'
                                            , \'""" + ref_coupon_id + """\');"""

            items = execute(query, 'post', conn)

            response['message'] = 'Successful'
            response['result'] = items

            return response, 200
        except:
            raise BadRequest('Bad request, error while inserting new refund.')
        finally:
            disconnect(conn)

        # http://127.0.0.1:4000/api/v2/insertNewRefund
        # https://rqiber37a4.execute-api.us-west-1.amazonaws.com/dev/api/v2/insertNewRefund
        # {
        #     "created_at": "2020-09-10",
        #     "email_id": "test",
        #     "phone_num": "999999999",
        #     "image_url": "bnlah",
        #     "driver_note": "b",
        #     "admin_note": "blah",
        #     "refund_amount": "b",
        #     "ref_coupon_id": "b"
        # }

class Payments(Resource):
    def get(self):
        response = {}
        items = {}
        try:
            conn = connect()

            items = execute('SELECT * FROM jd.payments', 'get', conn)

            response['message'] = 'Successful'
            response['result'] = items

            return response, 200
        except:
            raise BadRequest('Bad request, error while retrieving payments')
        finally:
            disconnect(conn)

class UpdateDeliveryStatus(Resource):
    def post(self):
        response = {}
        try:
            conn = connect()
            data = request.get_json(force=True)

            purchase_uid = data['purchase_uid']
            cmd = data['cmd']
            note = data['note']

            if cmd == 'Delivered':
                query_init = """
                            SELECT purchase_status FROM sf.purchases WHERE purchase_uid = \'""" + purchase_uid + """\'; 
                            """
                items_init = execute(query_init,'get',conn)
                
                if items_init['code'] != 280:
                    items_init['message']  ='check sql query'
                    return items_init
                
                status = items_init['result'][0]['purchase_status']

                if status == 'ACTIVE':
                    query = """
                            UPDATE sf.purchases 
                            SET delivery_status = 'TRUE' 
                            WHERE purchase_uid = \'""" + purchase_uid + """\'; 
                            """
                else:
                    query = """
                            UPDATE sf.purchases 
                            SET 
                            delivery_status = 'TRUE',
                            purchase_status = 'ACTIVE' 
                            WHERE purchase_uid = \'""" + purchase_uid + """\'; 
                            """

            elif cmd == 'Skip':
                
                query = """
                        UPDATE sf.purchases 
                        SET
                        delivery_status = 'SKIP',
                        feedback_notes = \'""" + note + """\'
                        WHERE purchase_uid = \'""" + purchase_uid + """\'; 
                        """

            elif cmd == 'Undo':
                query = """
                        UPDATE sf.purchases 
                        SET
                        delivery_status = 'FALSE'
                        WHERE purchase_uid = \'""" + purchase_uid + """\'; 
                        """

            else:
                return "choose correct option"
            
            items = execute(query,'post',conn)
            return items
        except:
            raise BadRequest('Bad request, error while updating delivery status')
        finally:
            disconnect(conn)

'''
class UpdateDeliveryStatus(Resource):
    def post(self):
        response = {}
        try:
            conn = connect()
            data = request.get_json(force=True)

            purchase_uid = data['purchase_uid']
            delivery_date = data['delivery_date']
            cmd = data['cmd']

            if cmd == 'update':
                query = """UPDATE sf.purchases pu SET delivery_status = 'TRUE' WHERE EXISTS(SELECT delivery_email FROM  
                                    sf.payments pa WHERE pa.pay_purchase_uid = pu.purchase_uid AND pu.purchase_uid = '""" + purchase_uid + """'
                                    AND pa.start_delivery_date = '""" + delivery_date + """');"""
            else:
                query = """UPDATE sf.purchases pu SET delivery_status = 'FALSE' WHERE EXISTS(SELECT delivery_email FROM  
                                    sf.payments pa WHERE pa.pay_purchase_uid = pu.purchase_uid AND pu.purchase_uid = '""" + purchase_uid + """'
                                    AND pa.start_delivery_date = '""" + delivery_date + """');"""

            items = execute(query, 'post', conn)

            response['code'] = items['code']
            response['message'] = 'Successfully updated delivery status'

            return response, 200
        except:
            raise BadRequest('Bad request, error while updating delivery status')
        finally:
            disconnect(conn)

'''
# {
#     "purchase_uid":"400-000114",
#     "delivery_date":"2021-01-31 10:00:00",
#     "cmd":"update"
# }

class GetAWSLink(Resource):
    def post(self):
        response = {}
        try:
            conn = connect()

            uid = request.form.get('purchase_uid')
            img = request.files.get('image')

            key = 'purchase/' + uid
            item_photo_url = helper_upload_img(img, key)

            query = """UPDATE sf.purchases SET delivery_photo = \'""" + item_photo_url + """\' WHERE purchase_uid = \'""" + uid + """\';"""
            items = execute(query, 'post', conn)

            if items['code'] != 281:
                items['message'] = 'An error occured'
                return items

            get_aws_link = """SELECT delivery_photo FROM sf.purchases WHERE purchase_uid = \'""" + uid + """\';"""
            aws_link = execute(get_aws_link, 'get', conn)

            response['message'] = 'Sucessfully retrieved delivery photo'
            response['result'] = aws_link['result']

            return response, 200
        except:
            raise BadRequest('Bad request, error occured while adding delivery photo')
        finally:
            disconnect(conn)

class updateRouteInfo(Resource):
    
    def post(self):
        
        try:

            conn = connect()
            data = request.get_json(force=True)

            route_id = data['route_id']
            purchase_uids = data['purchase_uids']

            query = """
                    SELECT route FROM jd.routes WHERE route_id = \'""" + route_id + """\';
                    """
            items = execute(query,'get',conn)

            if items['code'] != 280:
                items['message'] = 'check sql query'
                return items
            
            print(purchase_uids,type(purchase_uids))
            dict_routes = json.loads(items['result'][0]['route'])
            for key, vals in dict_routes.items():
                print('INSERT-----------------------')
                print(key)
                if vals[0]['purchase_uid'] in purchase_uids:
                    vals[0]['delivery_status'] = 'TRUE'
            dict_routes = str(dict_routes)
            dict_routes = dict_routes.replace("'", '"')
            query_update = """
                            UPDATE jd.routes
                            SET route = \'""" + dict_routes + """\'
                            WHERE route_id = \'""" + route_id + """\';
                            """
            items_update = execute(query_update,'post',conn)

            return items_update

        except:
            raise BadRequest('Bad request, error while updating delivery status')
        finally:
            disconnect(conn)

class updateDriverSchedule(Resource):
    def post(self):
        try:
            conn = connect()
            data = request.get_json(force=True)

            schedule = "'" + str(data['driver_hours']).replace("'", "\"") + "'"

            query = """
                    UPDATE jd.drivers 
                    SET 
                    driver_available_hours =  """ + schedule + """
                    WHERE driver_uid = '""" + data['uid'] + """\';
                    """
            return execute(query,'post',conn)


        except:
            raise BadRequest('Bad request, error while updating delivery schedule')
        finally:
            disconnect(conn)

class drivers_sort_report(Resource):

    def get(self, date, driver_num):

        try:
            conn = connect()

            query_cust = """   
                        SELECT * from jd.routes WHERE driver_num =  \'""" + driver_num + """\' AND shipment_date LIKE \'""" + date + '%' + """\'
                        ORDER BY route_id DESC LIMIT 1;
                        """

            items_cust = execute(query_cust,'get',conn)

            route = json.loads(items_cust['result'][0]['route'])
            

            customers_list = []

            for key,val in route.items():
                # print("in",vals,type(vals))
                vals = val[0]
                if key != "1":
                    customers_list.append(vals['delivery_first_name']+vals['delivery_last_name']+vals['delivery_street']+vals['delivery_unit']) 
            # return items_cust

            query = """
                    SELECT obf.*, pay.start_delivery_date, pay.payment_uid, itm.business_price, itm.item_unit, itm.item_name, bus.business_name
                    FROM sf.orders_by_farm AS obf, sf.payments AS pay, (SELECT * FROM sf.sf_items LEFT JOIN sf.supply ON item_uid = sup_item_uid) AS itm, sf.businesses as bus
                    WHERE obf.purchase_uid = pay.pay_purchase_uid AND obf.item_uid = itm.item_uid AND obf.itm_business_uid = itm.itm_business_uid AND start_delivery_date LIKE \'""" + date + '%' + """\' AND bus.business_uid = obf.itm_business_uid; 
                    """
            items = execute(query, 'get', conn)

            if items['code'] != 280:
                items['message'] = 'check sql query'
                return items
            
            item_dict = {}
            for vals in items['result']:
                if vals['delivery_first_name']+vals['delivery_last_name']+vals['delivery_address']+vals['delivery_unit'] in customers_list:
                    if vals['item_name'] in item_dict:
                        flag = 0
                        # loop through all customers
                        for i,custs in enumerate(item_dict[vals['item_name']]['customers']):
                            if custs['customer_first_name']+custs['customer_last_name']+custs['customer_address']+custs['customer_unit'] in vals['delivery_first_name']+vals['delivery_last_name']+vals['delivery_address']+vals['delivery_unit']:
                                item_dict[vals['item_name']]['customers'][i]['qty'] = int(item_dict[vals['item_name']]['customers'][i]['qty']) + int(vals['qty'])
                                flag = 1
                        if flag == 0:    
                            item_dict[vals['item_name']]['customers'].append({'customer_first_name':vals['delivery_first_name'],
                                        'customer_last_name':vals['delivery_last_name'],'customer_uid':vals['pur_customer_uid'],
                                        'customer_address':vals['delivery_address'],'customer_unit':vals['delivery_unit'],'qty':vals['qty']})
                        item_dict[vals['item_name']]['qty'] = int(item_dict[vals['item_name']]['qty']) + int(vals['qty'])
                        flag = 0
                    
                    else:
                        item_dict[vals['item_name']]  ={}
                        item_dict[vals['item_name']]['customers'] = [{'customer_first_name':vals['delivery_first_name'],
                                    'customer_last_name':vals['delivery_last_name'],'customer_uid':vals['pur_customer_uid'],
                                    'customer_address':vals['delivery_address'],'customer_unit':vals['delivery_unit'],'qty':vals['qty']}]
                        item_dict[vals['item_name']]['qty'] = int(vals['qty']) 
                        item_dict[vals['item_name']]['business_name'] = vals['business_name']
                        item_dict[vals['item_name']]['business_uid'] = vals['itm_business_uid']  
                        item_dict[vals['item_name']]['item'] = vals['name']
                        item_dict[vals['item_name']]['item_uid'] = vals['item_uid']
                        item_dict[vals['item_name']]['item_img'] = vals['img']
                        item_dict[vals['item_name']]['item_unit'] = vals['item_unit']
                        item_dict[vals['item_name']]['item_business_price'] = vals['business_price']
            
            items['result'] = [vals for key, vals in sorted(item_dict.items())]
            return items

        
        except:
            raise BadRequest('Bad request, error while updating delivery schedule')
        finally:
            disconnect(conn)

class updateRouteOrder(Resource):
    def post(self):
        try:
            conn = connect()
            data = request.get_json(force=True)
            print(data)
            route = "'" + str(data['route']).replace("'", "\"") + "'"
            query = """
                    UPDATE jd.routes
                    SET 
                    route =  """ + route + """
                    WHERE route_id = \'""" + data['route_id'] + """\';
                    """
            print(query)
            return execute(query,'post',conn)


        except:
            raise BadRequest('Bad request, error while updating route order')
        finally:
            disconnect(conn)

class sortedProduce(Resource):
    def post(self):
        try:
            conn = connect()
            data = request.get_json(force=True)
            action = data['action']
            route_id = data['route_id']

            if action == 'get':
            
                query = """
                        SELECT sorted_produce FROM jd.routes
                        WHERE route_id = \'""" + route_id + """\';
                        """
                print(query)
                return execute(query,'get',conn)
            
            elif action == 'post':
                produce = data['sorted_produce']
                produce = "'" + str(produce).replace("'", "\"") + "'"
                query = """
                        UPDATE jd.routes
                        SET sorted_produce = """ + produce + """
                        WHERE route_id = \'""" + route_id + """\';
                        """
                print(query)
                return execute(query,'post',conn)
            else:
                return 'choose correct option'

        except:
            raise BadRequest('Bad request, error while updating delivery schedule')
        finally:
            disconnect(conn)

class driverDirections(Resource):
    def post(self):
        try:
            conn = connect()
            data = request.get_json(force=True)
            action = data['action']
            
            route_id = data['route_id']
            
            if action == 'get':
                
                query = """
                        SELECT route_directions FROM jd.routes
                        WHERE route_id = \'""" + route_id + """\';
                        """
                print(query)
                return execute(query,'get',conn)
            
            elif action == 'post':
                directions = data['directions']
                query = """
                        SELECT route_directions FROM jd.routes
                        WHERE route_id = \'""" + route_id + """\';
                        """
                items = execute(query,'get',conn)
                print(items)

                initDirections = items['result'][0]['route_directions']
                print(initDirections,type(initDirections))

                initDirections = json.loads(initDirections)
                print(initDirections,type(initDirections))
                
                initDirections.extend(directions)
                print(initDirections)
                initDirections = "'" + str(initDirections).replace("'", "\"") + "'"
                print(initDirections)

                query = """
                        UPDATE jd.routes
                        SET route_directions = """ + initDirections + """
                        WHERE route_id = \'""" + route_id + """\';
                        """
                print(query)
                return execute(query,'post',conn)
            else:
                return 'choose correct option'

        except:
            raise BadRequest('Bad request, error while updating delivery schedule')
        finally:
            disconnect(conn)


######################################### RIDE SHARE ######################################################## 

class custInfo(Resource):
     def post(self):
        try:
            conn = connect()
            data = request.get_json(force=True)
            action = data['action']
            cust_id = data['cust_id']
            if action == 'get':
                
                query = """
                        SELECT * FROM test.ride_share 
                        WHERE cust_id  = \'""" + cust_id + """\';
                        """
                return execute(query,'get',conn)
            
            elif action == 'post':
                location = data['location']
                location = "'" + str(location).replace("'", "\"") + "'"
                query = """
                        UPDATE test.ride_share
                         SET cust_location = """ + location + """ 
                         WHERE (cust_id = \'""" + cust_id + """\');
                        """
                return execute(query,'post',conn)
            else:
                return 'choose correct option'
        
        except:
            raise BadRequest('Bad request, error while calling cust info')
        finally:
            disconnect(conn)



class getDriver(Resource):
    def get(self,cust_id,radius):
        try:
            conn = connect()
            query = """
                    SELECT cust_location FROM test.ride_share
                    WHERE cust_id = \'""" + cust_id + """\';
                    """
            items = execute(query,'get',conn)
            if items['code'] != 280:
                items['message'] = 'check sql query'
                return items
            passanger_location = json.loads(items['result'][0]['cust_location'])
            
            from haversine import haversine, Unit
            passanger = (passanger_location['lat'], passanger_location['long']) # (lat, lon)
            #get drivers who are online and free

            query = """
                    SELECT * FROM test.ride_share
                    WHERE cust_type = 'DRIVER' AND cust_available = 'TRUE';
                    """
            items = execute(query,'get',conn)
            if items['code'] != 280:
                items['message'] = 'check sql query'
                return items
            avail_drivers = []
            for drivers in items['result']:
                driver_location = json.loads(drivers['cust_location'])
                driver = (driver_location['lat'], driver_location['long'])

                distance = haversine(passanger, driver, unit=Unit.MILES)
                print(distance)
                if distance <= float(radius):
                    avail_drivers.append(drivers)

            items['result'] = avail_drivers
            return items
        
        except:
            raise BadRequest('Bad request, error while calling get driver')
        finally:
            disconnect(conn)

#################################################################################################

# Api Routes
api.add_resource(SignUp, '/api/v2/SignUp')
api.add_resource(UpdateSocialProfile, '/api/v2/UpdateSocialProfile')
api.add_resource(UpdateDirectProfile, '/api/v2/UpdateDirectProfile')

api.add_resource(AccountSalt, '/api/v2/AccountSalt')
api.add_resource(Login, '/api/v2/Login')
api.add_resource(AppleLogin, '/api/v2/AppleLogin', '/')
#api.add_resource(GoogleLogin, '/api/v2/GoogleLogin', '/')
api.add_resource(driver_route_day, '/api/v2/driver_route_day')
api.add_resource(Customers, '/api/v2/Customers')
api.add_resource(Purchases, '/api/v2/Purchases')
api.add_resource(Businesses, '/api/v2/Businesses')
api.add_resource(InsertNewBusiness, '/api/v2/insertNewBusiness')
api.add_resource(GetBusinessConstraints,'/api/v2/getBusinessConstraints/<string:business_uid>')
api.add_resource(SpecificDriver, '/api/v2/SpecificDriver')
api.add_resource(Drivers, '/api/v2/Drivers')
api.add_resource(UpdateDriverID, '/api/v2/updateDriverID/<string:driver_id>/<string:route_id>')
api.add_resource(GetCustomersByBusiness,'/api/v2/getCustomersByBusiness/<string:business_uid>')
api.add_resource(GetVehicles, '/api/v2/getVehicles')
api.add_resource(GetCustomersNotOrderFromBusiness, '/api/v2/getCustomersNotOrderFromBusiness/<string:business_uid>')
api.add_resource(NewDriver, '/api/v2/insertNewDriver')
api.add_resource(GetRoutes, '/api/v2/GetRoutes')
api.add_resource(GetRouteInfo, '/api/v2/GetRouteInfo')
api.add_resource(GetCoupons, '/api/v2/getCoupons')
api.add_resource(InsertNewCoupon, '/api/v2/insertNewCoupon')
api.add_resource(IncreaseNumCouponUsed, '/api/v2/increaseCouponNum')
api.add_resource(DisableCoupon, '/api/v2/disableCoupon')
api.add_resource(GetRefunds, '/api/v2/getRefunds')
api.add_resource(NewRefund, '/api/v2/insertNewRefund')
api.add_resource(Payments, '/api/v2/Payments')
api.add_resource(UpdateDeliveryStatus, '/api/v2/UpdateDeliveryStatus')
api.add_resource(GetAWSLink, '/api/v2/GetAWSLink')
api.add_resource(updateRouteInfo, '/api/v2/updateRouteInfo')
api.add_resource(updateDriverSchedule, '/api/v2/updateDriverSchedule')
api.add_resource(drivers_sort_report, '/api/v2/drivers_sort_report/<string:date>,<string:driver_num>')
api.add_resource(updateRouteOrder, '/api/v2/updateRouteOrder')
api.add_resource(sortedProduce, '/api/v2/sortedProduce')
api.add_resource(driverDirections, '/api/v2/driverDirections')






############################################ RIDE SHARE

api.add_resource(custInfo, '/api/v2/custInfo')
api.add_resource(getDriver, '/api/v2/getDriver/<string:cust_id>,<string:radius>')

############################################

#Driver SignUp and Login Routes



if __name__ == '__main__':
    app.run(host='127.0.0.1', port=4005)
