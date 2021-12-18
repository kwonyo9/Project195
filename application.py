# -*- coding: utf-8 -*-


from flask import Flask, render_template, request, redirect, session
from models import db, roomData, temp, users, outdoor, ml
from decimal import Decimal
from boto3.dynamodb.conditions import Key, Attr
import json
import hashlib

application = Flask(__name__)
application.config['DYNAMO_SESSION'] = db
application.secret_key = "mahbubfrr"
application._static_folder = "static"


@application.route('/')
def index():
    return render_template('index.html')


@application.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        passwd = request.form['password']
        passwd = hashlib.sha512((passwd + email).encode('utf-8')).hexdigest()
        users.put_item(
            Item={
                'name': name,
                'email': email,
                'passwd': passwd
            }
        )
        msg = "Registration Complete. Please Login to your account !"

        return render_template('login.html', msg=msg)
    return render_template('index.html')


def verify_user(user_email, password):
    query = users.query(
        KeyConditionExpression=Key('email').eq(user_email)
    )
    try:
        user = query['Items'][0]
        passwd = user['passwd']
        salt = user['email']
        generate_hash = hashlib.sha512((password + salt).encode('utf-8')).hexdigest()
        if generate_hash == passwd:
            return user["name"]
        else:
            return None
    except Exception as err:
        print("Verification Error", str(err))
        return None


def get_item(tableobj, key, name):
    try:
        return tableobj.query(KeyConditionExpression=Key(key).eq(name))['Items']
    except Exception as e:
        print(e)
        return None


def get_all_live():
    room_data = get_item(roomData, 'deviceID', 'room01')[0]
    outdoor_data = get_item(outdoor, 'deviceID', 'roof1')[0]
    ml_data = get_item(ml, 'name', 'comfortable_temp')[0]
    dataset = [room_data,outdoor_data,ml_data]
    for i in dataset:
        for k,v in i.items():
            if isinstance(v, Decimal):
                i[k] = float(v)
    return dataset


@application.route('/login', methods=['GET', 'POST'])
def login():
    warning = False
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        is_verified = verify_user(email, password)
        if is_verified:
            session["user"] = is_verified
            return redirect("/home")
        else:
            warning = True
    return render_template('login.html', warning=warning)


@application.route('/home')
def home():
    user_name = None
    print(session['user'])
    dataset = get_all_live()
    ctemp = get_item(temp, "nodeName", "livenode")[0]['setTemp']
    try:
        user_name = session["user"]
    except:
        pass
    if not session['user']:
        return redirect("/login")
    else:
        return render_template('home.html', user_name=user_name, ctemp=ctemp, data=dataset)



@application.route('/livenode', methods=['GET'])
def livenode():
    return dict(data=get_all_live())


@application.route('/getdata', methods=['GET', 'POST'])
def getdata():
    if request.method == "POST":
        data = request.form['setTemp']
        print(data)
        temp.put_item(
            Item={
                'nodeName': 'livenode',
                'setTemp': data

            }
        )
        return data
    else:
        key = request.args.get('key')
        value = request.args.get("value")
        data = get_item(roomData, key, value)[0]
        for k,val in data.items():
            if isinstance(val, Decimal):
                data[k] = float(val)
        return data

@application.route('/logout', methods=['GET'])
def logout():
    session['user']= False
    return redirect("/home")


if __name__ == "__main__":
    application.run(debug=True)

    # application.run(debug=True,host='0.0.0.0.0',port='8080')
