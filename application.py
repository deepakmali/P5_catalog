from flask import Flask, render_template, request, redirect, url_for
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Categories, Items, Users
from flask import session as login_session

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
    return render_template('login.html')

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
