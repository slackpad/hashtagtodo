import arrow
import pytz
import uuid

from datetime import datetime
from flask import abort, Blueprint, flash, g, make_response, redirect, render_template, request, session
from flask.ext.jsonpify import jsonify
from google.appengine.api import taskqueue
from todo.blueprints import app_user
from todo.client import make_client
from todo.gcal_sync import sync_user
from todo.models.calendar import Calendar
from todo.models.event import Event
from todo.models.freemium import Freemium
from todo.models.stat import Stat
from todo.models.user import User
from todo.pipelines import ExportPipeline

BP = Blueprint('admin_user', __name__)

@BP.before_request
def csrf_protect():
    if request.method == 'POST':
        token = session.pop('_csrf_token', None)
        if not token or token != request.form.get('_csrf_token'):
            abort(403)

    if '_csrf_token' not in session:
        session['_csrf_token'] = str(uuid.uuid4())

@BP.before_request
def restrict_to_admin_users():
    g.user = None
    if 'user' in session:
        g.user = User.get_by_id(session['user'])

    if not g.user or not g.user.is_admin:
        session.pop('user', None)
        abort(403)

@BP.route('/admin/dashboard')
def dashboard():
    return render_template('admin-dashboard.html')

@BP.route('/admin/user/search')
def search_user():
    query = request.args.get('q', '')
    results = User.search(query)
    simplified = list()
    for result in results:
        entry = {
            'link': '/admin/user/manage/%s' % result.doc_id
        }
        for field in result.fields:
            if field.name == 'created':
                entry[field.name] = arrow.get(field.value).humanize()
            else:
                entry[field.name] = field.value
        simplified.append(entry)
    extra = {
        'total': results.number_found,
        'shown': len(results.results),
    }
    return render_template('admin-user-search.html', results=simplified, extra=extra)

@BP.route('/admin/user/manage/<user_id>', methods=('GET', 'POST'))
def manage_user(user_id):
    user = User.get_by_id(user_id)
    if user is None:
        User.unindex(user_id)
        flash('User deleted their account; cleaned up search index')
        return redirect('/admin/user/search')

    if request.method == 'POST':
        operation = request.form.get('operation')
        if operation == 'goodbye':
            app_user.send_goodbye(user)
        elif operation == 'sync':
            sync_time = datetime.utcnow()
            sync_utc = pytz.utc.localize(sync_time)
            client = make_client(user)
            sync_user(sync_time, user, client, debug=True)
            flash('Synced user')
        elif operation == 'upgrade':
            user.is_premium = True
            user.put()
        elif operation == 'downgrade':
            user.is_premium = False
            user.put()
        else:
            flash('Unknown operation')

    calendars = 0
    todos = 0
    completed = 0
    for calendar in Calendar.get_all(user.key):
        calendars += 1
        for event in Event.get_all(calendar.key):
            todos += 1
            if event.done:
                completed += 1

    extra = {
        'calendars': calendars,
        'todos': todos,
        'completed': completed,
        'created': arrow.get(user.created).humanize(),
        'updated': arrow.get(user.updated).humanize(),
    }
    return render_template('admin-user-manage.html', manage_user=user, extra=extra)

@BP.route('/admin/freemium', methods=('GET', 'POST'))
def freemium():
    if request.method == 'POST':
        operation = request.form.get('operation')
        if operation == "add":
            addresses = [email.strip() for email in request.form.get('addresses', '').split(',')]
            for email in addresses:
                Freemium.create_or_update(email)
        elif operation == 'remove':
            prefix = 'remove-'
            for key in request.form:
                if key.startswith(prefix):
                    email = key[len(prefix):]
                    entry = Freemium.get_by_email(email)
                    if entry is not None:
                        entry.key.delete()
        else:
            flash('Unknown operation')

    entries = Freemium.get_all()
    entries = [entry.key.id() for entry in entries]
    return render_template('admin-freemium.html', entries=entries)

@BP.route('/api/v1/admin/stats')
def stats():
    stats = list()
    for stat in Stat.get_all(request.args.get('tag')):
        stats.append((stat.date().isoformat(), stat.stat))

    return jsonify(stats)

@BP.route('/api/v1/admin/stats/export')
def export():
    pipeline = ExportPipeline()
    pipeline.start()
    redirect_url = "%s/status?root=%s" % (pipeline.base_path, pipeline.pipeline_id)
    return redirect(redirect_url)

@BP.route('/api/v1/admin/sync/force')
def force_sync():
    task_url = '/api/v1/queues/sync/force'
    taskqueue.add(url=task_url)
    return make_response()
