# Synopsis
This Project is about coding a simple multi user blog.
Requirement document can be viewed [here](https://docs.google.com/document/d/1jFjlq_f-hJoAZP8dYuo5H3xY62kGyziQmiv9EPIA7tM/pub?embedded=true)
*This link might need login credentials to udacity.*

# Motivation
I completed this project as part of Full Stack Nano Degree from Udacity.
This is the fifth project in the curriculam.

# Installation
* Download all the files or clone the repository to your local machine.
* Make sure to have browser installed. Any web browser will do.
* Install python from [here](https://www.python.org/downloads/)
* Install flask using pip.[Guide](http://flask.pocoo.org/docs/0.12/installation/#system-wide-installation)
* Download and install sqlalchemy from [here](http://www.sqlalchemy.org/download.html)
* Download and install postgres database from [here](https://www.postgresql.org/docs/9.2/static/tutorial-install.html)
* Create database and users in postgresql, Follow the steps.
***Create a database.
    *	```psql```
    *   ```CREATE DATABASE CATALOG ;```
    *	```postgres=# create user appsys with password 'appsys';```
    *	```CREATE ROLE```
    *	```postgres=# grant all privileges on database catalog to appsys;```
    *	```GRANT```
    * ```create the same user in os level(add user appsys)```.

* Create credentials to use oauth for [Google](https://developers.google.com/identity/sign-in/web/sign-in) and [Facebook](https://developers.facebook.com/docs/facebook-login/web/accesstokens)
* Update the ```client_secrets.json``` with google credentials or download it directly.
* Update the ```fb_client_secrets.json``` with facebook credentials created.

# How to run the project?
* Navigate to the ```P5_catalog``` directory.(Downloaded)
* run the ```application.py``` file passing it as an argument to ```python```.
* Open http://localhost:8080/




#Credits.
* Back ground pattern for body was taken from [here](http://lea.verou.me/css3patterns/#carbon-fibre)
* Google and Facebook signin javascript code was taken from their respective websites and modified.
* I would like to thank Udacity Discussion forum and [stack overflow](http://www.stackoverflow.com) for helping me advance when stuck with few problems.
