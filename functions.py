from config import getKey
from functools import wraps
from flask import render_template, request, session
import httplib2

# decorate specific routes to require login
# http://flask.pocoo.org/docs/1.0/patterns/viewdecorators/
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("userID") is None:
            # if user is not logged in, redirect to login page
            return render_template('login.html', message='Please login first.')
        return f(*args, **kwargs)
    return decorated_function

# query for stock with symbol
def stockquery(symbol):
    connection = httplib2.HTTPSConnectionWithTimeout('sandbox.tradier.com', 443, timeout = 30)
    headers = {"Accept":"application/json",
           "Authorization":"Bearer " + getKey()}

    connection.request('GET', '/v1/markets/quotes?symbols=' + symbol, None, headers)
    try:
        response = connection.getresponse()
        content = response.read()
        # Success
        print('Response status ' + str(response.status))
        print(content)
    except:
        # Exception
        print('Exception during request')

