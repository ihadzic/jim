#!/usr/bin/env python2
#
# Copyright (c) 2016, Ilija Hadzic <ilijahadzic@gmail.com>
#
# MIT License, see LICENSE.txt for details

import tornado
import os
import sys
import binascii
import rules
import util
import string
from tornado import web, httpserver
from datetime import datetime
from datetime import timedelta

_http_server = None
_https_server = None
_log = None
_database = None
_bootstrap_token = None
_recent_days = 7

class DynamicBaseHandler(tornado.web.RequestHandler):
    def log_request(self):
        x_real_ip = self.request.headers.get("X-Real-IP")
        remote_ip = x_real_ip or self.request.remote_ip
        username = self.current_user.get('username') or 'nobody'
        _log.info("log_request: {}@{} {}".format(username, remote_ip, self.request))

    def finish_failure(self, err = None, status = None):
        if status:
            self.set_status(status)
        retval = { 'result': 'failure', 'reason': err }
        self.finish(retval)

    def finish_success(self, args = {}):
        retval = { 'result': 'success' }
        retval.update(args)
        self.finish(retval)

    def get_args(self):
        try:
            args = self.request.query_arguments
            return args
        except:
            self.finish_failure("query parse error")
            return None

    def initialize(self):
        self.set_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.set_header("Pragma", "no-cache")
        self.set_header("Expires", "0")

    def get_current_user(self):
        return { 'admin': util.bool_or_none(self.get_secure_cookie('admin')),
                 'id': util.int_or_none(self.get_secure_cookie('id')),
                 'username': self.get_secure_cookie('username') }

    def authorized(self, admin = False, quiet = False):
        if self.current_user['id'] != None:
            if admin:
                if self.current_user['admin']:
                    return True
                else:
                    if not quiet:
                        self.finish_failure('user is not admin', 401)
                    return False
            else:
                return True
        else:
            if not quiet:
                self.finish_failure('user is not logged in', 401)
            return False

class RootHandler(tornado.web.RequestHandler):
    def get(self):
        self.redirect('/login', permanent = True)

class MainMenuHandler(DynamicBaseHandler):
    def get(self):
        self.log_request()
        if self.authorized(quiet = True):
            self.render('main_menu.html',
                        admin = self.current_user['admin'])
        else:
            self.redirect('/login')

class GenericAdminFormHandler(DynamicBaseHandler):
    def generic_get(self, form_filename):
        self.log_request()
        if self.authorized(admin = True, quiet = True):
            self.render(form_filename)
        else:
            self.redirect('/login')

class AccountFormHandler(GenericAdminFormHandler):
    def get(self):
        self.generic_get('account_form.html')

class PlayerFormHandler(GenericAdminFormHandler):
    def get(self):
        self.generic_get('player_form.html')

class MatchFormHandler(GenericAdminFormHandler):
    def get(self):
        self.generic_get('match_form.html')

class LoginHandler(DynamicBaseHandler):
    def get(self):
        self.log_request()
        if self.current_user['id']:
            self.redirect('/main_menu')
        else:
            self.render('login.html',
                        color = 'black',
                        please_log_in = 'Please log in')

    def post(self):
        self.log_request()
        username = self.get_argument('name')
        password = self.get_argument('password')
        if _database.no_admins():
            # if there are no admins in the system, only accept bootstrap token
            if username == 'bootstrap' and password == _bootstrap_token:
                self.set_secure_cookie('admin', 'True')
                self.set_secure_cookie('username', username)
                self.set_secure_cookie('id', '0')
                self.redirect('/main_menu')
            else:
                self.redirect('/login_incorrect')
        else:
            # otherwise, authenticate in a regular way
            admin_id = _database.check_password(username, password, 'admins')
            if admin_id:
                self.set_secure_cookie('admin', 'True')
                self.set_secure_cookie('username', username)
                self.set_secure_cookie('id', str(admin_id))
                self.redirect('/main_menu')
            else:
                player_id = _database.check_password(username, password, 'players')
                if player_id:
                    self.set_secure_cookie('admin', 'False')
                    self.set_secure_cookie('username', username)
                    self.set_secure_cookie('id', str(player_id))
                    self.redirect('/main_menu')
                else:
                    self.redirect('/login_incorrect')

class LoginIncorrectHandler(LoginHandler):
    def get(self):
        self.log_request()
        if self.current_user['id']:
            self.redirect('/main_menu')
        else:
            self.render('login.html',
                        color = 'red',
                        please_log_in = 'Login incorrect (please try again)')

class LogoutHandler(DynamicBaseHandler):
    def get(self):
        self.log_request()
        self.clear_cookie('admin')
        self.clear_cookie('username')
        self.clear_cookie('id')
        self.redirect('/login')

class DateHandler(DynamicBaseHandler):
    def get(self):
        self.log_request()
        if self.current_user['id']:
            if self.current_user['admin']:
                name = tornado.escape.xhtml_escape('admin:' + str(self.current_user['id']))
            else:
                name = tornado.escape.xhtml_escape('player:' + str(self.current_user['id']))
        else:
            name = 'nobody'
        self.render('date.html',
                    date_string = str(datetime.now()),
                    user_string = name)

class LadderHandler(DynamicBaseHandler):
    def get(self):
        self.log_request()
        if self.authorized(quiet = True):
            args = self.get_args()
            today = datetime.ctime(datetime.now());
            try:
                matches_since = datetime.strptime(args['matches_since'][0], '%Y-%m-%d')
            except:
                matches_since = datetime.now() - timedelta(_recent_days)
            since_str = str(matches_since).split()[0]
            _log.info("ladder: matches_since: {}".format(since_str))
            self.render('ladder.html',
                        date_string = today,
                        a_ladder = _database.get_ladder('a'),
                        b_ladder = _database.get_ladder('b'),
                        c_ladder = _database.get_ladder('c'),
                        u_ladder = _database.get_ladder('unranked')
                        )
        else:
            self.redirect('/login')

class RosterHandler(DynamicBaseHandler):
    def get(self):
        self.log_request()
        if self.authorized(quiet = True):
            self.render('roster.html',
                        date_string = datetime.ctime(datetime.now()),
                        roster = _database.get_roster()
                        )
        else:
            self.redirect('/login')

class PlayerBaseHandler(DynamicBaseHandler):
    def parse_args(self, args, add_flag, password):
        try:
            username = args['username'][0]
        except:
            username = None
        if add_flag and not username:
            self.finish_failure('username missing')
            return None
        if add_flag and not password:
            self.finish_failure('password missing')
            return None
        try:
            first_name = args['first_name'][0]
        except:
            first_name = None
        if add_flag and not first_name:
            self.finish_failure("player fist name missing")
            return None
        try:
            last_name = args['last_name'][0]
        except:
            last_name = None
        if add_flag and not last_name:
            self.finish_failure("player last name missing")
            return None
        try:
            home_phone = args['home_phone'][0]
        except:
            home_phone = None
        try:
            cell_phone = args['cell_phone'][0]
        except:
            cell_phone = None
        try:
            work_phone = args['work_phone'][0]
        except:
            work_phone = None
        if add_flag and not (home_phone or cell_phone or work_phone):
            self.finish_failure("at least one phone number is required")
            return None
        try:
            email = args['email'][0]
        except:
            email = None
        if add_flag and not email:
            self.finish_failure("e-mail is required")
            return None
        try:
            ladder = args['ladder'][0].lower()
        except:
            ladder = None
        if add_flag and not ladder:
            ladder = 'unranked'
        try:
            company = args['company'][0]
        except:
            company = None
        if add_flag and not company:
            self.finish_failure("company name is required")
            return None
        if add_flag and not ladder in [ 'a', 'b', 'c', 'unranked', 'beginner' ]:
            self.finish_failure("invalid ladder category")
            return None
        try:
            initial_points_str = args['initial_points'][0]
        except:
            if add_flag:
                initial_points_str = '0'
            else:
                initial_points_str = None
        if initial_points_str:
            try:
                initial_points = int(initial_points_str)
            except:
                self.finish_failure("initial ladder points must be an integer")
                return None
            if initial_points < 0:
                self.finish_failure("initial ladder points cannot be negative")
                return None
        else:
            if add_flag:
                initial_points = 0
            else:
                initial_points = None
        try:
            active = util.str_to_bool(args['active'][0])
            if active == None:
                self.finish_failure("active-flag must be boolean")
                return
        except:
            if add_flag:
                active = True
            else:
                active = None
        player = { 'username': username,
                   'password': password,
                   'first_name': first_name,
                   'last_name' : last_name,
                   'email' : email,
                   'home_phone' : home_phone,
                   'work_phone' : work_phone,
                   'cell_phone' : cell_phone,
                   'company': company,
                   'ladder': ladder,
                   'initial_points': initial_points,
                   'active': active}
        if add_flag:
            return player
        else:
            return util.purge_null_fields(player)

class AddPlayerHandler(PlayerBaseHandler):

    def update_database(self, player):
        player_id, err = _database.update_player(player)
        if player_id > 0:
            player.update({'player_id': player_id})
            return True, err
        else:
            return False, err

    def get_or_post(self, password):
        self.log_request()
        if not self.authorized(admin = True):
            return
        args = self.get_args()
        if args == None:
            return
        player = self.parse_args(args, True, password)
        if player == None:
            return
        r, err = self.update_database(player)
        if r:
            self.finish_success(player)
        elif err:
            self.finish_failure(err)
        else:
            self.finish_failure("could not add player to the database")

    def post(self):
        password = self.request.body
        if password:
            self.get_or_post(password)
        else:
            self.get_or_post(None)

    def get(self):
        self.get_or_post(None)

class DelPlayerHandler(PlayerBaseHandler):
    def get_or_post(self):
        self.log_request()
        if not self.authorized(admin = True):
            return
        args = self.get_args()
        if args == None:
            return
        try:
            player_id = int(args['player_id'][0])
        except:
            self.finish_failure("missing or invalid player ID")
            return
        if _database.delete_player(player_id):
            self.finish_success({'player_id': player_id})
        else:
            self.finish_failure("could not delete selected player")

    def get(self):
        self.get_or_post()

    def post(self):
        self.get_or_post()

class UpdatePlayerHandler(PlayerBaseHandler):

    def update_database(self, player, player_id):
        player_id, err = _database.update_player(player, player_id)
        if player_id > 0:
            player.update({'player_id': player_id})
            return True, err
        else:
            return False, err

    def get_or_post(self, password):
        self.log_request()
        if not self.authorized(admin = True):
            return
        args = self.get_args()
        if args == None:
            return
        player = self.parse_args(args, False, password)
        if player == None:
            return
        try:
            player_id = int(args['player_id'][0])
        except:
            self.finish_failure("missing or invalid player ID")
            return
        r, err = self.update_database(player, player_id)
        if r:
            self.finish_success(player)
        elif err:
            self.finish_failure(err)
        else:
            self.finish_failure("could not add player to the database")

    def post(self):
        password = self.request.body
        if password:
            self.get_or_post(password)
        else:
            self.get_or_post(None)

    def get(self):
        self.get_or_post(None)

class GetPlayerHandler(PlayerBaseHandler):
    def get_or_post(self):
        self.log_request()
        if not self.authorized():
            return
        args = self.get_args()
        if args == None:
            return
        # everything is optional except an empty set
        player = self.parse_args(args, False, None)
        try:
            # don't let some bozo search us by password
            del player['password']
        except:
            pass
        if player == None:
            player = {}
        try:
            player_id = int(args['player_id'][0])
        except:
            player_id = None
        if player_id:
            player.update({'player_id': player_id})
        try:
            op = args['op'][0].lower()
        except:
            op = 'and'
        if not op:
            op = 'and'
        elif op != 'and' and op != 'or':
            self.finish_failure("invalid search operator")
            return
        _log.info("get_player: search operator is '{}'".format(op))
        matched_players = _database.lookup_player(player, op)
        self.finish_success({'entries': matched_players})

    def get(self):
        self.get_or_post()

    def post(self):
        self.get_or_post()

class AddMatchHandler(DynamicBaseHandler):
    def update_database(self, match):
        match_id, winner_last_name, loser_last_name, err = _database.add_match(match)
        if match_id > 0:
            match.update({'match_id': match_id})
            match.update({'winner_last_name': winner_last_name})
            match.update({'loser_last_name': loser_last_name})
            return True, err
        else:
            return False, err

    def get(self):
        self.log_request()
        if not self.authorized(admin = True):
            return
        args = self.get_args()
        if args == None:
            return
        try:
            challenger_id = int(args['challenger'][0])
        except:
            self.finish_failure("challenger ID missing or invalid")
            return
        try:
            opponent_id = int(args['opponent'][0])
        except:
            self.finish_failure("opponent ID missing or invalid")
            return
        try:
            cgames_str = args['cgames']
            cgames = [ int(g) for g in cgames_str ]
        except:
            self.finish_failure("list of games won by challenger missing or invalid")
            return
        try:
            ogames_str = args['ogames']
            ogames = [ int(g) for g in ogames_str ]
        except:
            self.finish_failure("list of games won by opponent missing or invalid")
            return
        try:
            forfeited = util.str_to_bool(args['forfeited'][0])
            if forfeited == None:
                self.finish_failure("forfeited-flag must be boolean")
                return
        except:
            forfeited = False
        try:
            retired = util.str_to_bool(args['retired'][0])
            if retired == None:
                self.finish_failure("retired-flag must be boolean")
                return
        except:
            retired = False
        try:
            tournament = util.str_to_bool(args['tournament'][0])
            if tournament == None:
                self.finish_failure("tournament-flag must be boolean")
                return
        except:
            tournament = False
        try:
            date = datetime.strptime(args['date'][0], '%Y-%m-%d')
        except:
            self.finish_failure("match date missing")
            return
        winner_id, cpoints, opoints, err = rules.process_match(challenger_id, opponent_id, cgames, ogames, retired, forfeited, date, tournament)
        if err:
            self.finish_failure(err)
            return
        match = {'opponent_id': opponent_id,
                 'challenger_id': challenger_id,
                 'winner_id': winner_id,
                 'cgames': string.join(cgames_str, ','),
                 'ogames': string.join(ogames_str, ','),
                 'cpoints': cpoints,
                 'opoints': opoints,
                 'retired': retired,
                 'forfeited' : forfeited,
                 'date': str(date).split()[0],
                 'tournament': tournament}
        # TODO: we also need to do the following along with adding
        #       the match to the database:
        # 1) promote the player if applicable
        # 2) record the match ID that promoted the player to the current ladder
        # 3) record the ladder from which the player came from (so that we can
        #    demote him/her if the promoting match has been deleted
        # All of the above must be done in transactional manner so that we don't
        # end up with inconsistent records if something crashes in the middle
        # of the transaction
        r, err = self.update_database(match)
        if r:
            self.finish_success(match)
        else:
            self.finish_failure(err)

class DelMatchHandler(DynamicBaseHandler):
    def get(self):
        self.log_request()
        if not self.authorized(admin = True):
            return
        args = self.get_args()
        if args == None:
            return
        try:
            match_id = int(args['match_id'][0])
        except:
            self.finish_failure("missing or invalid match ID")
            return
        # TODO: remove the entry from the database
        # don't forget that if we are deleting a match that promoted
        # a player, that the player must be demoted to the rank it came from
        self.finish_success({'match_id': match_id})

class GetMatchHandler(DynamicBaseHandler):
    def get(self):
        self.log_request()
        if not self.authorized():
            return
        args = self.get_args()
        if args == None:
            return
        try:
            challenger_id = int(args['challenger_id'][0])
        except:
            challenger_id = None
        try:
            opponent_id = int(args['opponent_id'][0])
        except:
            opponent_id = None
        try:
            winner_id = int(args['winner_id'][0])
        except:
            winner_id = None
        try:
            date = datetime.strptime(args['date'][0], '%Y-%m-%d')
        except:
            date = None
        try:
            since = datetime.strptime(args['since'][0], '%Y-%m-%d')
        except:
            since = None
        try:
            ladder = args['ladder'][0].lower()
        except:
            ladder = None
        if since and date:
            self.finish_failure("cannot have both since and date parameters")
            return
        keys =  util.purge_null_fields({ 'challenger_id': challenger_id,
                                         'opponent_id': opponent_id,
                                         'winner_id': winner_id,
                                         'ladder' : ladder,
                                         'date': str(date).split()[0] if date else None, 
                                         'since': str(since).split()[0] if since else None })
        _log.info("keys = {}".format(keys))
        matches = _database.lookup_match(keys)
        self.finish_success({'entries': matches})

class UpdateMatchHandler(DynamicBaseHandler):
    def get(self):
        self.log_request()
        self.finish_failure("operation not supported", 400)
        return

class AccountBaseHandler(DynamicBaseHandler):
    def parse_args(self, args, add_flag, password):
        try:
            username = args['username'][0]
        except:
            return None, "username missing"
        if not password:
            return None, "password missing"
        if not add_flag:
            try:
                account_id = int(args['account_id'][0])
            except:
                account_id = None
        else:
            account_id = None
        if add_flag:
            account = {
                'username' : username,
                'password' : password
                }
            return account, None
        else:
            account = {
                'username' : username,
                'password' : password,
                'account_id' : account_id
                }
            return util.purge_null_fields(account), None

class AddAccountHandler(AccountBaseHandler):
    def update_database(self, account):
        account_id, err = _database.update_account(account)
        if account_id > 0:
            account.update({'account_id': account_id})
            return True, err
        else:
            return False, err

    def get_or_post(self, password):
        self.log_request()
        if not self.authorized(admin = True):
            return
        args = self.get_args()
        if args == None:
            return
        account, err = self.parse_args(args, True, password)
        if account == None:
            self.finish_failure(err)
            return
        r, err = self.update_database(account)
        if r:
            self.finish_success(account)
        else:
            self.finish_failure(err)

    def get(self):
        self.get_or_post(None)

    def post(self):
        password = self.request.body
        if password:
            self.get_or_post(password)
        else:
            self.get_or_post(None)

class DelAccountHandler(AccountBaseHandler):
    def get_or_post(self):
        self.log_request()
        if not self.authorized(admin = True):
            return
        args = self.get_args()
        if args == None:
            return
        try:
            username = args['username'][0]
        except:
            self.finish_failure("missing or invalid username")
            return
        r, err =  _database.delete_account(username)
        if r > 0:
            self.finish_success({'account_id': r})
        else:
            self.finish_failure(err)

    def get(self):
        self.get_or_post()

    def post(self):
        self.get_or_post()

class GetAccountHandler(AccountBaseHandler):
    def get_or_post(self):
        self.log_request()
        if not self.authorized(admin = True):
            return
        args = self.get_args()
        if args == None:
            return
        account, err = self.parse_args(args, False, None)
        # even an empty set is optional
        if account == None:
            account = {}
        try:
            # don't let some bozo search us by password
            del account['password']
        except:
            pass
        try:
            op = args['op'][0].lower()
        except:
            op = 'and'
        if not op:
            op = 'and'
        elif op != 'and' and op != 'or':
            self.finish_failure("invalid search operator")
            return
        _log.info("get_account: search operator is '{}'".format(op))
        matched_accounts = _database.lookup_account(account, op)
        self.finish_success({'entries': matched_accounts})

    def get(self):
        self.get_or_post()

    def post(self):
        self.get_or_post()

class UpdateAccountHandler(AccountBaseHandler):
    def update_database(self, account, username):
        account_id, err = _database.update_account(account, username)
        if account_id > 0:
            account.update({'account_id': account_id})
            return True, err
        else:
            return False, err

    def get_or_post(self, password):
        self.log_request()
        if not self.authorized(admin = True):
            return
        args = self.get_args()
        if args == None:
            return
        account, err = self.parse_args(args, False, password)
        if account == None:
            self.finish_failure(err)
            return
        username = account.get('username')
        assert username
        r, err = self.update_database(account, username)
        if r:
            self.finish_success(account)
        else:
            self.finish_failure(err)

    def get(self):
        self.get_or_post(None)

    def post(self):
        password = self.request.body
        if password:
            self.get_or_post(password)
        else:
            self.get_or_post(None)

class GetReportHandler(DynamicBaseHandler):
    def get(self):
        self.log_request()
        if not self.authorized():
            return
        args = self.get_args()
        if args == None:
            return
        try:
            latest = util.str_to_bool(args['latest'][0])
            if latest == None:
                latest = True
        except:
            latest = False
        if latest:
            # latest report spans two most recent report days
            dates =  [ datetime.now() - timedelta(i) for i in range(0, 14) if (datetime.now() - timedelta(i)).weekday() == rules.report_day() ]
            until = dates[0]
            since = dates[1]
        else:
            try:
                since = datetime.strptime(args['since'][0], '%Y-%m-%d')
            except:
                self.finish_failure("must specify the report start date")
                return
            try:
                until = datetime.strptime(args['until'][0], '%Y-%m-%d')
            except:
                until = datetime.now()
        ranges = {'since' : str(since).split()[0],
                  'until' : str(until).split()[0]}
        # TODO: do the series of database reads and construct the report
        self.finish_success({'entries': [ranges]})

def run_server(ssl_options = util.test_ssl_options, http_port = 80, https_port = 443, html_root = sys.prefix + '/var/jim/html', template_root = sys.prefix + '/var/jim/templates', database = sys.prefix + './jim.db', bootstrap_token = 'deadbeef' ):
    global _http_server
    global _https_server
    global _log
    global _database
    global _bootstrap_token

    # if some bozo calls us with None specified as an argument
    if template_root == None:
        template_root = sys.prefix + '/var/jim/templates'
    if html_root == None:
        html_root = sys.prefix + '/var/jim/html'
    if database == None:
        database = sys.prefix + './jim.db'
    if bootstrap_token == None:
        bootstrap_token = 'deadbeef'

    # list handlers for REST calls here
    handlers = [
        ('/', RootHandler),
        ('/login', LoginHandler),
        ('/login_incorrect', LoginIncorrectHandler),
        ('/logout', LogoutHandler),
        ('/date', DateHandler),
        ('/ladder', LadderHandler),
        ('/roster', RosterHandler),
        ('/add_player', AddPlayerHandler),
        ('/del_player', DelPlayerHandler),
        ('/get_player', GetPlayerHandler),
        ('/update_player', UpdatePlayerHandler),
        ('/add_match', AddMatchHandler),
        ('/del_match', DelMatchHandler),
        ('/get_match', GetMatchHandler),
        ('/update_match', UpdateMatchHandler),
        ('/add_account', AddAccountHandler),
        ('/del_account', DelAccountHandler),
        ('/get_account', GetAccountHandler),
        ('/update_account', UpdateAccountHandler),
        ('/get_report', GetReportHandler),
        ('/main_menu', MainMenuHandler),
        ('/match_form', MatchFormHandler),
        ('/player_form', PlayerFormHandler),
        ('/account_form', AccountFormHandler)
        ]

    _bootstrap_token = bootstrap_token
    _log = util.get_syslog_logger("web")
    _database = database
    handlers.append(('/(.*)', web.StaticFileHandler, {'path': html_root}))
    app = tornado.web.Application(handlers = handlers, template_path = template_root,
                                  cookie_secret = binascii.b2a_hex(os.urandom(32)))
    _log.info("creating servers")
    _http_server = tornado.httpserver.HTTPServer(app, no_keep_alive = False)
    _https_server = tornado.httpserver.HTTPServer(app, no_keep_alive = False, ssl_options = ssl_options)
    _log.info("setting up TCP ports")
    _http_server.listen(http_port)
    _https_server.listen(https_port)
    _log.info("starting server loop")
    tornado.ioloop.IOLoop.instance().start()
    _log.info("server loop exited")
