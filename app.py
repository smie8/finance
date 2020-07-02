from flask import Flask, render_template, request, redirect, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_session import Session
from functions import stockquery, login_required
from passlib.hash import sha256_crypt
# from config import getPostgresUri
import datetime
import os

# initialize/configure the app
app = Flask(__name__)

# session config
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# if ENV is other than 'dev' -> app is using heroku's database
ENV = 'dev'
# ENV = 'heroku'
# heroku's env variables:
#   heroku config:set POSTGRES_URI=insert-key-here

# sqlalchemy config
if ENV == 'dev':
    app.debug = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:grespost@localhost/finance'
else:
    app.debug = False
    app.config['SQLALCHEMY_DATABASE_URI'] = pg_uri
    # TODO app.config['SQLALCHEMY_DATABASE_URI'] = pg_uri

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
    name = db.Column(db.String(250))

    def __init__(self, userid, symbol, count, name):
        self.userid = userid
        self.symbol = symbol
        self.count = count
        self.name = name

class History(db.Model):
    __tablename__ = 'history'
    id = db.Column(db.Integer, primary_key=True)
    userid = db.Column(db.Integer)
    symbol = db.Column(db.String(20))
    count = db.Column(db.Integer)
    price = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.String(200))
    total = db.Column(db.Float)
    name = db.Column(db.String(250))
    
    def __init__(self, userid, symbol, count, price, timestamp, total, name):
        self.userid = userid
        self.symbol = symbol
        self.count = count
        self.price = price
        self.timestamp = timestamp
        self.total = total
        self.name = name

# routes
@app.route('/')
def index():

    if not session.get('userID'):
        return render_template('login.html')
    else:
        return redirect('/dashboard')        

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
            flash('Please enter username to login.')
            return redirect('/login')
        elif not password:
            flash('Please enter password.')
            return redirect('/login')

        # exception handling in case user is not found in database
        try:
            # let's find the user from db and check hashed password
            user = db.session.query(Users).filter(Users.username == username)

            if sha256_crypt.verify(password, user[0].password):
                print('Correct password.') 
                # let's save logged in user into session
                session['userID'] = user[0].id
                flash('Logged in successfully as user "' + username + '"')
                return redirect('/dashboard')
            else:
                flash('Incorrect password.')
                return redirect('/login')
        except:
            # TODO bug
            flash('User "' + username + '" does not exist.')
            return redirect('/login')


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

        # username validation
        if username:
            # if user does not exist, create new user
            if db.session.query(Users).filter(Users.username == username).count() == 0:

                # password validation
                if not password:
                    return render_template('signup.html', message='Password missing.')
                elif password != password2:
                    return render_template('signup.html', message='Passwords do not match.')
                elif len(password) < 8:
                    return render_template('signup.html', message='Password must contain at least 8 characters.')

                # hash password
                password = sha256_crypt.encrypt(password)

                data = Users(username, password, initMoney)
                db.session.add(data)
                db.session.commit()

                # log in as this new user
                try:
                    user = db.session.query(Users).filter(Users.username == username)
                    session['userID'] = user[0].id
                except:
                    return render_template('login.html', message='Something went wrong.')
                flash('Created and logged in user "' + username + '". You have been given $10,000 in cash.')
                return redirect('/dashboard')
            
            return render_template('signup.html', message='This username is taken.')
        else:
            return render_template('signup.html', message='Username missing.')

@app.route('/quote', methods=['GET', 'POST'])
@login_required
def quote():

    if request.method == 'GET':
        return render_template('quote.html')

    if request.method == 'POST':
        symbol = request.form['symbol']
        try:
            data = stockquery(symbol)
            msg = 'Price for ' + str(data['company']) + ' is $' + str(data['price'])
            return render_template('quote.html', message=msg)
        except:
            return render_template('quote.html', message='Stock not found with symbol \"' + symbol + '\"')

@app.route('/buy', methods=['GET', 'POST'])
@login_required
def buy():

    if request.method == 'GET':
        return render_template('buy.html')

    if request.method == 'POST':
        try:
            symbol = request.form['symbol']
            count = int(request.form['count'])
            userid = session['userID']
            timestamp = str(datetime.datetime.now())
            timestamp = timestamp.split('.')
            timestamp = timestamp[0]

            data = stockquery(symbol)
            price = data['price']
            name = str(data['company'])
            cost = price * count # TODO times count
            msg = 'Bought ' + str(count) + ' share(s) of company ' + name
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
                data = Stocks(userid, symbol, count, name)
                db.session.add(data)
            else:
                stock[0].count += count
                db.session.commit()
            print('stocks updated')

            total = round(price * count, 2)
            price = round(price, 2)
            # commit to history database
            data = History(userid, symbol, count, price, timestamp, total, name)
            db.session.add(data)
            db.session.commit()
            print('history updated')

            return render_template('buy.html', message=msg)
            
        except:
            return render_template('buy.html', message='Something went wrong.')
 

@app.route('/sell', methods=['GET', 'POST'])
@login_required
def sell():

    userid = session['userID']

    if request.method == 'GET':
        # get all user's shares from database and pass them to select menu's options
        symbols = db.session.query(Stocks).filter(Stocks.userid == userid)
        return render_template('sell.html', symbols = symbols)

    if request.method == 'POST':
        try:
            symbol = request.form['symbol']
            count = int(request.form['count'])
            timestamp = str(datetime.datetime.now())
            timestamp = timestamp.split('.')
            timestamp = timestamp[0]

            data = stockquery(symbol)
            price = data['price']
            cost = price * count
            name = str(data['company'])
            msg = 'Sold ' + str(count) + ' share(s) of stock ' + name
            user = db.session.query(Users).filter(Users.id == userid)
            money = user[0].money

            # count should be > 0
            if count < 1: 
                flash('Number should be positive integer.')
                return redirect('/sell')

            # update stocks count. if stocks == 0, delete row
            stock = db.session.query(Stocks).filter(Stocks.userid == userid, Stocks.symbol == symbol).first()
            if stock.count - count >= 0:
                # TODO , does not work
                # if no shares left -> delete, else update
                if stock.count - count == 0:
                    print('no shares left')
                    db.session.delete(stock)
                    db.session.commit()
                    print('shares deleted')
                else:
                    stock.count -= count
                    db.session.commit()
                    print('shares substracted from inventory')

                # add money to user
                user[0].money += cost
                db.session.commit()
                print('money added')

            elif stock.count - count < 0:
                flash('You do not own that many shares.')
                return redirect('/sell')

            total = round(price * count, 2)
            count *= -1 # because user is selling
            price = round(price, 2)
            # commit to history database
            data = History(userid, symbol, count, price, timestamp, total, name)
            db.session.add(data)
            db.session.commit()
            print('history updated')

            flash(msg)
            return redirect('/sell')
            
        except:
            flash('Something went wrong.')
            return redirect('/sell')

@app.route('/history')
@login_required
def history():
    # fetch user's transaction history
    userid = session['userID']
    try:
        stocks = db.session.query(History).filter(History.userid == userid)
        return render_template('history.html', stocks=stocks)
    except:
        print('Something went wrong')
        return render_template('history.html')


@app.route('/dashboard')
@login_required
def dashboard():
    userid = session['userID']
    try:
        # fetch user's money
        user = db.session.query(Users).filter(Users.id == userid).first()
        money = user.money

        # fetch stock owned by user
        stocks = db.session.query(Stocks).filter(Stocks.userid == userid)
        # stocks list
        stocksList = []
        # total value
        total = 0

        for stock in stocks:
            data = stockquery(stock.symbol)
            print(data)
            price = data['price']
            stock.price = round(price, 2)
            stock.total = round(stock.count * stock.price, 2)
            stockDict = {
                "symbol": stock.symbol,
                "name": stock.name,
                "price": stock.price,
                "count": stock.count,
                "total": stock.total
            }
            # put dictionary to list
            stocksList.append(stockDict)
            total += stock.total

        total = round(total, 2)
        totalmoney = round(total + money, 2)

        return render_template('dashboard.html', stocks=stocksList, total=total, money=money, totalmoney=totalmoney)
    except:
        print('Something went wrong')
        return render_template('dashboard.html')
 
@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out.')
    return redirect("/")


# if this file is executed as main program, run flask app
if __name__ == '__main__':
    app.run()