import logging
import os.path
from os import environ
from collections import defaultdict
from sys import stdout
import random

try:
    import cStringIO as sio
except ImportError:
    from io import StringIO as sio

#from Tornado
import tornado.httpserver
import tornado.ioloop
import tornado.web
import tornado.gen

from pymongo import MongoClient

import json
from bson import ObjectId


# for redis
from toredis import Client
import redis

from bson import json_util
from bson.objectid import ObjectId

MONGODB_DB_URL = 'mongodb://heroku_qzkzsqmj:bejucbi1s53qb9ldqobd166od5@ds157529.mlab.com:57529/heroku_qzkzsqmj'
MONGODB_DB_NAME = 'heroku_qzkzsqmj'

environ['CONFIG'] = './page.conf'

client = MongoClient(MONGODB_DB_URL)
db = client[MONGODB_DB_NAME]


class BaseHandler(tornado.web.RequestHandler):
    def db(self):
        return self.application.db

    def get_current_user(self):
        return self.get_secure_cookie("user")

class MainHandler(BaseHandler):
    def get(self):
        self.render("index.html", title="Oxford Experiments")

class RegisterHandler(BaseHandler):
    def post(self):
        name = self.get_argument('name')
        result = db.players.insert_one({
            "name" : name
            })
        self.render("about.html", title="Oxford Experiments", oid = result.inserted_id)
        #self.render("welcome.html", title="Oxford Experiments", oid = result.inserted_id, round = 1)

class QuizHandler(BaseHandler):
    def post(self, submit):
        self.render("quiz.html", title="Oxford Experiments")

class InstructionsHandler(BaseHandler):
    def get(self, oid):
        self.render("instructions.html", title="Oxford Experiments", oid = oid)

class Instructions2Handler(BaseHandler):
    def get(self, oid):
        self.render("instructions2.html", title="Oxford Experiments", oid = oid)

class TutorialHandler(BaseHandler):
    def post(self, oid):
    	self.render("tutorial.html", title="Oxford Experiments", oid = oid)


class Tutorial2Handler(BaseHandler):
    def post(self, oid):
        self.render("tutorial2.html", title="Oxford Experiments", oid = oid)

class WelcomeHandler(BaseHandler):
    def get(self, oid):
        #if(city != "Paris"):
         #   self.render("about.html", title="Oxford Experiments", oid = oid)
        #else:
        print oid
        self.render("welcome.html", title="Oxford Experiments", oid = oid, rd=rd)
    def post(self, oid):
        #oid = self.get_argument('oid')
        self.render("welcome.html", title="Oxford Experiments", oid = oid, round = 1)

class PaymentHandler(BaseHandler):
    def get(self, oid):
        user = db.players.find_one({"_id": ObjectId(self.get_argument("oid"))})
        self.render("payment.html", title="Oxford Experiments", oid = self.get_argument("oid"), payment = 5, user = user)

class GameHandler(BaseHandler):
    def post(self, oid):
        #oid = self.get_argument('oid')
        self.render("game.html", title="Oxford Experiments", oid = oid)

class PlayerCreateHandler(BaseHandler):
    def get(self, oid):

        user = db.players.find_one({"_id": self.get_argument('oid')})
        logger.info('[PlayerCreateHandler] Subject: %s ', oid)

        self.write({"subject" : oid, "user_obj" : user })

class PlayerHandler(BaseHandler):
    def get(self):
        player_id = tornado.escape.xhtml_escape(self.current_user)
        player = db.players.find_one({"_id":ObjectId(str(player_id))})
        self.set_header("Content-Type", "application/json")
        self.write(json.dumps((player),default=json_util.default))

class SubjectHandler(tornado.web.RequestHandler):

    def prepare(self):
        #logger.info("Inside SubjectHandler")
        try:
            self.subject = self.get_cookie('dx')
            self.game = self.get_cookie('yx')
            #logger.info('[SubjectHandler] Subject : %s and Game: %s',self.subject, self.game )
            self.sub_key = ':'.join(('session', self.subject, 'path'))
            #logger.info('[SubjectHandler] Subkey : %s ',self.sub_key )
            #logger.exception('[SubjectHandler] When preparing subject: %s', self.subject)
        except TypeError as e:
            #logger.exception('[SubjectHandler] When preparing subject: %s', e.args[0])
            raise tornado.web.HTTPError(403)

    def get_current_user(self):
        return self.subject and self.game

class CredentialHandler(SubjectHandler):

    def _clear_most_cookies(self):
        for name in self.request.cookies.iterkeys():
            if name != 'ff':
                self.clear_cookie(name, path='/game', domain='127.0.0.1')

    @tornado.web.authenticated
    def get(self):
        print "inside credential"

        admitted = self.get_cookie('zx')
        conn = self.get_argument('conn', None)


        logger.info('[CredentialHandler] Game: %s | Subject: %s | Admitted: %s | Conn: %s', self.game, self.subject, admitted, conn)

        try:
            if admitted:
                session, version = self.application.redis_cmd.hmget(self.sub_key, ['sess', 'ver'])
                #session = self.application.redis_cmd.hget(sub_key, 'sess')
                #version = self.application.redis_cmd.hget(sub_key, 'ver')

                if conn == 'chat' and session:
                    chat = self.application.redis_cmd.hget(self.sub_key, 'chat')
                    #logger.info('[CredentialHandler] Chat number: %s', chat)
                    self.finish({'ps': True, 'gm': self.game, 'sb': self.subject, 'ver': version, 'ss': session, 'ch': chat})
                elif conn == 'game' and session:
                    # subject's session journey is ending so clear it up
                    pipe = self.application.redis_cmd.pipeline()
                    pipe.delete(self.sub_key).hsetnx(':'.join(('data', self.game, 'pregame', self.subject)), 'pre_end', datetime.now().strftime('%H%M%S'))
                    pipe.execute()

                    #self._clear_most_cookies()
                    self.clear_cookie('zx', path='/game', domain='127.0.0.1')
                    #logger.info('[CredentialHandler] All session accesses reset for subject: %s', self.subject)
                    self.finish({'ps': True, 'gm': self.game, 'sb': self.subject, 'ss': session, 'ver': version})
                else:
                    #logger.warning('[CredentialHandler] INVALID CREDENTIAL request: %s from admitted subject: %s', conn, self.subject)
                    self.clear_all_cookies(path='/game', domain='127.0.0.1')
                    #logger.info('[CredentialHandler] All session accesses reset for subject: %s', self.subject)
                    self.finish({'ps': False})
            else:
                if conn == 'wait':
                    self.finish({'ps': True, 'gm': self.game, 'sb': self.subject})
                else:
                    #logger.warning('[CredentialHandler] - INVALID CREDENTIAL request: %s from unadmitted subject: %s', self.subject, conn)
                    self.clear_all_cookies(path='/game', domain='127.0.0.1')
                    #logger.info('[CredentialHandler] All session accesses reset for subject: %s', self.subject)
                    self.finish({'ps': False})
        except TypeError as e:
            #logger.exception('[CredentialHandler] When credentializing %s: %s', self.subject, e.args[0])
            self.clear_all_cookies(path='/game', domain='127.0.0.1')
            #logger.info('[CredentialHandler] All session accesses reset for subject: %s', self.subject)
            self.finish({'ps': False})

class SyncExperimentLaunchHandler(tornado.web.RequestHandler):

    @tornado.gen.coroutine
    #@tornado.web.authenticated
    def get(self, game):
        # activate the game;
        print "Hello " + game
        logger.info('[SyncExperimentLaunchHandler] Inside SyncExperiement')
        try:
            WaitingRoomConnection.room_types[game] = WaitingRoomConnection.CONTINUOUS_ADMISSION

            # set up the waiting room
            WaitingRoomConnection.admission_sizes = 1
            WaitingRoomConnection.room_statuses = None
            GameConnection.ready = 0

            logger.info("[SyncExperimentLaunchHandler] game size %s", str(WaitingRoomConnection.admission_sizes))

            # set up the sync game server
            game_config_msg = json.dumps({'id': game, 'size': 2})
            #yield tornado.gen.Task(self.application.redis_pub.publish, 'config:sync', game_config_msg)

            self.finish('Game ' + game + ' successfully activated')
        except TypeError as e:
            logger.exception('[SyncExperimentLaunchHandler] When launching game %s: %s', game, e.args[0])
            self.finish('error')
        except ValueError as e:
            logger.exception('[SyncExperimentLaunchHandler] When launching game %s: %s', game, e.args[0])
            self.finish('error')

class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, ObjectId):
            return str(o)
        return json.JSONEncoder.default(self, o)

class UserHandler(tornado.web.RequestHandler):

    def get(self):
        for users in db.players.find():
           self.write(JSONEncoder().encode(users))
           self.write("<br>")