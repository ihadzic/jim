#!/usr/bin/env python2

import tornado
import logging
import datetime
import os
import sys
import binascii
import rules
import util
from tornado import web, httpserver
from datetime import datetime

_http_server = None
_https_server = None
_template_root = sys.prefix + '/var/jim/templates'
_log = None
# This is default (test-only) certificate located in ./certs directory.
# default certificate is self-signed, so we don't have 'ca_cert' field
# in the dictionary. Normally, we need one to point to the 'CA'
_test_ssl_options = { 'certfile' : sys.prefix + '/var/jim/certs/cert.pem', 'keyfile': sys.prefix + '/var/jim/certs/key.pem' }

def get_player_id():
    return 42

class DynamicBaseHandler(tornado.web.RequestHandler):
    def finish_failure(self, err = None):
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

    def get_player_args(self, args, mandatory):
        try:
            first_name = args['first_name'][0]
        except:
            if mandatory:
                self.finish_failure("player fist name missing")
                return None
            else:
                first_name = None
        try:
            last_name = args['last_name'][0]
        except:
            if mandatory:
                self.finish_failure("player last name missing")
                return None
            else:
                last_name = None
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
        if mandatory and not (home_phone or cell_phone or work_phone):
            self.finish_failure("at least one phone number is required")
            return None
        try:
            email = args['email'][0]
        except:
            if mandatory:
                self.finish_failure("e-mail is required")
                return None
            else:
                email = None
        try:
            ladder = args['ladder'][0].lower()
        except:
            if mandatory:
                ladder = 'unranked'
            else:
                ladder = None
        try:
            company = args['company'][0]
        except:
            if mandatory:
                self.finish_failure("company name is required")
                return None
            else:
                company = None
        if not ladder in [ 'a', 'b', 'c', 'unranked', 'beginner' ]:
            self.finish_failure("invalid ladder category")
            return None
        try:
            initial_points_str = args['initial_points'][0]
        except:
            if mandatory:
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
            initial_points = None
        player = {'name': first_name + ' ' + last_name,
                  'email' : email,
                  'home_phone' : home_phone,
                  'work_phone' : work_phone,
                  'cell_phone' : cell_phone,
                  'company': company,
                  'ladder': ladder,
                  'initial_points': initial_points}
        if mandatory:
            return player
        else:
            return util.purge_null_fields(player)

    def initialize(self):
        self.set_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.set_header("Pragma", "no-cache")
        self.set_header("Expires", "0")

    def get_current_user(self):
        return self.get_secure_cookie('user')

class RootHandler(tornado.web.RequestHandler):
    def get(self):
        self.redirect('/login', permanent = True)

class LoginHandler(DynamicBaseHandler):
    def get(self):
        if self.current_user:
            self.redirect('/date')
        else:
            self.render('login.html')

    def post(self):
        # TODO: check the password here
        self.set_secure_cookie('user', self.get_argument('name'))
        self.redirect('/date')

class LogoutHandler(DynamicBaseHandler):
    def get(self):
        self.clear_cookie('user')
        self.redirect('/login')

class DateHandler(DynamicBaseHandler):
    def get(self):
        if self.current_user:
            name = tornado.escape.xhtml_escape(self.current_user)
        else:
            name = 'nobody'
        self.render('date.html',
                    date_string = str(datetime.datetime.now()),
                    user_string = name)

class AddPlayerHandler(DynamicBaseHandler):
    def get(self):
        args = self.get_args()
        if args == None:
            return
        player = self.get_player_args(args, True)
        if player == None:
            return
        # REVISIT: player ID comes from the database after adding the
        #          new record, for now we have this placeholder function
        #          that will go away after we add the real DB backend
        player_id = get_player_id()
        player.update({'player_id': player_id})
        self.finish_success(player)

class UpdatePlayerHandler(DynamicBaseHandler):
    def get(self):
        args = self.get_args()
        if args == None:
            return
        player = self.get_player_args(args, False)
        if player == None:
            return
        try:
            player_id = int(args['id'][0])
        except:
            self.finish_failure("missing or invalid player ID")
            return
        player.update({'id': player_id})
        # REVISIT: update player record in the database
        self.finish_success(player)

class MatchResultHandler(DynamicBaseHandler):
    def get(self):
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
        # TODO: do the database transaction
        self.finish_success({'opponent_id': opponent_id,
                             'challenger_id': challenger_id,
                             'winner_id': winner_id,
                             'cgames': cgames,
                             'ogames': ogames,
                             'cpoints': cpoints,
                             'opoints': opoints,
                             'retired': retired,
                             'forfeited' : forfeited,
                             'date': str(date).split()[0],
                             'tournament': tournament})

def run_server(ssl_options = _test_ssl_options, http_port = 80, https_port = 443, html_root = sys.prefix + '/var/jim/html', template_root = sys.prefix + '/var/jim/templates'):
    global _http_server
    global _https_server
    global _log

    # if some bozo calls us with None specified as an argument
    if template_root == None:
        template_root = sys.prefix + '/var/jim/templates'
    if html_root == None:
        html_root = sys.prefix + '/var/jim/html'

    # list handlers for REST calls here
    handlers = [
        ('/', RootHandler),
        ('/login', LoginHandler),
        ('/logout', LogoutHandler),
        ('/date', DateHandler),
        ('/add_player', AddPlayerHandler),
        ('/update_player', UpdatePlayerHandler),
        ('/match_result', MatchResultHandler)
        ]

    _log = logging.getLogger("web")
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
