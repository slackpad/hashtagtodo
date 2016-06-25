from google.appengine.ext import ndb

class Freemium(ndb.Model):
    created = ndb.DateTimeProperty(auto_now_add=True)
    updated = ndb.DateTimeProperty(auto_now=True)

    @classmethod
    def create_or_update(cls, email):
        entry = cls.get_or_insert(email)
        entry.put()
        return entry

    @classmethod
    def get_by_email(cls, email):
        return ndb.Key('Freemium', email).get()

    @classmethod
    def get_all(cls):
        return cls.query()
