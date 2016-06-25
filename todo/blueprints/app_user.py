import arrow
import json
import pytz
import uuid

from datetime import datetime
from flask import abort, Blueprint, flash, g, redirect, render_template, request, session
from google.appengine.api import mail, taskqueue
from todo.client import make_client
from todo.config import AUTH_SECRET, AUTH_SERVICES, EMAILS
from todo.contrib.rfc3339 import parse_datetime
from todo.gcal_sync import delete_todolist
from todo.models.calendar import Calendar
from todo.models.event import Event
from todo.models.user import User


BP = Blueprint('app_user', __name__)

@BP.before_request
def csrf_protect():
    if request.method == 'POST':
        token = session.pop('_csrf_token', None)
        if not token or token != request.form.get('_csrf_token'):
            abort(403)

    if '_csrf_token' not in session:
        session['_csrf_token'] = str(uuid.uuid4())

@BP.before_request
def restrict_to_signed_in_users():
    g.user = None
    if 'user' in session:
        g.user = User.get_by_id(session['user'])

    if not g.user:
        session.pop('user', None)
        return redirect('/')

    g.client = make_client(g.user)

@BP.route('/logout', methods=('POST',))
def logout():
    session.pop('user', None)
    return redirect('/')

@BP.route('/help')
def help():
    return render_template('help.html')

@BP.route('/todos')
def todos():
    task_url = '/api/v1/queues/sync/user'
    params = {
        'user_id': g.user.key.urlsafe(),
        'force': 1,
    }
    taskqueue.add(url=task_url, params=params)
    return render_template('todos.html')

@BP.route('/calendars', methods=('GET', 'POST'))
def calendars():
    calendars = Calendar.get_all(g.user.key)
    if request.method == 'POST':
        if g.user.is_premium:
            enable_todolist = 'enable-todolist' in request.form
            if g.user.enable_todolist != enable_todolist:
                g.user.enable_todolist = enable_todolist
                g.user.put()
                if enable_todolist:
                    task_url = '/api/v1/queues/sync/user'
                    params = {
                        'user_id': g.user.key.urlsafe(),
                        'force': 1,
                    }
                    taskqueue.add(url=task_url, params=params)
                else:
                    try:
                        delete_todolist(g.user, g.client)
                    except:
                        pass

        for calendar in calendars:
            active_key = 'active-' + calendar.key.urlsafe()
            calendar.active = active_key in request.form

            todolist_key = 'todolist-' + calendar.key.urlsafe()
            calendar.show_in_todolist = todolist_key in request.form

            calendar.put()

        flash('Calendar settings saved.')

    return render_template('calendars.html', calendars=calendars)

@BP.route('/account')
def account():
    return render_template('account.html')

@BP.route('/account/delete', methods=('GET', 'POST'))
def delete():
    if request.method == 'POST':
        dos = arrow.get(g.user.created).humanize()
        calendars = len([c for c in Calendar.query(ancestor=g.user.key)])
        todos = len([e for e in Event.query(ancestor=g.user.key)])
        subject = '%s %s closed their account' % (g.user.first_name, g.user.last_name)
        body = '''
%s (joined %s, made %d todos and had %d calendars)

%s
''' % (g.user.email, dos, todos, calendars, request.form.get('feedback'))
        mail.send_mail(sender=EMAILS['alerts'], to=EMAILS['support'], subject=subject, body=body)

        calendars = Calendar.get_all(g.user.key)
        for calendar in calendars:
            for event in Event.get_all(calendar.key):
                event.key.delete()
            calendar.key.delete()

        User.unindex(g.user.key.urlsafe())
        g.user.key.delete()
        session.pop('user', None)
        return redirect('/index.html')

    return render_template('delete.html')
