from flask import Flask, render_template, request
from flask_sqlalchemy import SQLAlchemy

# initialize the app
app = Flask(__name__)

ENV = 'production'

# sqlalchemy config
if ENV == 'development':
    app.debug = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:grespost@localhost/finance'
else:
    app.debug = False
    app.config['SQLALCHEMY_DATABASE_URI'] = 'postgres://oarxlexrxojpdg:28b0f1651cc8790a64949c6804b29242763b855372b782d344c387997e1645f4@ec2-35-173-94-156.compute-1.amazonaws.com:5432/d9l1e9pirshh41'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# database-object
db = SQLAlchemy(app)

# model
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

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/signup', methods=['POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        password2 = request.form['password2']
        initMoney = 10000

        print('username: ' + username, 'password: ' + password)

        # check if password was re-entered correctly
        if password != password2:
            return render_template('index.html', message='Passwords do not match.')

        if username != '':
            # if user does not exist, create new user
            if db.session.query(Users).filter(Users.username == username).count() == 0:
                data = Users(username, password, initMoney)
                db.session.add(data)
                db.session.commit()

                return render_template('main.html', username=username, message="You have logged in successfully.")
            return render_template('index.html', message='This username is taken.')

        return render_template('index.html', message='Username missing.')

if __name__ == '__main__':
    app.run()