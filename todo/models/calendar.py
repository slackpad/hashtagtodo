from google.appengine.ext import ndb


class Calendar(ndb.Model):
    summary = ndb.StringProperty()
    time_zone = ndb.StringProperty()
    show_in_todolist = ndb.BooleanProperty(default=True)
    active = ndb.BooleanProperty(default=True)
    watch_id = ndb.StringProperty()
    watch_expires = ndb.DateTimeProperty()
    resource_id = ndb.StringProperty()
    created = ndb.DateTimeProperty(auto_now_add=True)
    updated = ndb.DateTimeProperty(auto_now=True)

    @classmethod
    def create_or_update(cls, user_key, _id, summary, time_zone):
        if not _id:
            raise ValueError('Invalid id for Calendar object.')

        calendar = cls.get_or_insert(_id, parent=user_key,
                                     summary=summary,
                                     time_zone=time_zone)
        if calendar.summary != summary or \
           calendar.time_zone != time_zone:
            calendar.summary = summary
            calendar.time_zone = time_zone
            calendar.put()

        return calendar

    @classmethod
    def get_by_id(cls, _id):
        return ndb.Key(urlsafe=_id).get()

    @classmethod
    def get_by_watch_id(cls, watch_id):
        return cls.query(cls.watch_id==watch_id).get()

    @classmethod
    def get_all(cls, user_key):
        return cls.query(ancestor=user_key)
