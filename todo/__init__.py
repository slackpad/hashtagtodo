import todo.blueprints.admin_user as admin_user
import todo.blueprints.app_user as app_user
import todo.blueprints.jobs_api as jobs_api
import todo.blueprints.new_user as new_user
import todo.blueprints.pushes_api as pushes_api
import todo.blueprints.queues_api as queues_api

from datetime import timedelta
from flask import Flask
from todo.config import COOKIE_SECRET

app = Flask(__name__)
app.secret_key = COOKIE_SECRET
app.permanent_session_lifetime = timedelta(days=180)
app.register_blueprint(admin_user.BP)
app.register_blueprint(app_user.BP)
app.register_blueprint(jobs_api.BP)
app.register_blueprint(new_user.BP)
app.register_blueprint(pushes_api.BP)
app.register_blueprint(queues_api.BP)

from google.appengine.api import urlfetch
urlfetch.set_default_fetch_deadline(60)
