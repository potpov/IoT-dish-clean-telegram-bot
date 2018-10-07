from google.appengine.ext import ndb


class Users(ndb.Model):
    name = ndb.StringProperty(required=True)
    last = ndb.DateTimeProperty(required=True)
    total = ndb.IntegerProperty(required=True)
