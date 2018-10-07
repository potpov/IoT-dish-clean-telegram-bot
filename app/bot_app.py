# -*- encoding: utf8 -*-
import telegram
from flask import Flask, request
from flask_restful import Api, Resource, reqparse
import config
import appengine_config
from google.appengine.ext import ndb
import requests_toolbelt.adapters.appengine
from models import model
from datetime import datetime
import os
import json
from flask import jsonify

app = Flask(__name__)
app.config.from_object(__name__)
app.debug = True
DEBUG = True
api = Api(app)

bot = telegram.Bot(token=config.token)

users = config.user_list

# Use the App Engine Requests adapter. This makes sure that Requests uses URLFetch.
requests_toolbelt.adapters.appengine.monkeypatch()


# webhook functions for bot debug
@app.route('/set_webhook', methods=['GET', 'POST'])
def set_webhook():
    s = bot.setWebhook(config.url)
    if s:
        return "webhook setup ok"
    else:
        return "webhook setup failed"


@app.route('/HOOK', methods=['POST'])
def webhook_handler():
    return 'disabled'


@app.route('/init/<secret>', methods=['GET', 'POST'])
def create(secret):
    if secret != config.init_key:
        return 'not allowed. bye!', 401
    for user in users:
        key = ndb.Key(model.Users, user)
        q = model.Users(key=key, name=user, last=datetime.now(), total=0)
        q.put()
    return 'completed', 200


@app.route('/doc', methods=['GET'])
def apidoc():
    SITE_ROOT = os.path.realpath(os.path.dirname(__file__))
    json_url = os.path.join(SITE_ROOT, 'json', 'swagger.json')
    data = json.load(open(json_url))
    return jsonify(data)

    
# set up parsers for APIs
newJobParser = reqparse.RequestParser()
newJobParser.add_argument('secret', type=str, required=True)

jobCompleteParser = reqparse.RequestParser()
jobCompleteParser.add_argument('secret', type=str, required=True)
jobCompleteParser.add_argument('user', type=str, required=True)

alertParser = reqparse.RequestParser()
alertParser.add_argument('secret', type=str, required=True)
alertParser.add_argument('time', type=int, required=True)


# APIs handlers
class NewJob(Resource):
    def post(self):
        args = newJobParser.parse_args()
        if args.secret != config.api_key:
            return 'API KEY missing', 401
        # finding the last one who clean dishes
        query = model.Users.query().order(model.Users.last)
        user = query.get()
        bot.sendMessage(chat_id=config.chat_id,
                        text="dishes have to be washed. next to wash dishes is {}".format(user.name))
        return {}


class JobComplete(Resource):
    def post(self):
        args = jobCompleteParser.parse_args()
        if args.secret != config.api_key:
            return 'API KEY missing', 401
        bot.sendMessage(chat_id=config.chat_id,
                        text="dish clean. job completed by {}".format(args.user))
        k = ndb.Key(model.Users, args.user)
        # update of the stats
        result = k.get()
        if result is None:
            bot.sendMessage(chat_id=config.chat_id,
                            text="can't find {} in the datastore. maybe we gotta reset the DB?".format(args.user))
        result.total = result.total + 1
        result.put()
        # dump of the stats
        q = model.Users.query()
        dump = "here is some stats for you:\n"
        for user in q.fetch():
            dump += "user: {}, last job {}, total jobs: {}\n".format(user.name, user.last, user.total)
        bot.sendMessage(chat_id=config.chat_id, text=dump)
        return {}


class Alert(Resource):
    def post(self):
        args = alertParser.parse_args()
        if args.secret != config.api_key:
            return 'API KEY missing', 401
        # time arrives in millis, conversion needed
        time = args.time / 100000
        bot.sendMessage(chat_id=config.chat_id,
                        text="ALERT. dish not washed for {} minutes!".format(time))
        return {}


api.add_resource(NewJob, '/api/newjob')
api.add_resource(JobComplete, '/api/jobcomplete')
api.add_resource(Alert, '/api/alert')

