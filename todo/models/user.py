import datetime
import hashlib

from google.appengine.api import search
from google.appengine.ext import ndb

class User(ndb.Model):
    email = ndb.StringProperty()
    first_name = ndb.StringProperty()
    last_name = ndb.StringProperty()
    credentials = ndb.BlobProperty()
    is_admin = ndb.BooleanProperty(default=False)
    is_premium = ndb.BooleanProperty(default=False)
    enable_todolist = ndb.BooleanProperty(default=True)
    synced = ndb.DateTimeProperty()
    created = ndb.DateTimeProperty(auto_now_add=True)
    updated = ndb.DateTimeProperty(auto_now=True)

    def get_hash(self):
        return hashlib.sha256(self.email).hexdigest()[:8]

    def index(self):
        doc = search.Document(
            doc_id = self.key.urlsafe(),
            fields = [
                search.TextField(name='email', value=self.email),
                search.TextField(name='first_name', value=self.first_name),
                search.TextField(name='last_name', value=self.last_name),
                search.DateField(name='created', value=self.created),
                search.TextField(name='hash', value=self.get_hash()),
            ])

        try:
            index = search.Index(name="user")
            index.put(doc)
        except search.Error:
            print 'Failed to index user %s' % self.email

    @classmethod
    def unindex(cls, _id):
        index = search.Index(name="user")
        index.delete(_id)

    @classmethod
    def search(cls, query):
        sort1 = search.SortExpression(expression='created', direction=search.SortExpression.DESCENDING)
        sort_options = search.SortOptions(expressions=(sort1,))

        index = search.Index(name="user")
        results = index.search(query=search.Query(
            query,
            options = search.QueryOptions(
                number_found_accuracy=1000,
                sort_options=sort_options,
            ),
        ))
        return results

    @classmethod
    def create_or_update(cls, provider, _id, email, first_name, last_name,
                         credentials):
        if not _id:
            raise ValueError('Invalid id for User object.')

        user = cls.get_or_insert('%s.%s' % (provider, _id))
        user.email = email
        user.first_name = first_name
        user.last_name = last_name
        user.credentials = credentials
        user.put()
        user.index()

        return user

    @classmethod
    def get_by_raw_id(cls, _id):
        return ndb.Key(cls, _id).get()

    @classmethod
    def get_by_id(cls, _id):
        return ndb.Key(urlsafe=_id).get()

    @classmethod
    def get_all(cls):
        return cls.query()

    @classmethod
    def get_all_keys(cls):
        return cls.query().fetch(keys_only=True)
