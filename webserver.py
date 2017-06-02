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
        self.SessionRouter = SockJSRouter(SessionConnection, '/sockjs/session', options)

        GameConnection.ready = 0
        GameConnection.size = 2
        WaitingRoomConnection.MAX = 4
        WaitingRoomConnection.TOT_PLAYERS = WaitingRoomConnection.MAX

        urls = [
            (r'/', handlers.MainHandler),
            (r'/session', handlers.SessionHandler),
            (r'/about', RegisterHandler),
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
            (r'/admin/user', handlers.UserHandler),
            (r'/admin', AdminHandler)

        ] + self.WaitRouter.urls + self.GameRouter.urls + self.SessionRouter.urls
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

class SessionConnection(SockJSConnection):

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

    active_sessions = []

    session_dict = defaultdict(lambda: list())


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
    ADMIN_MSG = 107
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
    NUM_ROUNDS = 2
    PAIRS = [[4, 3, 2, 1],[4,3,2,1]]

    EMPLOYER_FIRST = []
    EMPLOYEE_FIRST = []
    MATCHED = []
    DROPPED = []

    NUMBERS = {}

    US_Players = 0
    India_Players = 0

    present_subjects = set()
    admin_client = 0

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
        
    def _register(self, mid):    
        try:
            self.mid = mid
            SessionConnection.US_Players = SessionConnection.US_Players + 1
            SessionConnection.present_subjects = SessionConnection.available_subjects
            SessionConnection.present_subjects.add(self)
            
        except Exception as e:
            logger.exception('[WaitingRoomConnection] When registering: %s', e.args[0])

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
        logger.debug('[SessionConnection] Transport %s opened for client %s of connection id: %s', self.session.transport_name, info.ip, self.session.session_id)
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

            if msg_type == SessionConnection.WAIT_MSG:
                self._register(msg["mid"])
            elif msg_type == SessionConnection.ENTRY_MSG:
                self._entry()
            elif msg_type == SessionConnection.ADMIN_MSG:
                SessionConnection.admin_client = self

    def on_close(self):
        #logger.info('[WaitingRoomConnection] DISCONNECTION of subject: %s from game: %s', self.subject_id, self.game_id)
        # stop heartbeat if enabled
        if SessionConnection.admin_client != self:
            SessionConnection.US_Players = SessionConnection.US_Players - 1
            SessionConnection.present_subjects.remove(self)

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


class WaitingRoomConnection(SockJSConnection):

    # game_id:subjects
    # game_id: string
    # subjects: set(connection)
    available_subjects = defaultdict(lambda: defaultdict(lambda: set()))

    # game_id:session_id:subjects
    # game_id: string
    # session_id: int
    # subjects: set(subject_id)
    admitted_subjects = defaultdict(lambda: defaultdict(lambda: set()))

    # game_id:sessions_available
    # game_id: string
    # sessions_available: list
    available_sessions = defaultdict(lambda: list())

    oid_dict = {}
    session_dict = {}
    admin_client = 0


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
    NUM_ROUNDS = 2
    PAIRS = [[4, 3, 2, 1],[4,3,2,1]]

    EMPLOYER_FIRST = []
    EMPLOYEE_FIRST = []
    MATCHED = []
    DROPPED = []

    NUMBERS = {}

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
        
    def _register(self, subject, game, rd):
        WaitingRoomConnection.admin_client = self
        self.subject_id = subject
        self.rd = int(rd)
        self.name = WaitingRoomConnection.oid_dict[str(subject)]
        self.session_id = WaitingRoomConnection.session_dict[self.name]
        GameConnection.ROUNDS[str(self.subject_id)] = self.rd
        logger.info("[WaitingRoomConnection] Subject " + self.subject_id + " waiting for Round " + rd)
        try:

            self.admission_size = WaitingRoomConnection.TOT_PLAYERS
            WaitingRoomConnection.available_subjects[self.session_id][self.rd].add(self)
            present_subjects = WaitingRoomConnection.available_subjects[self.session_id][self.rd]
            self.subject_no = len(present_subjects) if self.rd == 1 else WaitingRoomConnection.NUMBERS[str(self.subject_id)]

            if self.rd == 1:
                WaitingRoomConnection.NUMBERS[str(self.subject_id)] = self.subject_no
                logger.info("[WaitingRoomConnection] Subject " + str(self.subject_id) + " assigned #" + str(self.subject_no))

                GameConnection.NUMBERS[str(self.subject_id)] = self.subject_no
                WaitingRoomConnection.TOT_PLAYERS = WaitingRoomConnection.MAX
            
            repeat = True
            count = 0
            while (repeat):
                repeat = False
                count = count + 1
                if len(present_subjects) == 1:
                    GameConnection.PARTICIPANTS[self.rd] = defaultdict(lambda: set())
                    GameConnection.GAMES[self.rd] = {}
                    if self.rd == 1:
                      WaitingRoomConnection.EMPLOYER_FIRST = random.sample(xrange(1, WaitingRoomConnection.TOT_PLAYERS+1), 2)
                      WaitingRoomConnection.EMPLOYEE_FIRST = []
                    WaitingRoomConnection.MATCHED = []
                    for i in xrange(1, WaitingRoomConnection.TOT_PLAYERS+1):
                        if not i in WaitingRoomConnection.EMPLOYER_FIRST and not i in WaitingRoomConnection.EMPLOYEE_FIRST:
                            WaitingRoomConnection.EMPLOYEE_FIRST.append(i)
                    for j in WaitingRoomConnection.EMPLOYER_FIRST:
                        if j in WaitingRoomConnection.MATCHED:
                            continue
                        available = []
                        #logger.info('[WaitingRoomConnection] employee first for %d: %s', j, str(WaitingRoomConnection.EMPLOYEE_FIRST))
                        #logger.info('[WaitingRoomConnection] matched for %d: %s', j, str(WaitingRoomConnection.MATCHED))

                        for k in WaitingRoomConnection.EMPLOYEE_FIRST:
                            add = True
                            if k not in WaitingRoomConnection.MATCHED and k not in WaitingRoomConnection.DROPPED:
                                for l in range(self.rd - 1):
                                    if WaitingRoomConnection.PAIRS[l][j - 1] == k:
                                        add = False
                                if add:      
                                    available.append(k)
                        logger.info('[WaitingRoomConnection] available for %d: %s', j, str(available))

                        if (len(available) == 0 and count < 50):
                            repeat = True
                        else:
                            partner = 0
                            if (len(available) != 0):
                                partner = random.choice(available)
                                WaitingRoomConnection.PAIRS[self.rd - 1][partner - 1] = j
                                WaitingRoomConnection.MATCHED.append(partner)


                            logger.info('[WaitingRoomConnection] partner for %d: %d', j, partner)

                            WaitingRoomConnection.PAIRS[self.rd - 1][j - 1] = partner
                            WaitingRoomConnection.MATCHED.append(j)
            
            if self.rd == 1 and self.subject_no == 1:
                logger.info('[WaitingRoomConnection] employer first: %s', str(WaitingRoomConnection.EMPLOYER_FIRST))
                logger.info('[WaitingRoomConnection] employee first: %s', str(WaitingRoomConnection.EMPLOYEE_FIRST))


                print "[WaitingRoomConnection] Pairs: " + str(WaitingRoomConnection.PAIRS[self.rd-1]);
            WaitingRoomConnection.MATCHED = [];


            self.partner = WaitingRoomConnection.PAIRS[self.rd - 1][self.subject_no - 1]
            self.game_id = "nogame"
            if (self.partner != 0):
                self.game_id = "gm" + str(self.partner) + str(self.subject_no) if self.partner < self.subject_no else "gm" + str(self.subject_no)+ str(self.partner)

            GameConnection.GAMES[self.rd][str(self.subject_id)] = self.game_id
            GameConnection.PAST_PARTNERS[str(self.subject_id)].append(self.partner)

            #roles are assigned and roles are switched at round 2 currently
            GameConnection.PLAYER_ROLES[str(self.subject_id)] = "employer" if ((self.subject_no in WaitingRoomConnection.EMPLOYER_FIRST and int(self.rd) < 2) or (self.subject_no in WaitingRoomConnection.EMPLOYEE_FIRST and int(self.rd) >= 2)) else "worker"
            print "[WaitingRoomConnection] Subject " + self.subject_id + " assigned to role " + GameConnection.PLAYER_ROLES[str(self.subject_id)]
            print "[WaitingRoomConnection] Subject " + self.subject_id + "assigned to game " + self.game_id
            db.players.update_one({'_id': ObjectId(self.subject_id)},{'$set': {'subject_no': self.subject_no, 'game_id': self.game_id}})
            logger.info('[WaitingRoomConnection] WAIT_MSG from subject: %s of game: %s', self.subject_id, self.game_id)
            print "[WaitingRoomConnection] Number of waiting subjects:" + str(len(present_subjects)) + "/" + str(self.admission_size)

            if len(present_subjects) >= self.admission_size:
                WaitingRoomConnection.room_statuses[self.game_id] = WaitingRoomConnection.ENTRY_OPEN
                logger.info('[WaitingRoomConnection] ENTRY OPEN for games')
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
        logger.debug('[SessionConnection] Transport %s opened for client %s of connection id: %s', self.session.transport_name, info.ip, self.session.session_id)
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
                name = WaitingRoomConnection.oid_dict[str(msg['subject_id'])]
                adminTell(name)
                self._register(msg['subject_id'], msg['game_id'], msg['rd'])
            elif msg_type == WaitingRoomConnection.ENTRY_MSG:
                self._entry()

    def on_close(self):
        logger.info('[WaitingRoomConnection] DISCONNECTION of subject: %s from game %s waiting room in round %d', self.subject_id, self.game_id, self.rd)
        # stop heartbeat if enabled

        if tornado.options.options.heartbeat:
            self._stop_heartbeat()

        # remove from available_subjects if present
 
        if self in WaitingRoomConnection.available_subjects[self.session_id][self.rd]:
            WaitingRoomConnection.available_subjects[self.session_id][self.rd].remove(self)

        print "Finished closing connection for subject " + self.subject_id

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
    QUIT_MSG = 118

    ENTRY_OPEN = 110
    ENTRY_CLOSE = 111
    ENTRY_FULL = 112

    BLOCK_ADMISSION = 1010
    CONTINUOUS_ADMISSION = 1111

    ROLES = ["employer", "worker"]

    PARTICIPANTS = defaultdict(lambda: defaultdict(lambda: set()))
    GAMES = defaultdict(lambda: defaultdict(str))
    NUMBERS = {}
    PAST_PARTNERS = defaultdict(lambda: list())
    PLAYER_ROLES = {}
    ROUNDS = defaultdict(lambda: int)

    # heartbeat interval
    heartbeat_interval = 5000
    HEARTBEAT = 'h'

    def _init(self, oid):
        try:
            self.rd = GameConnection.ROUNDS[str(oid)]
            game_id = GameConnection.GAMES[self.rd][str(oid)]


            #To change treatment, edit following code
            # if (self.rd == 2) {
            #     lowBase = True
            #     varWage = False
            # }

            for k in WaitingRoomConnection.DROPPED:
                print "The player " + str(k) + " has been dropped"
                if str(k) in game_id:
                    game_id = "nogame"

            print "Game ID for " + str(oid) + " is " + game_id

            logger.info('[GameConnection] Initializing game ' + game_id)


            GameConnection.PARTICIPANTS[self.rd][game_id].add(self)
            present_subjects = GameConnection.PARTICIPANTS[self.rd][game_id]
            role = GameConnection.PLAYER_ROLES[str(oid)]
            self.send(json.dumps({'type': GameConnection.ROLE_MSG, 'role': role, 'round': len(GameConnection.PAST_PARTNERS[str(oid)])}))
            print len(present_subjects)
            if len(present_subjects) >= GameConnection.size:
                logger.info('[GameConnection] READY_MSG for game %s' + game_id)
                self.broadcast(present_subjects, json.dumps({'type': GameConnection.READY_MSG,

                                                                #  'treatment' is determined here  
                                                             'game_id': game_id,
                                                             'subject_no': GameConnection.NUMBERS[str(oid)],
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

                self._init(msg['subject_id'])
            elif msg_type == GameConnection.CONTRACT_MSG or msg_type == GameConnection.EFFORT_MSG or msg_type == GameConnection.ACTION_MSG:
                game_id = msg['game_id']
                self.broadcast(GameConnection.PARTICIPANTS[self.rd][game_id], message)
            elif msg_type == GameConnection.QUIT_MSG:
                WaitingRoomConnection.DROPPED.append(msg['subject_no'])
                WaitingRoomConnection.TOT_PLAYERS = WaitingRoomConnection.TOT_PLAYERS - 1

                for u in GameConnection.GAMES[self.rd + 1]:
                    game_check = GameConnection.GAMES[self.rd + 1][u]
                    if str(msg['subject_no']) in game_check:
                        GameConnection.GAMES[self.rd + 1][u] = "nogame"
                logger.info("[GameConnection] Player " + str(msg['subject_no']) + " disconnected from game " + msg['game_id'])
                game_id = msg['game_id']
                self.broadcast(GameConnection.PARTICIPANTS[self.rd][game_id], message)
            elif msg_type == GameConnection.FINISH_MSG:
                game_id = msg['game_id']
                logger.debug('[GameConnection] Entering info for subject %s into db',  msg['oid'])

                #After game, all parameters are handled - put into database 
                db.players.update_one({'_id': ObjectId(msg['oid'])},{'$set': {
                    "status": "finished",
                    "role": msg['role'],
                    "payment": msg['payment'],
                    "wage": msg['wage'],
                    "accept": msg['accept'],
                    "effortLevel": msg['effortLevel'],
                    "action": msg['action'] 
                    }})

                GameConnection.PARTICIPANTS[self.rd][game_id] = set();


    def on_close(self):
        #logger.info('[WaitingRoomConnection] DISCONNECTION of subject: %s from game: %s', self.subject_id, self.game_id)
        # stop heartbeat if enabled
        if tornado.options.options.heartbeat:
            self._stop_heartbeat()
        client.close()

class RegisterHandler(tornado.web.RequestHandler):
    def post(self):
        name = self.get_argument('name')
        result = db.players.insert_one({
            "name" : name
            })

        WaitingRoomConnection.oid_dict[str(result.inserted_id)] = name
        self.render("about.html", title="Oxford Experiments", oid = result.inserted_id)

class AdminHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("admin.html",usp=SessionConnection.US_Players,ip=SessionConnection.India_Players,sessions=SessionConnection.active_sessions)

    def post(self):
        if self.get_argument('action') == "sessionStart":
            createSession("US-only", self.get_argument('usAllNum'))
            self.render("admin.html",usp=SessionConnection.US_Players,ip=SessionConnection.India_Players,sessions=SessionConnection.active_sessions)
        elif self.get_argument('action') == "gameStart":
            startGame(self.get_argument('session'))
            self.render("admin.html",usp=SessionConnection.US_Players,ip=SessionConnection.India_Players,sessions=SessionConnection.active_sessions)

def adminTell(name):
    SessionConnection.admin_client.broadcast([SessionConnection.admin_client], json.dumps({'type': WaitingRoomConnection.ACTIVATE_MSG, 'name': name}))

def startGame(session_id):
    print "game started"
    present_subjects = WaitingRoomConnection.available_subjects[int(session_id)][1]
    print session_id
    print present_subjects
    print WaitingRoomConnection.admin_client
    WaitingRoomConnection.admin_client.broadcast(present_subjects, json.dumps({'type': WaitingRoomConnection.ACTIVATE_MSG}))
    


def createSession(sessionType, num):
    print "Creating session of type " + sessionType + " with " + num + " players."
    if(SessionConnection.present_subjects and len(SessionConnection.present_subjects) >= 0):
        print str(num) + " subjects: " + str(len(SessionConnection.present_subjects)) + " " + str(SessionConnection.present_subjects)
        sample = random.sample(SessionConnection.present_subjects, int(num))
        
        session_id = len(SessionConnection.active_sessions)


        ids = []
        for subject in sample:
            ids.append(subject.mid)
            WaitingRoomConnection.session_dict[subject.mid] = session_id

        session_obj = {'participants': ids, 'id': session_id}

        SessionConnection.session_dict[session_id] = sample
        SessionConnection.active_sessions.append(session_obj)
        sample.append(SessionConnection.admin_client)
        SessionConnection.admin_client.broadcast(sample, json.dumps({'type': SessionConnection.ACTIVATE_MSG}))
        #SessionConnection.admin_client.broadcast(SessionConnection.admin_client, json.dumps({'type': SessionConnection.ACTIVATE_MSG}))




def main():
    tornado.options.parse_command_line() 
    http_server = tornado.httpserver.HTTPServer(Application(),  xheaders=True)
    if options.production:
        options.port = int(os.environ.get("PORT", 33507))
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.current().start()

if __name__ == "__main__":
    main() 


