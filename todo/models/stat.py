from datetime import datetime
from google.appengine.ext import ndb
from isoweek import Week


class Stat(ndb.Model):
    tag = ndb.StringProperty()
    week = ndb.IntegerProperty()
    year = ndb.IntegerProperty()
    stat = ndb.FloatProperty()
    updated = ndb.DateTimeProperty(auto_now=True)

    def date(self):
        return Week(self.year, self.week).monday()

    @classmethod
    def create_or_update(cls, tag, year, week, stat):
        _id = "%s.%d.%d" % (tag, year, week)

        entry = cls.get_or_insert(_id)
        entry.tag = tag
        entry.week = week
        entry.year = year
        entry.stat = stat
        entry.put()

        return entry

    @classmethod
    def get_all(cls, tag):
        return cls.query(cls.tag==tag).order(cls.year).order(cls.week)
