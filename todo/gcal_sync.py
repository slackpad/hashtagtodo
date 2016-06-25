import arrow
import copy
import pytz
import re
import uuid

from apiclient.http import BatchHttpRequest
from datetime import datetime
from datetime import timedelta
from todo.config import is_prod, ROOT_URL
from todo.contrib.rfc3339 import datetimetostr, parse_datetime
from todo.models.calendar import Calendar
from todo.models.event import Event


CHECKBOX_SUMMARY_RE = re.compile(r'\[([^\]]*)\]')
MOSTLY_RFC_FORMAT = '%Y-%m-%dT%H:%M:%S'
TIME_FORMAT = '%Y-%m-%d'
TODO_RE = re.compile(r'\#todo\b', re.I)

def safe_timezone(time_zone):
    try:
        return pytz.timezone(time_zone)
    except pytz.UnknownTimeZoneError:
        # This is a hack! We need to audit for these and clean them up.
        print 'BAD_TZ: %s' % time_zone
        return pytz.timezone('America/Los_Angeles')

def parse_time(db_calendar, stamp):
    local_tz = safe_timezone(stamp.get('timeZone', db_calendar.time_zone))
    if 'date' in stamp:
        all_day = True
        local_time = datetime.strptime(stamp['date'], TIME_FORMAT)
        local_time = local_tz.normalize(local_tz.localize(local_time))
    else:
        all_day = False
        try:
            local_time = parse_datetime(stamp['dateTime'])
        except ValueError:
            local_time = datetime.strptime(stamp['dateTime'], MOSTLY_RFC_FORMAT)
            local_time = local_tz.normalize(local_tz.localize(local_time))

    return (all_day, local_time)

def _process_batch(updates):
    if not updates:
        return

    def callback(request_id, response, exception):
        if exception is not None:
            raise exception

    batch = BatchHttpRequest(callback=callback)
    [batch.add(update) for update in updates]
    batch.execute()

def _get_todolist(user, client, calendar):
    events = client.events().list(
        calendarId=calendar['id'],
        q='HashtagTodo').execute()
    for event in events.get('items', ()):
        summary = event.get('summary', '')
        description = event.get('description', '')
        if user.get_hash() in description:
            return event

    return None

def get_todolist(user, client):
    # Try the primary calendar first, as this is the default for the
    # vast majority of users.
    default = client.calendars().get(calendarId='primary').execute()
    event = _get_todolist(user, client, default)
    if event is not None:
        return event, default

    # Now look at the user's other calendars to see if it's on there.
    calendars = client.calendarList().list().execute()
    for calendar in calendars.get('items', ()):
        if calendar['id'] == default['id']:
            continue

        if not calendar['accessRole'] in ('owner', 'writer'):
            continue

        event = _get_todolist(user, client, calendar)
        if event is not None:
            return event, calendar

    # They don't have one, so add it to their default calendar.
    return None, default

def delete_todolist(user, client):
    event, calendar = get_todolist(user, client)
    if event is not None and user.get_hash() in event['description']:
        client.events().delete(calendarId=calendar['id'], eventId=event['id']).execute()

def _sync_todolist(sync_time, user, client, todolists):
    title = '%s Todo List' % user.first_name
    description = ''
    total_items = 0

    full_list = list()
    for (db_calendar, todolist) in todolists:
        if not db_calendar.show_in_todolist:
            continue

        for event in todolist:
            (_, due) = parse_time(db_calendar, event['start'])
            if due < sync_time:
                try:
                    due = parse_datetime(event['created'])
                except ValueError:
                    pass

            summary = event['summary'].replace('[  ]', '*').strip()
            summary = summary.replace('#todo', '').strip()

            human_due_date = arrow.get(due).humanize()
            full_list.append((due, '%s (%s)' % (summary, human_due_date)))
            total_items += 1

    full_list = sorted(full_list, key=lambda x: x[0])
    todo_list = [summary for (_, summary) in full_list]
    if todo_list:
        description += '\n'.join(todo_list)
    else:
        description += 'You have no todos! Start making events with #todo ' \
                       'in the title and HashtagTodo will keep track of them for you.'

    description += '\n\nREAD ONLY. Please edit the actual #todo calendar events to make changes.'
    description += '\n\nHashtagTodo'
    description += '\n\nUpdated at %s.' % sync_time.strftime(MOSTLY_RFC_FORMAT)
    description += '\n%s' % user.get_hash()

    # Make this an all-day event on the current day, making sure to respect the
    # time zone for the calendar we are putting this on.
    event, calendar = get_todolist(user, client)
    local_tz = safe_timezone(calendar['timeZone'])
    sync_local = local_tz.normalize(sync_time)
    start = sync_local.strftime(TIME_FORMAT)
    end = (sync_local + timedelta(1)).strftime(TIME_FORMAT)

    if total_items > 0:
        title = '%s (%d)' % (title, total_items)

    # This is all the new information for the todolist.
    patch = {
        'summary': title,
        'description': description,
        'start': {'date': start, 'dateTime': None, 'timeZone': None},
        'end': {'date': end, 'dateTime': None, 'timeZone': None},
        'gadget': {
            'iconLink': ROOT_URL + '/assets/images/hashtag-large.ico',
            'display': 'chip',
            'type': None,
            'link': None,
        },
    }

    # If we found an existing event, just patch that so we don't mess
    # with any settings the user might have changed.
    if event:
        return client.events().patch(calendarId=calendar['id'],
                                     eventId=event['id'],
                                     body=patch)

    # Update the patch with some more default options since we are creating
    # the event from scratch. We make these items private by default since
    # they cross multiple calendars and might leak information if they were
    # visible on a shared calendar.
    patch['transparency'] = 'transparent'
    patch['visibility'] = 'private'
    patch['reminders'] = {'useDefault': False}
    return client.events().insert(calendarId=calendar['id'],
                                  body=patch)

def _sync_event(sync_time, user, client, db_calendar, event):
    batch_updates = list()
    patch = dict()

    # Ensure all #todo items have the done-ness checkbox at the front.
    done_match = CHECKBOX_SUMMARY_RE.search(event['summary'])
    if done_match:
        if done_match.group(1).strip():
            done = True
        else:
            done = False
    else:
        patch['summary'] = '[  ] ' + event['summary']
        done = False

    # Record info about this event.
    Event.create_or_update(db_calendar.key, event['id'], '#todo', done)

    # Canonicalize the done checkbox. We add the check here to prevent loops in case
    # we end up matching multiple sets of brackets.
    if done and not '[x]' in event['summary']:
        clean_summary = CHECKBOX_SUMMARY_RE.sub('[x]', event['summary'], 1)
        if clean_summary != event['summary']:
            patch['summary'] = clean_summary

    # Roll forward any past-due open items.
    if not done and TODO_RE.search(event['summary']):
        (all_day, start) = parse_time(db_calendar, event['start'])
        start_day = datetime(start.year, start.month, start.day, tzinfo=start.tzinfo)
        if (start_day - sync_time).days < -1:
            local_tz = safe_timezone(db_calendar.time_zone)
            sync_local = local_tz.normalize(sync_time)
            patch['start'] = {'date': sync_local.strftime(TIME_FORMAT),
                              'dateTime': None,
                              'timeZone': None}
            (_, end) = parse_time(db_calendar, event['end'])
            if all_day:
                days = (end - start).days
            else:
                days = 1
            patch['end'] = {'date': (sync_local + timedelta(days)).strftime(TIME_FORMAT),
                            'dateTime': None,
                            'timeZone': None}

    if patch:
        batch_updates.append(client.events().patch(calendarId=db_calendar.key.id(),
                                                   eventId=event['id'],
                                                   body=patch))

    return (event, done, batch_updates)

def _sync_calendar(sync_time, user, client, db_calendar, debug=False):
    event_list = list()

    # Look for #todo items with a lookback, since they should all be pulled
    # forward.
    lookback = timedelta(days=30)
    events = client.events().list(
        calendarId=db_calendar.key.id(),
        q='#todo',
        timeMin=datetimetostr(sync_time - lookback),
        orderBy='startTime',
        singleEvents=True).execute()
    event_list.extend(events.get('items', ()))

    todolist = list()
    batch_updates = list()
    for event in event_list:
        if debug:
            print event

        if 'recurringEventId' in event:
            (_, start) = parse_time(db_calendar, event['start'])
            start_day = datetime(start.year, start.month, start.day, tzinfo=start.tzinfo)
            if (start_day - sync_time).days > 3:
                continue

        summary = event.get('summary', '')
        if TODO_RE.search(summary):
            (event, done, updates) = _sync_event(sync_time, user, client, db_calendar, event)
            batch_updates.extend(updates)

            if not done:
                todolist.append(event)

    return (todolist, batch_updates)

def sync_calendar(sync_time, user, client, db_calendar):
    sync_time = pytz.utc.localize(sync_time)
    (_, batch_updates) = _sync_calendar(sync_time, user, client, db_calendar)
    _process_batch(batch_updates)

    return len(batch_updates) > 0

def sync_user(sync_time, user, client, debug=False):
    todolists = list()
    sync_time = pytz.utc.localize(sync_time)
    calendars = client.calendarList().list().execute()
    for calendar in calendars.get('items', ()):
        if not calendar['accessRole'] in ('owner', 'writer'):
            continue

        db_calendar = Calendar.create_or_update(user.key,
                                                calendar['id'],
                                                calendar['summary'],
                                                calendar['timeZone'])

        # We have a nasty is_prod() check here because we don't want to register
        # push notifications for dev environments.
        if is_prod():
            # Update a little early so we always get some overlap with the push
            # notifications and the user doesn't experience any interruption in
            # service.
            UPDATE_WINDOW = 2 * 60 * 60
            if not db_calendar.watch_id or \
               (pytz.utc.localize(db_calendar.watch_expires) - sync_time).total_seconds() < UPDATE_WINDOW:
                watch_id = str(uuid.uuid4())
                body = {
                    'id': watch_id,
                    'type': 'web_hook',
                    'address': ROOT_URL + '/api/v1/pushes/calendars',
                }
                watch = client.events().watch(
                    calendarId=db_calendar.key.id(), body=body).execute()
                if watch:
                    db_calendar.watch_id = watch_id
                    db_calendar.resource_id = watch['resourceId']
                    expires = int(watch['expiration']) / 1000
                    db_calendar.watch_expires = datetime.fromtimestamp(expires)
                    db_calendar.put()

        if db_calendar.active:
            (todolist, batch_updates) = _sync_calendar(sync_time, user, client, db_calendar, debug=debug)
            _process_batch(batch_updates)
            todolists.append((db_calendar, todolist))

    if (not user.is_premium) or user.enable_todolist:
        todolist_request = _sync_todolist(sync_time, user, client, todolists)
        todolist_request.execute()

    user.synced = datetime.utcnow()
    user.put()
    return todolists
