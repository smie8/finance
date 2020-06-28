from flask import Flask, render_template, request, redirect, session
from flask_sqlalchemy import SQLAlchemy
from flask_session import Session
from functions import stockquery, login_required
from passlib.hash import sha256_crypt
from config import getPostgresUri
import datetime

# initialize/configure the app
app = Flask(__name__)

# session config
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# if ENV is other than 'dev' -> app is using heroku's database
ENV = 'dev'
# ENV = 'production'

# sqlalchemy config
if ENV == 'dev':
    app.debug = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:grespost@localhost/finance'
else:
    app.debug = False
    app.config['SQLALCHEMY_DATABASE_URI'] = getPostgresUri()

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# database-object
db = SQLAlchemy(app)

# database "table models"
class Users(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(250), unique=True)
    password = db.Column(db.String(250), unique=False)
    money = db.Column(db.Integer)

    # "constructor"
    def __init__(self, username, password, money):
        self.username = username
        self.password = password
        self.money = money

class Stocks(db.Model):
    __tablename__ = 'stocks'
    id = db.Column(db.Integer, primary_key=True)
    userid = db.Column(db.Integer)
    symbol = db.Column(db.String(20))
    count = db.Column(db.Integer)

    def __init__(self, userid, symbol, count):
        self.userid = userid
        self.symbol = symbol
        self.count = count

class History(db.Model):
    __tablename__ = 'history'
    id = db.Column(db.Integer, primary_key=True)
    userid = db.Column(db.Integer)
    symbol = db.Column(db.String(20))
    count = db.Column(db.Integer)
    price = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.String(200))
    
    def __init__(self, userid, symbol, count, price, timestamp):
        self.userid = userid
        self.symbol = symbol
        self.count = count
        self.price = price
        self.timestamp = timestamp

# routes
@app.route('/')
def index():

    # TODO

    return render_template('login.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    
    if request.method == 'GET':
        return render_template('login.html')
    elif request.method == 'POST':
        # makes sure nobody is logged in
        session.clear()

        username = request.form['username_login']
        password = request.form['password_login']

        if not username:
            return render_template('login.html', message='Please enter username to login.')
        elif not password:
            return render_template('login.html', message='Please enter password.')

        # TODO password hashing

        # exception handling in case user is not found in database
        try:
            user = db.session.query(Users).filter(Users.username == username)
            # if password == user[0].password:
            if sha256_crypt.verify(password, user[0].password):
                print('Correct password.') 
                session['userID'] = user[0].id
                # return redirect('/dashboard') TODO How to get redirect to work?
                return render_template('dashboard.html', message = 'Logged in successfully.')
            else:
                print('Incorrect password.')
                return render_template('login.html', message='Incorrect password.')
        except:
            return render_template('login.html', message='Incorrect username.')



@app.route('/signup', methods=['GET', 'POST'])
def signup():

    if request.method == 'GET':
        return render_template('signup.html')

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        password2 = request.form['password2']
        initMoney = 10000

        print('username: ' + username, 'password: ' + password)

        # password validation
        if not password:
            return render_template('signup.html', message='Password missing.')
        elif password != password2:
            return render_template('signup.html', message='Passwords do not match.')
        elif len(password) < 8:
            return render_template('signup.html', message='Password must contain at least 8 characters.')

        # hash
        password = sha256_crypt.encrypt(password)

        # username validation
        if username:
            # if user does not exist, create new user
            if db.session.query(Users).filter(Users.username == username).count() == 0:
                data = Users(username, password, initMoney)
                db.session.add(data)
                db.session.commit()

                # log in as this new user
                try:
                    user = db.session.query(Users).filter(Users.username == username)
                    session['userID'] = user[0].id
                except:
                    return render_template('login.html', message='Something went wrong.')
                return render_template('main.html', message='User ' + username + ' created. You have logged in successfully.')
            
            return render_template('signup.html', message='This username is taken.')
        else:
            return render_template('signup.html', message='Username missing.')

@app.route('/quote', methods=['GET', 'POST'])
def quote():

    if request.method == 'GET':
        return render_template('quote.html')

    if request.method == 'POST':
        symbol = request.form['symbol']
        try:
            data = stockquery(symbol)
            msg = 'Price for ' + str(data['company']) + ' is ' + str(data['price'])
            return render_template('quote.html', message=msg)
        except:
            return render_template('quote.html', message='Stock not found with symbol \"' + symbol + '\"')

@app.route('/buy', methods=['GET', 'POST'])
def buy():

    if request.method == 'GET':
        return render_template('buy.html')

    if request.method == 'POST':
        symbol = request.form['symbol']
        count = int(request.form['count'])
        userid = session['userID']
        timestamp = str(datetime.datetime.now())

        try:
            data = stockquery(symbol)
            price = data['price']
            cost = price * count # TODO times count
            msg = 'Bought ' + str(count) + ' stocks of company ' + str(data['company'])
            user = db.session.query(Users).filter(Users.id == userid)
            money = user[0].money

            # count should be > 0
            if count < 1: 
                return render_template('buy.html', message='Number should be positive integer.')

            # checking if user have sufficient funds for payment
            if cost > money:
                return render_template('buy.html', message='Could not buy. Insufficient funds.')

            # substract money from user
            user[0].money -= cost
            db.session.commit()
            print('money substracted')

            # create row to stocks database if user has no company's stocks, else update
            stock = db.session.query(Stocks).filter(Stocks.userid == userid, Stocks.symbol == symbol)
            if stock.count() == 0:
                data = Stocks(userid, symbol, count)
                db.session.add(data)
            else:
                stock[0].count += count
                db.session.commit()
            print('stocks updated')

            # commit to history database
            data = History(userid, symbol, count, price, timestamp)
            db.session.add(data)
            db.session.commit()
            print('history updated')

            return render_template('buy.html', message=msg)
            
        except:
            return render_template('buy.html', message='Something went wrong.')
 

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')
 
@app.route('/logout')
def logout():
    session.clear()
    return redirect("/")


# if this file is executed as main program, run flask app
if __name__ == '__main__':
    app.run()