from flask import Flask, render_template, request, redirect, url_for
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Categories, Items, Users
from flask import session as login_session

# imports for the login integration with oauth
# flow_from_client_secrets creates a flow object with clientsecrets.json file
from oauth2client.client import flow_from_clientsecrets
# If there is an error while exchanging authorisation code for access token FlowExchangeError can be used to catch it.
from oauth2client.client import FlowExchangeError
import httplib2
import json
# make_response converts return value from a function to send off to client.
from flask import make_response
import requests

# Getting details from google client_secrets.json file
CLIENT_ID = json.loads(open('client_secrets.json', 'r').read())['web']['client_id']

# Database connection and session creation goes here
engine = create_engine('postgresql://appsys:appsys@localhost:5432/catalog')
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()

app = Flask('__name__')


# Sign in functions start here
@app.route('/login')
def showLogin():
    state = 'SDFLKJFlk32laskdvLK'
    login_session['state'] = state
    return render_template('login.html', STATE=state)


@app.route('/gconnect', methods=['POST'])
def gconnect():
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    code = request.data
    try:
        # getting credential object by providing authorization code
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code) # This function exchages authorisation code for credential object.
    except FlowExchangeError:
        response = make_response(json.dumps('Failed to upgrade the authorisation code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Checking if the access token is valide with google server.
    access_token = credentials.access_token
    print access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s' % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    print result.get('error')
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response
    # checking if google plus ids match
    gplus_id = credentials.id_token['sub']
    print gplus_id
    print result
    if result['user_id'] != gplus_id:
        response = make_response(json.dumps("Token's userid does not mathc user's userid"), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # checking if client_id match
    if result['issued_to'] != CLIENT_ID:
        response = make_response(json.dumps("Token's client Id does not match with apps"), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Checking if user is already logged in 
    stored_credentials = login_session.get('credentials')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_credentials is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps("Current user is already connected"), 200)
        response.headers['Content-Type'] = 'application/json'
        return response
    # storing the access token in session for later use
    login_session['credentials'] = credentials
    login_session['gplus_id'] = gplus_id
    # Get user info
    userinfo_url = 'https://www.googleapis.com/oauth2/v1/userinfo'
    params = {'access_token':credentials.access_token, 'alt':'json'}
    answer = requests.get(userinfo_url, params=params)
    data = json.loads(answer.text)
    # Getting users info in login session
    login_session['username'] = data["name"]
    login_session['picture'] = data["picture"]
    login_session['email'] = data["email"]
    print login_session['username']
    return login_session['username']

# Logging out users
@app.route('/gdisconnect')
def gdisconnect():
    # disconnect the connected user
    credentials = login_session['credentials']
    if credentials is None:
        response = make_response(json.dumps('Current user is not connected'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    access_token = credentials.access_token
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request.get(url, 'GET')[0]
    if result['status'] == '200':
        # Reset the user's session
        del login_session['credentials']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        del login_session['gplus_id']

        response = make_response(json.dumps('Successfully disconnected'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response
    else:
        response = make_response(json.dumps('Failed to revoke the user token'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response



# Application operation functions start here
@app.route('/')
@app.route('/categories')
def home():
    categories = session.query(Categories).order_by(Categories.name).all()
    # latest_items = session.query(Items).order_by(Items.created_on.desc()).limit(10)
    latest_items = session.query(Items).join('categories').order_by(Items.created_on.desc()).limit(10)
    return render_template("home_page.html",
                           categories=categories,
                           latest_items=latest_items
                           )


@app.route('/categories/new', methods=['GET', 'POST'])
def create_category():
    if request.method == 'GET':
        return render_template("new_category.html", category=None)
    else:
        category = request.form['new_category']
        new_category = Categories(name=category)
        session.add(new_category)
        session.commit()
        return redirect(url_for('home'))


@app.route('/categories/<string:category_name>/edit', methods=['GET', 'POST'])
def edit_category(category_name):
    category = session.query(Categories).filter_by(name=category_name).one()
    if request.method == 'GET':
        return render_template('new_category.html', category=category)
    else:
        new_name = request.form['new_category']
        category.name = new_name
        session.add(category)
        session.commit()
        return redirect(url_for('home'))


@app.route('/categories/<string:category_name>/items')
def category_items(category_name):
    category = session.query(Categories).filter_by(name=category_name).one()
    items = session.query(Items).filter_by(category_id=category.id).all()
    return render_template('category_items.html',
                           category=category,
                           items=items,
                           )


@app.route('/categories/items/new', methods=['GET', 'POST'])
@app.route('/categories/<string:category_name>/items/new', methods=['GET', 'POST'])
def create_item(category_name=None):
    # print category_name
    if category_name:
        category = session.query(Categories).filter_by(name=category_name).one()
        all_categories = None
    else:
        category= None
        all_categories = session.query(Categories).all()
    if request.method == 'GET':
        return render_template('new_item.html',
                               category=category,
                               item=None,
                               all_categories=all_categories
                               )
    else:

        item_name = request.form['new_item_name']
        item_desc = request.form['new_item_desc']
        # print category.name
        selected_id = int(request.form['selected_category'])
        # print selected_id
        if not category:
            category = session.query(Categories).filter_by(id=selected_id).one()
        elif category.id != selected_id:
            category = session.query(Categories).filter_by(id=selected_id).one()
        new_item = Items(name=item_name,
                         description=item_desc,
                         category_id=category.id)
        session.add(new_item)
        session.commit()
        return redirect(url_for('home'))


@app.route('/categories/<string:category_name>/items/<string:item_name>/edit', methods=['GET', 'POST'])
def edit_item(category_name, item_name):
    category = session.query(Categories).filter_by(name=category_name).one()
    item = session.query(Items).filter_by(name=item_name).one()
    if request.method == 'GET':
        return render_template('new_item.html',
                               category=category,
                               item=item
                               )
    else:
        item_name = request.form['new_item_name']
        item_desc = request.form['new_item_desc']
        item.name = item_name
        item.description = item_desc
        session.add(item)
        session.commit()
        return redirect(url_for('category_items', category_name=category_name))


if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=8080)
