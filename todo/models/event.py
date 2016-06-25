from google.appengine.ext import ndb


class Event(ndb.Model):
    tag = ndb.StringProperty()
    done = ndb.BooleanProperty()
    created = ndb.DateTimeProperty(auto_now_add=True)
    updated = ndb.DateTimeProperty(auto_now=True)

    @classmethod
    def create_or_update(cls, calendar_key, _id, tag, done=False):
        if not _id:
            raise ValueError('Invalid id for Event object.')

        event = cls.get_or_insert(_id, parent=calendar_key,
                                  tag=tag,
                                  done=done)
        if event.tag != tag or event.done != done:
            event.tag = tag
            event.done = done
            event.put()

        return event

    @classmethod
    def get_all(cls, calendar_key):
        return cls.query(ancestor=calendar_key)
