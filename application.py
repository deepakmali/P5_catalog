from flask import Flask, render_template, request
from flask import redirect, url_for, flash, jsonify
from sqlalchemy import create_engine, and_
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Categories, Items, Users
from flask import session as login_session
import random
import string
# imports for the login integration with oauth
# flow_from_client_secrets creates a flow object with clientsecrets.json file
from oauth2client.client import flow_from_clientsecrets
# If there is an error while exchanging authorisation code for access
# token FlowExchangeError can be used to catch it.
from oauth2client.client import FlowExchangeError
import httplib2
import json
# make_response converts return value from a function to send off to client.
from flask import make_response
import requests

# Getting details from google client_secrets.json file
CLIENT_ID = json.loads(open('client_secrets.json', 'r').read())[
    'web']['client_id']
APPUSER_ID = None

#
# Database connection and session creation goes here
engine = create_engine('postgresql://appsys:appsys@localhost:5432/catalog')
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()

app = Flask('__name__')


# creating user and returning the id, if already exists, just return userid
def create_user(login_session):
    user = Users()
    user.name = login_session['name']
    user.email = login_session['email']
    user.picture = login_session['picture']
    session.add(user)
    session.commit()
    user = session.query(Users).filter_by(email=login_session['email']).one()
    return user

# get userid


def get_userid(login_session):
    user = session.query(Users).filter_by(email=login_session['email']).first()
    if not user:
        user = create_user(login_session)
    # print 'user'
    # print user.id
    return user.id


# check if user is logged in and route to login page if not logged in
def isUserLoggedIn():
    # global APPUSER_ID
    # print 'test'
    # print APPUSER_ID
    if APPUSER_ID:
        user = session.query(Users).filter_by(id=APPUSER_ID).first()
        if user:
            return True
    return False


# Sign in functions start here
@app.route('/login')
def showLogin():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
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
        # This function exchages authorisation code for credential object.
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorisation code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Checking if the access token is valide with google server.
    access_token = credentials.access_token
    # print access_token
    url = (
        'https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s' %
        access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # print result.get('error')
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response
    # checking if google plus ids match
    gplus_id = credentials.id_token['sub']
    # print gplus_id
    # print result
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's userid does not mathc user's userid"), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # checking if client_id match
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client Id does not match with apps"), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Checking if user is already logged in
    stored_credentials = login_session.get('credentials')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_credentials is not None and gplus_id == stored_gplus_id:
        response = make_response(
            json.dumps("Current user is already connected"), 200)
        response.headers['Content-Type'] = 'application/json'
        return response
    # storing the access token in session for later use
    login_session['credentials'] = credentials
    login_session['gplus_id'] = gplus_id
    # Get user info
    userinfo_url = 'https://www.googleapis.com/oauth2/v1/userinfo'
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)
    data = json.loads(answer.text)
    # Getting users info in login session
    login_session['provider'] = 'google'
    login_session['name'] = data["name"]
    login_session['picture'] = data["picture"]
    login_session['email'] = data["email"]
    # print login_session['name']
    global APPUSER_ID
    APPUSER_ID = get_userid(login_session)
    login_session['logged'] = True
    # print 'in gonnect'
    # print APPUSER_ID
    return login_session['name']

# Logging out users


@app.route('/gdisconnect')
def gdisconnect():
    # disconnect the connected user
    credentials = login_session['credentials']
    if credentials is None:
        response = make_response(
            json.dumps('Current user is not connected'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    access_token = credentials.access_token
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    if result['status'] == '200':
        # Reset the user's session
        del login_session['credentials']
        del login_session['name']
        del login_session['email']
        del login_session['picture']
        del login_session['gplus_id']
        global APPUSER_ID
        APPUSER_ID = None
        login_session['logged'] = False

        response = make_response(json.dumps('Successfully disconnected'), 200)
        response.headers['Content-Type'] = 'application/json'
        flash('Successfully Logged out')
        return redirect(url_for('home'))
    else:
        response = make_response(
            json.dumps('Failed to revoke the user token'), 401)
        response.headers['Content-Type'] = 'application/json'
        return redirect(url_for('home'))


# connecting with facebook. This will be called in the ajax call from
# login page
@app.route('/fbconnect', methods=['POST'])
def fbconnect():
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    access_token = request.data
    app_id = json.loads(
        open(
            'fb_client_secrets.json',
            'r').read())['web']['app_id']
    app_secret = json.loads(open('fb_client_secrets.json', 'r').read())[
        'web']['app_secret']
    url = ('https://graph.facebook.com/oauth/access_token?'
           'grant_type=fb_exchange_token&client_id=%s&client_secret=%s'
           '&fb_exchange_token=%s') % (app_id, app_secret, access_token)
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]

    userinfo_url = "https://graph.facebook.com/v2.8/me"

    data = json.loads(result)
    token = 'access_token=' + data['access_token']

    url = 'https://graph.facebook.com/v2.4/me?%s&fields=name,id,email' % token
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    # store the results
    data = json.loads(result)
    # print data
    login_session['provider'] = 'facebook'
    # print data
    login_session['email'] = data['email']
    login_session['username'] = data['name']
    login_session['facebook_id'] = data['id']
    # The token must be stored in the login_session in order to properly logout
    # let's strip out the information before the equals sign in our token
    stored_token = token.split("=")[1]
    login_session['access_token'] = stored_token

    # Get user picture
    url = 'https://graph.facebook.com/v2.4/me/picture?%s&redirect=0&height=200&width=200' % token  # NOQA
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    data = json.loads(result)

    login_session['picture'] = data["data"]["url"]
    global APPUSER_ID
    APPUSER_ID = get_userid(login_session)
    login_session['logged'] = True
    return login_session['username']


@app.route('/fbdisconnect')
def fbdisconnect():
    facebook_id = login_session['facebook_id']
    # The access token must me included to successfully logout
    access_token = login_session['access_token']
    url = 'https://graph.facebook.com/%s/permissions?access_token=%s' % (
        facebook_id, access_token)
    h = httplib2.Http()
    result = h.request(url, 'DELETE')[1]
    global APPUSER_ID
    APPUSER_ID = None
    login_session['logged'] = False
    flash('Successfully Logged out')
    return redirect(url_for('home'))


@app.route('/logout')
def logout():
    if login_session['provider'] == 'facebook':
        return redirect(url_for('fbdisconnect'))
    else:
        return redirect(url_for('gdisconnect'))

# Application operation functions start here


@app.route('/')
@app.route('/categories')
def home():
    categories = session.query(Categories).order_by(Categories.name).all()
    latest_items = session.query(Items).join(
        'categories').order_by(Items.created_on.desc()).limit(10)
    return render_template("home_page.html",
                           categories=categories,
                           latest_items=latest_items
                           )


@app.route('/categories/new', methods=['GET', 'POST'])
def create_category():
    if not isUserLoggedIn():
        flash('Please login to continue....')
        return redirect(url_for('showLogin'))
    if request.method == 'GET':
        return render_template("new_category.html", category=None)
    else:
        category = request.form['new_category']
        if not category:
            flash('Category name can not be empty')
            return redirect(url_for('create_category'))
        isExists = session.query(Categories).filter_by(name=category).first()
        if isExists:
            flash('This category name already exists.')
            return redirect(url_for('create_category'))
        new_category = Categories(name=category,
                                  created_by=APPUSER_ID)
        session.add(new_category)
        session.commit()
        flash('Category created successfully!!')
        return redirect(url_for('home'))


@app.route('/categories/<string:category_name>/edit', methods=['GET', 'POST'])
def edit_category(category_name):
    if not isUserLoggedIn():
        flash('Please login to continue....')
        return redirect(url_for('showLogin'))
    category = session.query(Categories).filter_by(name=category_name).one()
    if request.method == 'GET':
        return render_template('new_category.html', category=category)
    else:
        new_name = request.form['new_category']
        if not new_name:
            flash('Category name can not be empty.')
            return redirect(url_for('edit_category',
                                    category_name=category_name))
        if category.name == new_name:
            flash('No changes made to the category name.')
            return redirect(url_for('edit_category',
                                    category_name=category_name))
        isExists = session.query(Categories).filter_by(name=category_name)
        if isExists:
            flash('This category name already exists.')
            return redirect(url_for('edit_category',
                                    category_name=category_name))
        category.name = new_name
        session.add(category)
        session.commit()
        flash('Category name updated.')
        return redirect(url_for('home'))


# To delete the category
@app.route('/categories/<string:category_name>/delete')
def category_delete(category_name):
    category_id = session.query(Categories).filter_by(
        name=category_name).first().id
    category = session.query(Categories).filter_by(name=category_name)
    if not category:
        flash('Category not found.')
        return redirect(url_for('home'))
    items = session.query(Items).filter_by(category_id=category_id)
    items.delete()
    category.delete()
    session.commit()
    flash('Category deleted successfully.')
    return redirect(url_for('home'))


@app.route('/categories/<string:category_name>/items')
def category_items(category_name):
    print 'APPUSER_ID'
    print APPUSER_ID
    if not isUserLoggedIn():
        flash('Please login to continue....')
        return redirect(url_for('showLogin'))
    category = session.query(Categories).filter_by(name=category_name).one()
    items = session.query(Items).filter_by(category_id=category.id).all()
    user = session.query(Users).filter_by(id=APPUSER_ID).one()
    edit_allowed = (user == category.created_by)
    return render_template('category_items.html',
                           category=category,
                           items=items,
                           edit_allowed=edit_allowed
                           )


@app.route('/categories/items/new', methods=['GET', 'POST'])
@app.route('/categories/<string:category_name>/items/new',
           methods=['GET', 'POST'])
def create_item(category_name=None):
    if not isUserLoggedIn():
        flash('Please login to continue....')
        return redirect(url_for('showLogin'))
    # print category_name
    if category_name:
        category = session.query(Categories).filter_by(
            name=category_name).one()
        all_categories = None
    else:
        category = None
        all_categories = session.query(Categories).filter_by(
            created_by=APPUSER_ID).all()
    if request.method == 'GET':
        return render_template('new_item.html',
                               category=category,
                               item=None,
                               all_categories=all_categories,
                               )
    else:
        # created by is not required for items
        new_item_name = request.form['new_item_name']
        item_desc = request.form['new_item_desc']
        # print category.name
        selected_id = int(request.form['selected_category'])
        if not (new_item_name and item_desc):
            flash('Item name and Description should not be empty.')
            return redirect(url_for('create_item',
                                    category_name=category_name))
        if not selected_id:
            flash('Category has to be selected')
            return redirect(url_for('create_item',
                                    category_name=category_name))
        print new_item_name
        isExists = session.query(Items).filter_by(name=new_item_name,
                                                  category_id=category.id).first()  # NOQA
        print isExists
        if isExists:
            flash('This item already exists in this category.')
            return redirect(url_for('create_item',
                                    category_name=category_name))
        # print selected_id
        if not category:
            category = session.query(
                Categories).filter_by(id=selected_id).one()
        elif category.id != selected_id:
            category = session.query(
                Categories).filter_by(id=selected_id).one()
        new_item = Items(name=new_item_name,
                         description=item_desc,
                         category_id=category.id)
        session.add(new_item)
        session.commit()
        flash('Item added!!')
        return redirect(url_for('home'))


@app.route('/categories/<string:category_name>/items/<string:item_name>/edit',
           methods=['GET', 'POST'])
def edit_item(category_name, item_name):
    if not isUserLoggedIn():
        flash('Please login to continue....')
        return redirect(url_for('showLogin'))
    category = session.query(Categories).filter_by(name=category_name).one()
    item = session.query(Items).filter_by(name=item_name,
                                          category_id=category.id).one()
    if request.method == 'GET':
        return render_template('new_item.html',
                               category=category,
                               item=item
                               )
    else:
        new_item_name = request.form['new_item_name']
        item_desc = request.form['new_item_desc']
        print 'item name'
        print new_item_name
        if not (new_item_name and item_desc):
            flash('Item name and Description should not be empty.')
            return redirect(url_for('edit_item',
                                    category_name=category_name,
                                    item_name=item_name))
        if item.name == new_item_name and item.description == item_desc:
            flash('No changes made to the Item')
            return redirect(url_for('category_items',
                                    category_name=category_name))

        if item.name == new_item_name and item.description != item_desc:
            item.description = item_desc
            session.add(item)
            session.commit()
            return redirect(
                url_for('category_items', category_name=category_name))

        isExists = session.query(Items).filter_by(name=new_item_name,
                                                  category_id=category.id).first()  # NOQA
        if isExists:
            flash('This item is already present in this category.')
            return redirect(url_for('edit_item',
                                    category_name=category_name,
                                    item_name=item_name))
        item.name = new_item_name
        item.description = item_desc
        session.add(item)
        session.commit()
        flash('Item updated.')
        return redirect(url_for('category_items', category_name=category_name))


# delete an item
@app.route('/categories/<string:category_name>/items/<string:item_name>/delete', methods=['GET', 'POST'])  # NOQA
def item_delete(category_name, item_name):
    category = session.query(Categories).filter_by(name=category_name).first()
    item = session.query(Items).filter_by(name=item_name,
                                          category_id=category.id)
    if not (category and item):
        flash('Category or Item not found')
        return redirect(url_for('category_items',
                                category_name=category_name))
    item.delete()
    session.commit()
    flash('Item was deleted.')
    return redirect(url_for('category_items',
                            category_name=category_name))


# to return the json oject of all the categories
@app.route('/categories/all_categories/JSON')
def all_categories_json():
    categories = session.query(Categories).all()
    return jsonify(Categories=[i.serialize for i in categories])


# to return all the items of a category
@app.route('/categories/<string:category_name>/items/JSON')
def all_items_json(category_name):
    category = session.query(Categories).filter_by(name=category_name).one()
    items = session.query(Items).filter_by(category_id=category.id).all()
    return jsonify(Items=[i.serialize for i in items])


@app.route('/categories/<string:category_name>/items/<string:item_name>/JSON')
def item_json(category_name, item_name):
    category = session.query(Categories).filter_by(name=category_name).one()
    item = session.query(Items).filter_by(
        name=item_name, category_id=category.id).one()
    return jsonify(item.serialize)


if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=8080)
