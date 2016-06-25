from authomatic import Authomatic
from authomatic.adapters import WerkzeugAdapter
from flask import Blueprint, flash, jsonify, make_response, redirect, render_template, request, session
from google.appengine.api import users
from todo.client import make_client
from todo.config import AUTH_SECRET, AUTH_SERVICES
from todo.models.freemium import Freemium
from todo.models.user import User


AUTHOMATIC = Authomatic(AUTH_SERVICES, AUTH_SECRET)
BP = Blueprint('new_user', __name__)

@BP.route('/login/<provider>', methods=('GET', 'POST'))
def login(provider):
    if request.method == 'POST':
        session.permanent = 'remember' in request.form
        session.modified = True

    response = make_response()
    result = AUTHOMATIC.login(WerkzeugAdapter(request, response), provider)
    if result:
        if result.user:
            result.user.update()
            credentials = result.user.credentials.serialize()
            user = User.create_or_update(provider,
                                         result.user.id,
                                         result.user.email,
                                         result.user.first_name,
                                         result.user.last_name,
                                         credentials)
            session['user'] = user.key.urlsafe()

            # If they are on the freemium list hook them up.
            if (not user.is_premium) and (Freemium.get_by_email(result.user.email) is not None):
                user.is_premium = True
                user.put()
                flash('You\'ve been upgraded to a free premium account for one year!')

            return redirect('/todos')

        return render_template('login.html', result=result)

    return response

@BP.route('/')
def index():
    if 'user' in session:
        return redirect('/todos')

    return redirect('/index.html')
