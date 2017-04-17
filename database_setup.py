from sqlalchemy import Table, Column, Integer, String, ForeignKey, DateTime
from sqlalchemy import create_engine
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
import datetime

Base = declarative_base()

class Users(Base):
    """
    To store the details of user logged in via Google or Facebook.
    """
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    name = Column(String(80), nullable=False)
    email = Column(String(400), nullable=False)
    profile_pic = Column(String(500))
    created_on = Column(DateTime, onupdate=datetime.datetime.now)


class Categories(Base):
    """
    To store the Details of categories and by who/when it was created.
    """
    __tablename__ = 'categories'
    id = Column(Integer, primary_key=True)
    name = Column(String(80), nullable=False)
    created_by = Column(Integer, ForeignKey('users.id'))
    users = relationship(Users)
    created_on = Column(DateTime, default=datetime.datetime.now)


class Items(Base):
    """
    To store details of items. To which category the item belongs and created 
    by who and the time it was created.
    """
    __tablename__ = 'items'
    id = Column(Integer, primary_key=True)
    name = Column(String(80), nullable=False)
    description = Column(String(500))
    category_id = Column(Integer, ForeignKey('categories.id'))
    created_by = Column(Integer, ForeignKey('users.id'))
    created_on = Column(DateTime, default=datetime.datetime.now)
    item_pic = Column(String(250), default='/static/item_default.png')
    categories = relationship(Categories)
    users = relationship(Users)


engine = create_engine('postgresql://appsys:appsys@localhost:5432/catalog')
Base.metadata.create_all(engine)
