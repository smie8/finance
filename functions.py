# from config import getKey
from functools import wraps
from flask import render_template, request, session
import httplib2
import json
import os

# get api key from env variables
api_key = os.getenv("API_KEY")

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
    # headers = {"Accept":"application/json",
    #        "Authorization":"Bearer " + getKey()}
    # TODO
    headers = {"Accept":"application/json",
        "Authorization":"Bearer " + api_key}

    connection.request('GET', '/v1/markets/quotes?symbols=' + symbol, None, headers)
    try:
        response = connection.getresponse()
        respContent = response.read()
        # Success
        print('Response status ' + str(response.status))
        respContent = respContent.decode('UTF-8')
        # to json
        respContent = json.loads(respContent)
        # let's return the response's data as dict
        stockData = {
            'company': respContent['quotes']['quote']['description'],
            'price': respContent['quotes']['quote']['last'],
            'symbol': respContent['quotes']['quote']['symbol']

        }

        return stockData

    except:
        # Exception
        print('Exception during request')

