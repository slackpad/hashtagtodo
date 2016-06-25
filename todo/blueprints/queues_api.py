import pytz

from datetime import datetime
from flask import abort, Blueprint, make_response, request
from google.appengine.api import taskqueue
from todo.client import make_client
from todo.gcal_sync import safe_timezone, sync_user
from todo.models.calendar import Calendar
from todo.models.user import User
from todo.stat_rollup import do_rollup


BP = Blueprint('queues_api', __name__)

@BP.before_request
def check_admin():
    if not 'X-AppEngine-QueueName' in request.headers:
        abort(403)

@BP.route('/api/v1/queues/sync/user', methods=('POST',))
def sync_job():
    sync_time = datetime.utcnow()
    sync_utc = pytz.utc.localize(sync_time)
    user = User.get_by_id(request.form['user_id'])

    if 'force' in request.form:
        client = make_client(user)
        sync_user(sync_time, user, client)
    else:
        for db_calendar in Calendar.get_all(user.key):
            local_tz = safe_timezone(db_calendar.time_zone)
            sync_local = local_tz.normalize(sync_utc)
            if sync_local.hour == 0:
                client = make_client(user)
                sync_user(sync_time, user, client)
                break

    return make_response()

@BP.route('/api/v1/queues/sync/force', methods=('POST',))
def force_job():
    task_url = '/api/v1/queues/sync/user'
    for key in User.get_all_keys():
        params = {
            'user_id': key.urlsafe(),
            'force': 1,
        }
        taskqueue.add(url=task_url, params=params)

    return make_response()

@BP.route('/api/v1/queues/stats/rollup', methods=('POST',))
def rollup_job():
    do_rollup()
    return make_response()

