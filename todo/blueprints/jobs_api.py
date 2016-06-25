from flask import abort, Blueprint, make_response, request
from google.appengine.api import taskqueue
from todo.models.user import User
from todo.pipelines import SyncPipeline

BP = Blueprint('jobs_api', __name__)

@BP.before_request
def check_admin():
    if not 'X-AppEngine-Cron' in request.headers:
        abort(403)

@BP.route('/api/v1/jobs/sync')
def sync_job():
    pipeline = SyncPipeline()
    pipeline.start()
    return make_response()

@BP.route('/api/v1/jobs/rollup')
def users_job():
    task_url = '/api/v1/queues/stats/rollup'
    taskqueue.add(url=task_url)
    return make_response()
