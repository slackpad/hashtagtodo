from datetime import datetime
from collections import defaultdict
from todo.models.calendar import Calendar
from todo.models.event import Event
from todo.models.stat import Stat
from todo.models.user import User


def rollup_users():
    rollup = defaultdict(lambda: defaultdict(int))
    for user in User.get_all():
        (year, week, day) = user.created.isocalendar()
        rollup[year][week] += 1

    def gen():
        for year in sorted(rollup):
            for week in sorted(rollup[year]):
                yield (year, week)

    cum = 0
    for year, week in gen():
        cum += rollup[year][week]
        Stat.create_or_update('user-count', year, week, cum)

def rollup_todos():
    created = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    engaged = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    for event in Event.query():
        user = event.key.parent().parent().id()
        (year, week, day) = event.created.isocalendar()
        created[year][week][user] += 1
        (year, week, day) = event.updated.isocalendar()
        engaged[year][week][user] += 1

    for year, weekly in created.iteritems():
        for week, users in weekly.iteritems():
            Stat.create_or_update('user-created-event', year, week, len(users.keys()))

    for year, weekly in engaged.iteritems():
        for week, users in weekly.iteritems():
            Stat.create_or_update('user-engaged-event', year, week, len(users.keys()))

def do_rollup():
    rollup_users()
#    rollup_todos()
