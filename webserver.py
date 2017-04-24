#!/usr/bin/python

__author__ = "Bryant Chen, based on Chang Yang's work on UbiquityLab"
__email__ = "bachen@stanford.edu"

#from Python
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
from tornado.options import define, options

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

define('port', default=5000, help='run on the given port', type=int)
define('debug', default=False, help='run in debug mode', metavar='True|False', type=bool)
define('heartbeat', default=False, help='check client-side heartbeats', metavar='True|False', type=bool)
define('production', default=False, help='run in Production or Testing mode', metavar='True|False', type=bool)

environ['CONFIG'] = './page.conf'

client = MongoClient(MONGODB_DB_URL)
db = client[MONGODB_DB_NAME]

tornado.options.parse_config_file(environ.get('CONFIG'))

level = getattr(logging, tornado.options.options.logging.upper())
# set up app level logger
logger = logging.getLogger('content')
logger.setLevel(logging.DEBUG)
app_handler = logging.StreamHandler(stdout)
app_formatter = logging.Formatter('[%(levelname)1.1s A %(asctime)s] %(message)s | %(module)s:%(lineno)d', '%y%dm%d %H:%M:%S')
app_handler.setFormatter(app_formatter)
app_handler.setLevel(level)
logger.addHandler(app_handler)
logger.propagate = False
# set up framework level logger
frame_handler = logging.StreamHandler(stdout)
frame_formatter = logging.Formatter('[%(levelname)1.1s L %(asctime)s] %(message)s | %(module)s:%(lineno)d', '%y%m%d %H:%M:%S')
frame_handler.setFormatter(frame_formatter)
frame_handler.setLevel(level)
# use the root logger for framework level/Tornado logs
# remove the stderr one added by Tornado by default first
del logging.getLogger().handlers[:]
logging.getLogger().addHandler(frame_handler)
logging.getLogger().setLevel(level)

from sockjs.tornado import SockJSConnection, SockJSRouter
import handlers


class Application(tornado.web.Application):
    def __init__(self):
        options = {'disconnect_delay': 5, 'jsessionid': False, 'sockjs_url': 'https://d1fxtkz8shb9d2.cloudfront.net/sockjs-0.3.min.js'}
        self.WaitRouter = SockJSRouter(WaitingRoomConnection, '/sockjs/wait', options)
        self.GameRouter = SockJSRouter(GameConnection, '/sockjs/game', options)

        GameConnection.ready = 0
        GameConnection.size = 2
        GameConnection.participants = list();

        urls = [
            (r'/', handlers.MainHandler),
            (r'/about', handlers.RegisterHandler),
            (r'/quiz/user/([a-zA-Z0-9])*', handlers.QuizHandler),
            (r'/instructionsemployer([^/]*)', handlers.InstructionsHandler),
            (r'/instructionsemployee([^/]*)', handlers.Instructions2Handler),
            (r'/tutorial1/user/([a-zA-Z0-9])*', handlers.TutorialHandler),
            (r'/tutorial2/user/([a-zA-Z0-9])*', handlers.Tutorial2Handler),
            (r'/welcome([^/]*)', handlers.WelcomeHandler),
            (r'/payment([^/]*)', handlers.PaymentHandler),
            (r'/game/user/([a-zA-Z0-9])*', handlers.GameHandler),
            (r'/api/player/register([^/]*)', handlers.PlayerCreateHandler),
            (r'/api/player/(.*)', handlers.PlayerHandler),
            (r'/api/credential', handlers.CredentialHandler),
            (r'/experimenter/config/sync/activate/([a-zA-Z0-9]+$)', handlers.SyncExperimentLaunchHandler),
            (r'/admin/user', handlers.UserHandler)

        ] + self.WaitRouter.urls + self.GameRouter.urls
        settings = {
            "debug": True,
            "template_path": os.path.join(os.path.dirname(__file__), "templates"),
            "static_path": os.path.join(os.path.dirname(__file__), "static"),
            "cookie_secret": "__TODO:_GENERATE_RANDOM_VALUE_HERE__"
        }

        self.redis_cmd = redis.Redis(db=0, \
        password='dufkeIASF93NSDCJW8sajkef83fjA9fesi3nf8SAFOJ8sibnagnwurqwo', \
        unix_socket_path='/tmp/redis.sock')

        self.redis_pub = Client()
        self.redis_pub.connect_usocket('/tmp/redis.sock', callback=self.auth)

        tornado.web.Application.__init__(self, urls, **settings)

    @tornado.gen.coroutine
    def auth(self):
        status = yield tornado.gen.Task(self.redis_pub.auth, 'dufkeIASF93NSDCJW8sajkef83fjA9fesi3nf8SAFOJ8sibnagnwurqwo')
        if status == 'OK':
            logger.info('[Application] Redis authenticated')
            status = yield tornado.gen.Task(self.redis_pub.select, '1')
            if status == 'OK':
                logger.info('[Application] Redis db 1 selected')


class WaitingRoomConnection(SockJSConnection):

    # game_id:subjects
    # game_id: string
    # subjects: set(connection)
    available_subjects = set()

    # game_id:session_id:subjects
    # game_id: string
    # session_id: int
    # subjects: set(subject_id)
    admitted_subjects = defaultdict(lambda: defaultdict(lambda: set()))

    # game_id:sessions_available
    # game_id: string
    # sessions_available: list
    available_sessions = defaultdict(lambda: list())

    # game_id:size
    # game_id: string
    # size: int
    admission_sizes = 4
    # game_id:status
    # game_id: string
    # status: int
    room_statuses = {}

    # game_id:type
    # game_id: string
    # type: int
    room_types = {}

    WAIT_MSG = 99
    ENTRY_MSG = 100
    ACTIVATE_MSG = 101
    DEACTIVATE_MSG = 102
    FULL_MSG = 103
    CLOSE_MSG = 104
    SESSION_MSG = 105
    HEARTBEAT_MSG = 106
    NO_CONFIG_MSG = 110
    DUPLICATE_MSG = 111

    ENTRY_OPEN = 110
    ENTRY_CLOSE = 111
    ENTRY_FULL = 112

    BLOCK_ADMISSION = 1010
    CONTINUOUS_ADMISSION = 1111

    # heartbeat interval
    heartbeat_interval = 5000
    HEARTBEAT = 'h'

    # constants
    TOT_PLAYERS = 4
    NUM_ROUNDS = 3
    PAIRS = [4, 3, 2, 1]

    # if the subject has already been admitted or has already done this experiment
    
    def _duplicate(self):
        available = False
        admitted = False
        if self.game_id in WaitingRoomConnection.available_subjects:
            available = any(conn.subject_id == self.subject_id for conn in WaitingRoomConnection.available_subjects)
        if self.game_id in WaitingRoomConnection.admitted_subjects:
            admitted = any(subjects for subjects in WaitingRoomConnection.admitted_subjects[self.game_id].itervalues() if self.subject_id in subjects)

        return available or admitted

    # register in the waiting room  
        
    def _register(self, subject, game):
        self.subject_id = subject
        self.admission_sizes = WaitingRoomConnection.TOT_PLAYERS
        try:
            # first check if the waiting room has been configured
            logger.info('[WaitingRoomConnection] admission_sizes: %s', WaitingRoomConnection.admission_sizes)

            present_subjects = WaitingRoomConnection.available_subjects
            self.admission_size = WaitingRoomConnection.admission_sizes
            present_subjects.add(self)
            self.subject_no = len(present_subjects)
            self.partner = WaitingRoomConnection.PAIRS[self.subject_no - 1]
            self.game_id = "gm" + str(self.partner) + str(self.subject_no) if self.partner < self.subject_no else "gm" + str(self.subject_no)+ str(self.partner)
            print "[WaitingRoomConnection] Subject " + self.subject_id + "assigned to game " + self.game_id
            db.players.update_one({'_id': ObjectId(self.subject_id)},{'$set': {'subject_no': self.subject_no, 'game_id': self.game_id}})
            logger.info('[WaitingRoomConnection] WAIT_MSG from subject: %s of game: %s', self.subject_id, self.game_id)
            print "[WaitingRoomConnection] Number of waiting subjects:" + str(self.subject_no) + "/" + str(self.admission_size)

            if len(present_subjects) >= self.admission_size:
                WaitingRoomConnection.room_statuses[self.game_id] = WaitingRoomConnection.ENTRY_OPEN
                logger.info('[WaitingRoomConnection] ENTRY OPEN for game: %s', self.game_id)
                logger.info('[WaitingRoomConnection] Subjects: %d', len(present_subjects))
                self.broadcast(present_subjects, json.dumps({'type': WaitingRoomConnection.ACTIVATE_MSG}))
   
        except Exception as e:
            logger.exception('[WaitingRoomConnection] When registering: %s', e.args[0])
        #finally:
            #if len(WaitingRoomConnection.available_subjects[self.game_id]) >= self.waiting_size - 1:
                #WaitingRoomConnection.room_statuses[self.game_id] = WaitingRoomConnection.ENTRY_CLOSE

    def _entry(self):
        logger.info('[WaitingRoomConnection] ENTRY_MSG from subject: %s of game: %s', self.subject_id, self.game_id)
        try:
            print "Entry" 
        except Exception as e:
            print "exception"
            logger.exception('[WaitingRoomConnection] When entering: %s', e.args[0])

    def _start_heartbeat(self):
        self.missed_heartbeats = 0
        self.heartbeat_timer = tornado.ioloop.PeriodicCallback(self._check_heartbeat, WaitingRoomConnection.heartbeat_interval)
        self.heartbeat_timer.start()

    def _check_heartbeat(self):
        #logger.info('[WaitingRoomConnection] - HEARTBEAT check for subject %s of game %s' % (self.subject_id, self.game_id))
        self.missed_heartbeats += 1
        # drop the connection if 3 consecutive heartbeats are missed
        if self.missed_heartbeats > 2:
            #logger.info('[WaitingRoomConnection] HEARTBEAT reached limit for subject %s of game %s', self.subject_id, self.game_id)
            #logger.info('[WaitingRoomConnection] Closing connection for subject %s of game %s', self.subject_id, self.game_id)
            self.close()

    def _stop_heartbeat(self):
        if self.heartbeat_timer is not None:
            self.heartbeat_timer.stop()
            self.heartbeat_timer = None
            #logger.info('[WaitingRoomConnection] Heartbeat stopped for subject: %s of game: %s' % (self.subject_id, self.game_id))

    def on_open(self, info):
        logger.debug('[WaitingRoomConnection] Transport %s opened for client %s of connection id: %s', self.session.transport_name, info.ip, self.session.session_id)
        self.game_id = None
        self.admission_size = None
        self.subject_id = None
        self.heartbeat_timer = None
        if tornado.options.options.heartbeat:
            self.send(json.dumps({'type': WaitingRoomConnection.HEARTBEAT_MSG}))
            self._start_heartbeat()

    def on_message(self, message):
        # ignore HEARTBEAT
        if message == WaitingRoomConnection.HEARTBEAT:
            #logger.info('[WaitingRoomConnection] HEARTBEAT from subject: %s of game: %s' % (self.subject_id, self.game_id))
            self.missed_heartbeats = 0
        else:
            # any other msg serve the same purpose as heartbeats
            self.missed_heartbeats = 0

            msg = json.loads(message)
            msg_type = msg['type']

            if msg_type == WaitingRoomConnection.WAIT_MSG:
                logger.info("[WaitingRoomConnection] gameid %s", msg['game_id'])
                self._register(msg['subject_id'], msg['game_id'])
            elif msg_type == WaitingRoomConnection.ENTRY_MSG:
                self._entry()

    def on_close(self):
        #logger.info('[WaitingRoomConnection] DISCONNECTION of subject: %s from game: %s', self.subject_id, self.game_id)
        # stop heartbeat if enabled
        if tornado.options.options.heartbeat:
            self._stop_heartbeat()

        # remove from available_subjects if present
        present_subjects = WaitingRoomConnection.available_subjects
        if self in present_subjects:
            present_subjects.remove(self)
            #logger.info('[WaitingRoomConnection] Removed subject: %s from game: %s, number of remaining subjects: %d', self.subject_id, self.game_id, len(present_subjects))

            # if there is still session left and entry is OPEN
            if len(WaitingRoomConnection.available_sessions[self.game_id]) > 0 and WaitingRoomConnection.room_statuses[self.game_id] == WaitingRoomConnection.ENTRY_OPEN:
                # no subject has entered and available subjects drop below required admission size
                if self.game_id not in WaitingRoomConnection.admitted_subjects and len(present_subjects) < self.admission_size:
                    #logger.info('[WaitingRoomConnection] Insufficient subjects waiting before any admission, ENTRY CLOSED for game: %s', self.game_id)
                    WaitingRoomConnection.room_statuses[self.game_id] = WaitingRoomConnection.ENTRY_CLOSE
                    self.broadcast(present_subjects, json.dumps({'type': WaitingRoomConnection.DEACTIVATE_MSG}))
                # some subject(s) has entered and available subjects drop below (required admission size - admitted)
                elif WaitingRoomConnection.room_types[self.game_id] == WaitingRoomConnection.BLOCK_ADMISSION and self.game_id in WaitingRoomConnection.admitted_subjects and \
                len(present_subjects) < (self.admission_size - len(WaitingRoomConnection.admitted_subjects[self.game_id][WaitingRoomConnection.available_sessions[self.game_id][0]])):
                    #logger.info('[WaitingRoomConnection] Insufficient subjects waiting after some admission, ENTRY CLOSED for game: %s', self.game_id)
                    WaitingRoomConnection.room_statuses[self.game_id] = WaitingRoomConnection.ENTRY_CLOSE
                    self.broadcast(present_subjects, json.dumps({'type': WaitingRoomConnection.DEACTIVATE_MSG}))

        #logger.debug('[WaitingRoomConnection] Transport %s closed for client %s of connection id: %s', self.session.transport_name, self.session.conn_info.ip, self.session.session_id)

    @classmethod
    def clear_up(cls, game):
        #logger.info('[WaitingRoomConnection] Cleaning up Waiting Room for game: %s ...', game)
        for available in list(cls.available_subjects):
            available.close()
        del cls.available_subjects

        cls.admitted_subjects.pop(game, None)
        cls.available_sessions.pop(game, None)

        # leave WaitingRoomConnection.admission_sizes and WaitingRoomConnection.room_statuses to manual deactivation
        # or automatic clean-up when all live sessions finish for a given game
        #logger.info('[WaitingRoomConnection] Cleaned up Waiting Room for game: %s', game)

class GameConnection(SockJSConnection):

    WAIT_MSG = 99
    INIT_MSG = 100
    ACTIVATE_MSG = 101
    DEACTIVATE_MSG = 102
    FULL_MSG = 103
    CLOSE_MSG = 104
    SESSION_MSG = 105
    HEARTBEAT_MSG = 106
    NO_CONFIG_MSG = 110
    DUPLICATE_MSG = 111
    ROLE_MSG = 112
    READY_MSG = 113
    CONTRACT_MSG = 114
    EFFORT_MSG = 115
    ACTION_MSG = 116
    FINISH_MSG = 117

    ENTRY_OPEN = 110
    ENTRY_CLOSE = 111
    ENTRY_FULL = 112

    BLOCK_ADMISSION = 1010
    CONTINUOUS_ADMISSION = 1111

    ROLES = ["employer", "employee"]

   # TREATMENTS = {'fl': {'lowBase': 1, 'varWage': 0},
    #              'fh': {'lowBase': 0, 'varWage': 0},
     #             'vl': {'lowBase': 1, 'varWage': 1},
      #            'vh': {'lowBase': 0, 'varWage': 1}}

   # GAMES = {'gm12': 'fl',
    
    #         'gm34': 'fh',
     #        'gm14': 'vl',
      #       'gm24': 'vh',
       #      'gm13': 'fh',
        #     'gm24': 'vl'}

    # heartbeat interval
    heartbeat_interval = 5000
    HEARTBEAT = 'h'

    def _init(self):
        logger.info('[WaitingRoomConnection] INIT_MSG')
        try:
            role = GameConnection.ROLES[GameConnection.ready % 2]
           # user = db.players.find_one({"_id": self.get_argument('oid')})
           # game_id = 'gm12'
            #logger.info('[WaitingRoomConnection] INIT_MSG game id %s', game_id)
            #treatment = TREATMENTS[GAMES[game_id]];
            self.send(json.dumps({'type': GameConnection.ROLE_MSG, 'role': role}))
            GameConnection.ready += 1
            GameConnection.participants.append(self)
            present_subjects = GameConnection.participants
            print len(present_subjects)
            if GameConnection.ready >= GameConnection.size:
                self.broadcast(present_subjects, json.dumps({'type': GameConnection.READY_MSG,
                                                           #  'treatment': TREATMENTS['fl'],   
                                                             'lowBase': bool(random.getrandbits(1)),
                                                             'varWage': bool(random.getrandbits(1))}))
            
        except Exception as e:
            logger.exception('[GameConnection] When waiting: %s', e.args[0])

    def _start_heartbeat(self):
        self.missed_heartbeats = 0
        self.heartbeat_timer = tornado.ioloop.PeriodicCallback(self._check_heartbeat, GameConnection.heartbeat_interval)
        self.heartbeat_timer.start()

    def _check_heartbeat(self):
        #logger.info('[WaitingRoomConnection] - HEARTBEAT check for subject %s of game %s' % (self.subject_id, self.game_id))
        self.missed_heartbeats += 1
        # drop the connection if 3 consecutive heartbeats are missed
        if self.missed_heartbeats > 2:
            #logger.info('[WaitingRoomConnection] HEARTBEAT reached limit for subject %s of game %s', self.subject_id, self.game_id)
            #logger.info('[WaitingRoomConnection] Closing connection for subject %s of game %s', self.subject_id, self.game_id)
            self.close()

    def _stop_heartbeat(self):
        if self.heartbeat_timer is not None:
            self.heartbeat_timer.stop()
            self.heartbeat_timer = None
            #logger.info('[WaitingRoomConnection] Heartbeat stopped for subject: %s of game: %s' % (self.subject_id, self.game_id))

    def on_open(self, info):
        logger.debug('[GameConnection] Transport %s opened for client %s of connection id: %s', self.session.transport_name, info.ip, self.session.session_id)
        self.game_id = None
        self.admission_size = None
        self.subject_id = None
        self.heartbeat_timer = None
        self.participants = 0
        if tornado.options.options.heartbeat:
            self.send(json.dumps({'type': WaitingRoomConnection.HEARTBEAT_MSG}))
            self._start_heartbeat()

    def on_message(self, message):

        self.missed_heartbeats = 0
        # ignore HEARTBEAT
        if message == GameConnection.HEARTBEAT:
            print 'beat'
            #logger.info('[WaitingRoomConnection] HEARTBEAT from subject: %s of game: %s' % (self.subject_id, self.game_id))
        else:
            msg = json.loads(message)
            msg_type = msg['type']

            if msg_type == GameConnection.INIT_MSG:
                logger.info("[GameConnection] Player at Game Screen")

                self._init()
            elif msg_type == GameConnection.CONTRACT_MSG or msg_type == GameConnection.EFFORT_MSG or msg_type == GameConnection.ACTION_MSG:
                if(False):
                    self.broadcast(GameConnection.participants, message)
                else:
                    self.broadcast(GameConnection.participants, message)
            elif msg_type == GameConnection.FINISH_MSG:
                logger.debug('[GameConnection] Entering info for subject %s into db',  msg['oid'])

                db.players.update_one({'_id': ObjectId(msg['oid'])},{'$set': {
                    "status": "finished",
                    "role": msg['role'],
                    "payment": msg['payment'],
                    "wage": msg['wage'],
                    "accept": msg['accept'],
                    "effortLevel": msg['effortLevel'],
                    "action": msg['action'] 
                    }})

    def on_close(self):
        GameConnection.participants = [];
        GameConnection.ready = 0;
        #logger.info('[WaitingRoomConnection] DISCONNECTION of subject: %s from game: %s', self.subject_id, self.game_id)
        # stop heartbeat if enabled
        if tornado.options.options.heartbeat:
            self._stop_heartbeat()
        client.close()

def main():
    tornado.options.parse_command_line() 
    http_server = tornado.httpserver.HTTPServer(Application(),  xheaders=True)
    if options.production:
        options.port = int(os.environ.get("PORT", 33507))
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.current().start()

if __name__ == "__main__":
    main()


