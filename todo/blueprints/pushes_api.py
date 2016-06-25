from datetime import datetime
from flask import abort, Blueprint, make_response, request
from todo.client import make_client
from todo.gcal_sync import sync_calendar, sync_user
from todo.models.calendar import Calendar
from todo.models.user import User


BP = Blueprint('pushes_api', __name__)

@BP.route('/api/v1/pushes/calendars', methods=('POST',))
def calendar_push():
    watch_id = request.headers['X-Goog-Channel-ID']
    db_calendar = Calendar.get_by_watch_id(watch_id)
    if db_calendar:
        if db_calendar.active:
            user = db_calendar.key.parent().get()
            client = make_client(user)
            sync_time = datetime.utcnow()
            try:
                updates = sync_calendar(sync_time, user, client, db_calendar)
                if updates:
                    sync_user(sync_time, user, client)
            except Exception as e:
                print e
    else:
        resource_id = request.headers['X-Goog-Resource-ID']
        print 'Unknown push notification for resource id %s' % resource_id

    return make_response()
