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
import db
from tornado import web, httpserver
from datetime import datetime
from datetime import timedelta

_http_server = None
_https_server = None
_bounce_server = None
_log = None
_database = None
_news = None
_bootstrap_token = None
_recent_days = 14

class BounceAllHandler(tornado.web.RequestHandler):
    def get(self, path):
        _log.info("bounce handler: {}".format(path))
        _log.info("request to redirect: {}".format(self.request))
        host = self.request.host.split(':')[0]
        self.redirect("https://" + host, permanent = True)

class NoCacheStaticFileHandler(tornado.web.StaticFileHandler):
    def set_extra_headers(self, path):
        self.set_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.set_header("Pragma", "no-cache")
        self.set_header("Expires", "0")

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
            try:
                with open(_news, 'r') as f:
                    news_content = f.read()
            except:
                news_content = None
            if not news_content:
                news_content = "No news today"
            news_content_list = news_content.split('\n')
            self.render('main_menu.html',
                        admin = self.current_user['admin'],
                        news_content_list = news_content_list)
        else:
            self.redirect('/login')

class GenericAdminFormHandler(DynamicBaseHandler):
    def generic_get(self, form_filename, **kwargs):
        self.log_request()
        if self.authorized(admin = True, quiet = True):
            self.render(form_filename, **kwargs)
        else:
            self.redirect('/login')

class PlayerFormRestrictedHandler(DynamicBaseHandler):
    def get(self):
        if self.authorized(admin = True, quiet = True):
            # admin is redirected to its own player form
            self.redirect('/player_form')
        elif self.authorized(quiet = True):
            self.render('player_form_restricted.html')
        else:
            # nobody is logged in, redirect to login form
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

class SeasonFormHandler(GenericAdminFormHandler):
    def get(self):
        self.generic_get('season_form.html')

class TokenFormHandler(GenericAdminFormHandler):
    def get(self):
        self.generic_get('token_form.html')

class NewsFormHandler(GenericAdminFormHandler):
    def get(self):
        try:
            with open(_news, 'r') as f:
                news_content = f.read()
        except:
            news_content = ""
        self.generic_get('news_form.html', news_content=news_content)

    def post(self):
        self.log_request()
        if not self.authorized(admin = True):
            return
        news_content = self.get_argument('news_content')
        try:
            with open(_news, 'w') as f:
                n = f.write(news_content)
                _log.info("wrote {} characters to {}".format(n, _news))
        except:
            _log.error("error writing to file {}".format(_news))
        self.redirect('/main_menu')

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

class InfoBaseHandler(DynamicBaseHandler):
    def expand_match_record(self, match):
        winner_id = match.get('winner_id')
        challenger_id = match.get('challenger_id')
        opponent_id = match.get('opponent_id')
        loser_id = opponent_id if winner_id == challenger_id else challenger_id
        challenger_last_name = match.get('challenger_last_name') + " (c)"
        opponent_last_name = match.get('opponent_last_name')
        winner_last_name = challenger_last_name if winner_id == challenger_id else opponent_last_name
        loser_last_name = opponent_last_name if winner_id == challenger_id else challenger_last_name
        ogames = match.get('ogames').split(',')
        cgames = match.get('cgames').split(',')
        assert len(ogames) == len(cgames)
        score_list = zip(cgames, ogames) if winner_id == challenger_id else zip(ogames, cgames)
        score_str =  "".join([str(x[0]) + "-" + str(x[1]) + " " for x in score_list])[:-1]
        if match.get('retired'):
            notes = "(retired)"
        elif match.get('forfeited'):
            notes = "(forfeited)"
        else:
            notes = ""
        match.update({'winner_last_name' : winner_last_name,
                      'loser_last_name' : loser_last_name,
                      'score' : score_str,
                      'winner_id': winner_id,
                      'loser_id' : loser_id,
                      'notes' : notes})
        return match

class LadderHandler(InfoBaseHandler):
    def get_or_post(self, args):
        _log.debug("ladder: args {}".format(args))
        today = datetime.ctime(datetime.now())
        try:
            matches_since = datetime.strptime(args['matches_since'][0], '%Y-%m-%d')
        except:
            matches_since = datetime.now() - timedelta(_recent_days)
        since_str = str(matches_since).split()[0]
        _log.info("ladder: matches_since: {}".format(since_str))
        a_matches = [self.expand_match_record(r) for r in _database.get_recent_matches('a', since_str)]
        b_matches = [self.expand_match_record(r) for r in _database.get_recent_matches('b', since_str)]
        c_matches = [self.expand_match_record(r) for r in _database.get_recent_matches('c', since_str)]
        _log.debug("ladder: A matches found: {}".format(a_matches))
        _log.debug("ladder: B matches found: {}".format(b_matches))
        _log.debug("ladder: C matches found: {}".format(c_matches))
        _, _, _, season_string = _database.get_season()
        self.render('ladder.html',
                    date_string = today,
                    season_string = season_string,
                    a_ladder = _database.get_ladder('a'),
                    b_ladder = _database.get_ladder('b'),
                    c_ladder = _database.get_ladder('c'),
                    u_ladder = _database.get_ladder('unranked'),
                    a_matches = a_matches,
                    b_matches = b_matches,
                    c_matches = c_matches
                    )

    def get(self):
        self.log_request()
        if self.authorized(quiet = True):
            args = self.get_args()
            self.get_or_post(args)
        else:
            self.redirect('/login')

    def post(self):
        self.log_request()
        if self.authorized(quiet=True):
            month = self.get_argument('since_date_1')
            day = self.get_argument('since_date_2')
            year = self.get_argument('since_date_3')
            self.get_or_post({'matches_since' : ["{}-{}-{}".format(year, month, day)]})
        else:
            self.redirect('/login')

class ProfileHandler(InfoBaseHandler):
    def get_or_post(self, args):
        _log.debug("ladder: args {}".format(args))
        player_ids = args.get('player_id')
        if not player_ids:
            if self.current_user['admin']:
                # admin must specify player id
                self.finish_failure("invalid or missing player id", 400)
                return
            else:
                # for regular player, assume logged-in user if id is not specified
                player_ids = [ str(self.current_user['id']) ]
        if len(player_ids) != 1:
            self.finish_failure("only one player id, please", 400)
            return
        player_id = player_ids[0]
        matched_players = _database.lookup_player({'player_id': player_id, 'active': '1'}, 'and')
        if len(matched_players) == 1:
            player = matched_players[0]
        else:
            self.finish_failure("player lookup failed", 404)
            return
        _log.debug("player: player found: {}".format(player))
        matched_ladder_info = _database.get_ladder(None, player_id)
        if len(matched_ladder_info) == 1:
            ladder_info = matched_ladder_info[0]
        else:
            self.finish_failure("ladder info lookup failed", 404)
            return
        _log.debug("player: ladder info found: {}".format(ladder_info))
        season_id, _, _, _ = _database.get_season()
        ch_matches = _database.lookup_match({ 'season_id': season_id, 'challenger_id': player_id})
        op_matches = _database.lookup_match({ 'season_id': season_id, 'opponent_id' : player_id})
        matches = [self.expand_match_record(r) for r in ch_matches + op_matches]
        _log.debug("player: matches found: {}".format(matches))
        player_e_mail = player.get('email')
        player_ladder = player.get('ladder').upper()
        player_company = player.get('company')
        player_location = player.get('location')
        if not player_location:
            player_location = "unknown"
        player_wlocation = player.get('wlocation')
        if not player_wlocation:
            player_wlocation = "unknown"
        player_note = player.get('note')
        if player_note:
            player_note = " --- " + player_note
        else:
            player_note = ""
        player_phone_numbers = ""
        if player.get('home_phone'):
            player_phone_numbers += player.get('home_phone') + " (h) "
        if player.get('work_phone'):
            player_phone_numbers += player.get('work_phone') + " (w) "
        if player.get('cell_phone'):
            player_phone_numbers += player.get('cell_phone') + " (c) "
        player_name_and_id = player.get('first_name') + " " + player.get('last_name') + " (" + player_id + ")"
        a_ladder_matches = str(ladder_info.get('a_wins')) + " wins, " + str(ladder_info.get('a_losses')) + " losses"
        b_ladder_matches = str(ladder_info.get('b_wins')) + " wins, " + str(ladder_info.get('b_losses')) + " losses"
        c_ladder_matches = str(ladder_info.get('c_wins')) + " wins, " + str(ladder_info.get('c_losses')) + " losses"
        self.render(
            'player_profile.html',
            matches =  matches,
            player_name_and_id = player_name_and_id,
            player_location = player_location,
            player_wlocation = player_wlocation,
            player_note = player_note,
            player_e_mail = player_e_mail,
            player_ladder = player_ladder,
            player_phone_numbers = player_phone_numbers,
            player_company = player_company,
            a_ladder_matches = a_ladder_matches,
            b_ladder_matches = b_ladder_matches,
            c_ladder_matches = c_ladder_matches
        )

    def get(self):
        self.log_request()
        if self.authorized(quiet = True):
            args = self.get_args()
            self.get_or_post(args)
        else:
            self.redirect('/login')

    def post(self):
        self.log_request()
        if self.authorized(quiet=True):
            player_id = self.get_argument('player_id')
            self.get_or_post({'player_id' : [ player_id ]})
        else:
            self.redirect('/login')

class RosterHandler(DynamicBaseHandler):
    def get(self):
        self.log_request()
        if self.authorized(quiet = True):
            _, _, _, season_string = _database.get_season()
            self.render('roster.html',
                        season_string = season_string,
                        date_string = datetime.ctime(datetime.now()),
                        roster = _database.get_roster()
                        )
        else:
            self.redirect('/login')

class ReportHandler(InfoBaseHandler):
    def token_error(self):
        self.finish_failure('invalid or expired token', 401)

    def get(self):
        self.log_request()
        args = self.get_args()
        if args == None:
            self.token_error()
            return
        try:
            token = args['token'][0]
        except:
            token = None
        if not token:
            self.token_error()
            return
        authorized, since_date, expires_date = _database.check_token(token, 'report_and_roster')
        if not authorized or datetime.now() > datetime.strptime(expires_date, '%Y-%m-%d'):
            self.token_error()
            return
        a_ladder = _database.get_ladder('a')
        b_ladder = _database.get_ladder('b')
        c_ladder = _database.get_ladder('c')
        u_ladder = _database.get_ladder('unranked')
        _log.info("report: matches_since: {}".format(since_date))
        a_matches = [self.expand_match_record(r) for r in _database.get_recent_matches('a', since_date)]
        b_matches = [self.expand_match_record(r) for r in _database.get_recent_matches('b', since_date)]
        c_matches = [self.expand_match_record(r) for r in _database.get_recent_matches('c', since_date)]
        _log.debug("report: A matches found: {}".format(a_matches))
        _log.debug("report: B matches found: {}".format(b_matches))
        _log.debug("report: C matches found: {}".format(c_matches))
        _, _, _, season_string = _database.get_season()
        today = datetime.ctime(datetime.now())
        roster = _database.get_roster()
        self.render('report.html', date_string = today,
                    a_matches = a_matches,
                    b_matches = b_matches,
                    c_matches = c_matches,
                    a_ladder = a_ladder,
                    b_ladder = b_ladder,
                    c_ladder = c_ladder,
                    u_ladder = u_ladder,
                    roster = roster,
                    season_string = season_string)


def format_phone_number(phone_number):
    p_dd = ''.join(c for c in phone_number if c.isdigit())
    if (len(p_dd)==10):
        ret_phone_number = '-'.join([p_dd[0:3],p_dd[3:6],p_dd[6:10]])
    else: 
        ret_phone_number = None
    return ret_phone_number
    



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

        if (home_phone != None):
            p_dd = ''.join(c for c in home_phone if c.isdigit())
            if (len(p_dd)==10):
                home_phone = '-'.join([p_dd[0:3],p_dd[3:6],p_dd[6:10]])
            else: 
                home_phone = None
                self.finish_failure("A 10-digit home phone number is required.")
                return None
            
        try:
            cell_phone = args['cell_phone'][0]
        except:
            cell_phone = None
        if (cell_phone != None):
            cell_phone = format_phone_number(cell_phone)
            if (cell_phone == None):
               self.finish_failure("A 10-digit cell phone number is required.")
               return None    
        try:
            work_phone = args['work_phone'][0]
        except:
            work_phone = None
        if (work_phone != None):
            work_phone = format_phone_number(work_phone)
            if (work_phone == None):
               self.finish_failure("A 10-digit work phone number is required.")
               return None    
            
        if add_flag and not (home_phone or cell_phone or work_phone):
            self.finish_failure("At least one 10-digit phone number is required.")
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
        try:
            location = args['location'][0]
        except:
            location = None
        try:
            wlocation = args['wlocation'][0]
        except:
            wlocation = None
        try:
            note = args['note'][0]
        except:
            note = None
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
        try:
            tournament_qualified_override_str = args['tournament_qualified_override'][0]
        except:
            if add_flag:
                tournament_qualified_override_str = '0'
            else:
                tournament_qualified_override_str = None
        if tournament_qualified_override_str:
            try:
                tournament_qualified_override = int(tournament_qualified_override_str)
            except:
                self.finish_failure("tournament flag must be an integer")
                return None
            if tournament_qualified_override not in [-1, 0, 1]:
                self.finish_failure("tournament flag must be -1, 0, or 1")
                return None
        else:
            if add_flag:
                tournament_qualified_override = 0
            else:
                tournament_qualified_override = None
        player = { 'username': username,
                   'password': password,
                   'first_name': first_name,
                   'last_name' : last_name,
                   'email' : email,
                   'home_phone' : home_phone,
                   'work_phone' : work_phone,
                   'cell_phone' : cell_phone,
                   'company': company,
                   'location': location,
                   'wlocation' : wlocation,
                   'note': note,
                   'ladder': ladder,
                   'initial_points': initial_points,
                   'active': active,
                   'tournament_qualified_override' : tournament_qualified_override}
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

    def purge_non_privileged_fields(self, player):
        if player.get('ladder') != None:
            player.pop('ladder')
        if player.get('initial_points') != None:
            player.pop('initial_points')
        if player.get('active') != None:
            player.pop('active')
        if player.get('tournament_qualified_override') != None:
            player.pop('tournament_qualified_override')

    def update_database(self, player, player_id):
        player_id, err = _database.update_player(player, player_id)
        if player_id > 0:
            player.update({'player_id': player_id})
            return True, err
        else:
            return False, err

    def get_or_post(self, password):
        self.log_request()
        if self.authorized(admin = False, quiet = True):
            if self.authorized(admin = True, quiet = True):
                _log.info("update_player: admin user {}".format(self.current_user['id']))
                is_admin = True;
            else:
                _log.info("update_player: regular user {}".format(self.current_user['id']))
                is_admin = False;
        else:
            self.finish_failure('not authorized')
            return
        args = self.get_args()
        if args == None:
            return
        player = self.parse_args(args, False, password)
        if player == None:
            return
        if is_admin:
            try:
                player_id = int(args['player_id'][0])
            except:
                self.finish_failure("missing or invalid player ID")
                return
            updated_player = player
        else:
            # force logged-in user ID if not admin
            player_id = self.current_user['id']
            self.purge_non_privileged_fields(player)
            _log.info("purged player record: {}".format(player))
            existing_players = _database.lookup_player({'player_id':player_id}, 'and')
            assert(len(existing_players) == 1)
            existing_player = existing_players[0]
            existing_player.update(player)
            updated_player = existing_player
        r, err = self.update_database(updated_player, player_id)
        if r:
            self.finish_success(updated_player)
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
        if player_id != None:
            if player_id < 0:
                # negative player_id means currently logged-in player
                if not self.current_user['admin']:
                    player_id = self.current_user['id']
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
        try:
            season_id = int(args['season_id'][0])
        except:
            season_id, _, _, _ = _database.get_season()
        keys =  util.purge_null_fields({ 'challenger_id': challenger_id,
                                         'opponent_id': opponent_id,
                                         'winner_id': winner_id,
                                         'ladder' : ladder,
                                         'season_id' : season_id,
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

class NewSeasonHandler(DynamicBaseHandler):
    def get_or_post(self, args):
        self.log_request()
        if not self.authorized(admin = True):
            return
        try:
            title = args['title'][0]
        except:
            title = None
        if not title:
            title = "season created on {}".format(str(datetime.now()))
        try:
            start_date = datetime.strptime(args['start_date'][0], '%Y-%m-%d')
            start_date = str(start_date).split()[0]
        except:
            start_date = None
        try:
            end_date = datetime.strptime(args['end_date'][0], '%Y-%m-%d')
            end_date = str(end_date).split()[0]
        except:
            end_date = None
        _log.info("new season requested: {}-{}".format(start_date, end_date))
        season_id, err = _database.new_season(start_date, end_date, title)
        if season_id:
            self.finish_success({'season_id' : season_id})
        else:
            self.finish_failure(err)

    def get(self):
        args = self.get_args()
        if args == None:
            return
        self.get_or_post(args)

    def post(self):
        start_date = self.get_argument('start_date')
        end_date = self.get_argument('end_date')
        args = {'start_date' : [start_date], 'end_date' : [end_date]}
        self.get_or_post(args)

class NewTokenHandler(DynamicBaseHandler):
    def get_or_post(self, args):
        self.log_request()
        if not self.authorized(admin = True):
            return
        try:
            token_type = args['token_type'][0]
        except:
            token_type = None
        if not type:
            token_type = 'report_and_roster'
        # if we need other token types, list them here
        if token_type not in ['report_and_roster']:
            self.finish_failure("invalid token type")
            return
        try:
            since_date = datetime.strptime(args['since_date'][0], '%Y-%m-%d')
            since_date = str(since_date).split()[0]
        except:
            self.finish_failure('missing or invalid since-date')
            return
        try:
            expires_date = datetime.strptime(args['expires_date'][0], '%Y-%m-%d')
            expires_date = str(expires_date).split()[0]
        except:
            self.finish_failure('missing or invalid expiration date')
            return
        _log.info("new token requested: since {}, type is {}, expires on {}".format(since_date, expires_date, token_type))
        token, token_id, err = _database.new_token(token_type, since_date, expires_date)
        if token and token_id:
            self.finish_success({'token' : token, 'token_id': token_id})
        else:
            self.finish_failure(err)

    def get(self):
        args = self.get_args()
        if args == None:
            return
        self.get_or_post(args)

    def post(self):
        start_date = self.get_argument('start_date')
        end_date = self.get_argument('end_date')
        args = {'start_date' : [start_date], 'end_date' : [end_date]}
        self.get_or_post(args)

def run_server(ssl_options = util.test_ssl_options, http_port = 80, https_port = 443, bounce_port = 8000, html_root = sys.prefix + '/var/jim/html', template_root = sys.prefix + '/var/jim/templates', database = sys.prefix + './jim.db', news = sys.prefix + './news.txt', bootstrap_token = 'deadbeef' ):
    global _http_server
    global _https_server
    global _bounce_server
    global _log
    global _database
    global _news
    global _bootstrap_token

    # if some bozo calls us with None specified as an argument
    if template_root == None:
        template_root = sys.prefix + '/var/jim/templates'
    if html_root == None:
        html_root = sys.prefix + '/var/jim/html'
    if database == None:
        database =  db.Database('./jim.db')
    if news == None:
        news = './news.txt'
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
        ('/report', ReportHandler),
        ('/profile', ProfileHandler),
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
        ('/new_season', NewSeasonHandler),
        ('/new_token', NewTokenHandler),
        ('/main_menu', MainMenuHandler),
        ('/match_form', MatchFormHandler),
        ('/player_form', PlayerFormHandler),
        ('/player_form_restricted', PlayerFormRestrictedHandler),
        ('/season_form', SeasonFormHandler),
        ('/token_form', TokenFormHandler),
        ('/news_form', NewsFormHandler),
        ('/account_form', AccountFormHandler)
        ]

    _bootstrap_token = bootstrap_token
    _log = util.get_syslog_logger("web")
    _database = database
    _news = news
    _log.info("news file: {}".format(_news))
    handlers.append(('/(.*)', NoCacheStaticFileHandler, {'path': html_root}))
    app = tornado.web.Application(handlers = handlers, template_path = template_root,
                                  cookie_secret = binascii.b2a_hex(os.urandom(32)))
    app_bounce = tornado.web.Application(handlers = [('/(.*)', BounceAllHandler)])
    _log.info("creating servers")
    _http_server = tornado.httpserver.HTTPServer(app, no_keep_alive = False)
    _https_server = tornado.httpserver.HTTPServer(app, no_keep_alive = False, ssl_options = ssl_options)
    _bounce_server = tornado.httpserver.HTTPServer(app_bounce)
    _log.info("setting up TCP ports: http={}, https={}, bounce={}".format(http_port, https_port, bounce_port))
    _http_server.listen(http_port)
    _https_server.listen(https_port)
    _bounce_server.listen(bounce_port)
    _log.info("starting server loop")
    tornado.ioloop.IOLoop.instance().start()
    _log.info("server loop exited")
