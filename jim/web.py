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
_player_reports_matches = None
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
        _database.kick_if_needed()
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

class MainMenuHandler(InfoBaseHandler):
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
            pending_matches = [];
            if _player_reports_matches and not self.current_user['admin']:
                player_ids = [ str(self.current_user['id']) ]
                player_id = player_ids[0]
                season_id, _, _, _, _, _ = _database.get_season()
                ch_matches = _database.lookup_match({ 'season_id': season_id, 'challenger_id': player_id, 'disputed': False, 'pending': True})
                op_matches = _database.lookup_match({ 'season_id': season_id, 'opponent_id' : player_id, 'disputed': False, 'pending' : True})
                pending_matches = [self.expand_match_record(r) for r in ch_matches + op_matches]
                pending_matches.sort(lambda x, y: util.cmp_date_field(x, y))
                _log.debug("main_menu: pending matches found: {}".format(pending_matches))
            self.render('main_menu.html',
                        admin = self.current_user['admin'],
                        news_content_list = news_content_list,
                        player_reports_matches = _player_reports_matches,
                        pending_matches = pending_matches)
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
            self.render('player_form.html',
                        admin = self.current_user['admin'],
                        player_reports_matches = _player_reports_matches)
        else:
            # nobody is logged in, redirect to login form
            self.redirect('/login')

class AccountFormHandler(GenericAdminFormHandler):
    def get(self):
        self.generic_get('account_form.html',
                         admin = self.current_user['admin'],
                         player_reports_matches = _player_reports_matches)

class PlayerFormHandler(GenericAdminFormHandler):
    def get(self):
        self.generic_get('player_form.html',
                        admin = self.current_user['admin'],
                        player_reports_matches = _player_reports_matches)

class MatchFormHandler(GenericAdminFormHandler):
    def get(self):
        self.generic_get('match_form.html',
                         admin = self.current_user['admin'],
                         player_reports_matches = _player_reports_matches)

class MatchFormRestrictedHandler(DynamicBaseHandler):
    def get(self):
        if self.authorized(admin = True, quiet = True):
            # admin is redirected to its own player form
            self.redirect('/match_form')
        elif self.authorized(quiet = True):
            player_id = self.current_user['id']
            matched_players = _database.lookup_player({'player_id': player_id}, 'and')
            assert(len(matched_players) == 1)
            player_last_name = matched_players[0].get('last_name')
            self.render('match_form.html',
                        admin = self.current_user['admin'],
                        player_reports_matches = _player_reports_matches,
                        player_1_last_name = player_last_name,
                        player_1_id = player_id)
        else:
            # nobody is logged in, redirect to login form
            self.redirect('/login')

class SeasonFormHandler(GenericAdminFormHandler):
    def get(self):
        self.generic_get('season_form.html',
                         admin = self.current_user['admin'],
                         player_reports_matches = _player_reports_matches)

class TournamentFormHandler(GenericAdminFormHandler):
    def get(self):
        min_matches, min_opponents, start_date = _database.get_tournament_parameters()
        # if tournament date is None, default to season-end date
        if not start_date:
            _, _ , start_date, _, _, _ = _database.get_season()
        start_date_3, start_date_1, start_date_2 = tuple(start_date.split('-'))
        qualified_players = [ p for p in _database.get_roster() if p.get('tournament_qualified') ]
        _log.info("qualified players: {}".format(qualified_players))
        self.generic_get('tournament_form.html',
                         admin = self.current_user['admin'],
                         player_reports_matches = _player_reports_matches,
                         start_date_1 = start_date_1,
                         start_date_2 = start_date_2,
                         start_date_3 = start_date_3,
                         min_matches = min_matches,
                         min_opponents = min_opponents,
                         qualified_players = qualified_players)

class NewsFormHandler(GenericAdminFormHandler):
    def get(self):
        try:
            with open(_news, 'r') as f:
                news_content = f.read()
        except:
            news_content = ""
        self.generic_get('news_form.html',
                         admin = self.current_user['admin'],
                         player_reports_matches = _player_reports_matches,
                         news_content=news_content)

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
        _, _, _, season_string, _, _ = _database.get_season()
        self.render('ladder.html',
                    admin = self.current_user['admin'],
                    player_reports_matches = _player_reports_matches,
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
        _log.debug("profile: args {}".format(args))
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
            matched_inactive_players = _database.lookup_player({'player_id': player_id, 'active': '0'}, 'and')
            if len(matched_inactive_players) == 1:
                self.render('player_profile_inactive.html',
                            admin = self.current_user['admin'],
                            player_reports_matches = _player_reports_matches)
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
        season_id, _, _, _, _, _ = _database.get_season()
        ch_matches = _database.lookup_match({ 'season_id': season_id, 'challenger_id': player_id, 'disputed': False, 'pending': False})
        op_matches = _database.lookup_match({ 'season_id': season_id, 'opponent_id' : player_id, 'disputed': False, 'pending' : False})
        matches = [self.expand_match_record(r) for r in ch_matches + op_matches]
        matches.sort(lambda x, y: util.cmp_date_field(x, y))
        _log.debug("player: matches found: {}".format(matches))
        ch_matches = _database.lookup_match({ 'season_id': season_id, 'challenger_id': player_id, 'disputed': False, 'pending': True})
        op_matches = _database.lookup_match({ 'season_id': season_id, 'opponent_id' : player_id, 'disputed': False, 'pending' : True})
        pending_matches = [self.expand_match_record(r) for r in ch_matches + op_matches]
        pending_matches.sort(lambda x, y: util.cmp_date_field(x, y))
        _log.debug("player: pending matches found: {}".format(pending_matches))
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
            admin = self.current_user['admin'],
            player_reports_matches = _player_reports_matches,
            matches =  matches,
            pending_matches =  pending_matches,
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
            _, _, _, season_string, _, _ = _database.get_season()
            self.render('roster.html',
                        admin = self.current_user['admin'],
                        player_reports_matches = _player_reports_matches,
                        season_string = season_string,
                        date_string = datetime.ctime(datetime.now()),
                        roster = _database.get_roster()
                        )
        else:
            self.redirect('/login')

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
                self.finish_failure("home phone number format invalid")
                return None
        try:
            cell_phone = args['cell_phone'][0]
        except:
            cell_phone = None
        if (cell_phone != None):
            cell_phone = format_phone_number(cell_phone)
            if (cell_phone == None):
               self.finish_failure("cell phone number format invalid")
               return None
        try:
            work_phone = args['work_phone'][0]
        except:
            work_phone = None
        if (work_phone != None):
            work_phone = format_phone_number(work_phone)
            if (work_phone == None):
               self.finish_failure("work phone number format invalid")
               return None

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
            self.finish_failure("missing args", 400)
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
            self.finish_failure("missing args", 400)
            return
        try:
            player_id = int(args['player_id'][0])
        except:
            self.finish_failure("missing or invalid player ID")
            return
        ch_matches = _database.lookup_match({ 'challenger_id': player_id})
        op_matches = _database.lookup_match({ 'opponent_id' : player_id})
        if ch_matches + op_matches:
            self.finish_failure("cannot delete players which has played matches in the past")
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
        new_ladder = player.get('ladder')
        if _database.ladder_changed(player_id, new_ladder):
            _, season_start_date, season_end_date, _, _, _  = _database.get_season()
            ssd = datetime.strptime(season_start_date, '%Y-%m-%d')
            sed = datetime.strptime(season_end_date, '%Y-%m-%d')
            today = datetime.now()
            date = datetime(today.year, today.month, today.day)
            # mid season administrative changes are a problem
            # because if the user is moved up and down, we can
            # run into the cases when promotion dates become invalid.
            #
            # For example, if we move the user from C ladder to A ladder
            # on date Da followed by moving the user back to B ladder
            # on date Db where Db > Da, the algorithm that determines which
            # ladder was the user in on any date breaks. There is no
            # way to tell that user was ever in ladder A.
            #
            # Restricting administrative moves to off-season solves the problem
            if ssd <= date <= sed:
                return False, "administrative ladder change not allowed in mid-season"
            if new_ladder == 'a':
                player.update({'a_promotion' : None})
                player.update({'b_promotion' : None})
                player.update({'c_promotion' : None})
            elif new_ladder == 'b':
                player.update({'a_promotion' : None})
                player.update({'b_promotion' : None})
                player.update({'c_promotion' : None})
            elif new_ladder == 'c':
                player.update({'a_promotion' : None})
                player.update({'b_promotion' : None})
                player.update({'c_promotion' : None})
            else:
                player.update({'a_promotion' : None})
                player.update({'b_promotion' : None})
                player.update({'c_promotion' : None})
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
            self.finish_failure("missing args", 400)
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
            self.finish_failure("missing args", 400)
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

class ValidateMatchHandler(DynamicBaseHandler):
    def get(self):
        self.log_request()
        if not self.authorized(admin = True):
            return
        args = self.get_args()
        if args == None:
            self.finish_failure("missing args", 400)
            return
        try:
            match_id = int(args['match_id'][0])
        except:
            self.finish_failure("missing or invalid match ID")
            return
        try:
            action = args['action'][0]
        except:
            action = 'approve'
        matches = _database.lookup_match({'match_id': match_id})
        if not matches:
            self.finish_failure("match not found")
            return
        _log.debug("got {} matches".format(len(matches)))
        assert(len(matches) == 1)
        match = matches[0]
        if action == 'approve':
            if match.get('pending'):
                if not match.get('disputed'):
                    _database.approve_match(match)
                    self.finish_success({'match': match, 'action': action})
                else:
                    self.finish_failure("cannot approve disputed matches")
            else:
                self.finish_failure("match already approved")
        elif action == 'dispute':
            if not match.get('disputed'):
                if match.get('pending'):
                    _database.dispute_match(match)
                    self.finish_success({'match': match, 'action': action})
                else:
                    self.finish_failure("cannot dispute approved matches")
            else:
                self.finish_failure("match already disputed")
        else:
            self.finish_failure("invalid action")
        return

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
        if self.authorized(admin = True, quiet = True):
            is_admin = True
        elif self.authorized(quiet = True):
            is_admin = False
            if not _player_reports_matches:
                self.finish_failure("Reporting user's mamtches coming soon. Please use E-mail until then.")
                return
        else:
            self.finish_failure("not logged in", 401)
            return
        args = self.get_args()
        if args == None:
            self.finish_failure("missing args", 400)
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
            pending = util.str_to_bool(args['pending'][0])
            if pending == None:
                self.finish_failure("pending-flag must be boolean")
                return
        except:
            pending = False
        if not pending and not is_admin:
            self.finish_failure("regular users can only submit pending matches")
            return
        try:
            disputed = util.str_to_bool(args['disputed'][0])
            if disputed == None:
                self.finish_failure("disputed-flag must be boolean")
                return
        except:
            disputed = False
        if disputed and not is_admin:
            # submitting matches that are disputed to begin
            # with doesn't make sense, but admin can still
            # do it for test purpose
            self.finish_failure("new mactch should not be disputed to begin with")
            return
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
                 'tournament': tournament,
                 'pending': pending,
                 'disputed': disputed
        }
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
            self.finish_failure("missing args", 400)
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

class GetMatchHandler(InfoBaseHandler):
    def get(self):
        self.log_request()
        if not self.authorized():
            return
        args = self.get_args()
        if args == None:
            self.finish_failure("missing args", 400)
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
        try:
            pending = util.str_to_bool(args['pending'][0])
        except:
            pending = None
        try:
            disputed = util.str_to_bool(args['disputed'][0])
        except:
            disputed = None
        if since and date:
            self.finish_failure("cannot have both since and date parameters")
            return
        try:
            season_id = int(args['season_id'][0])
        except:
            season_id, _, _, _, _, _ = _database.get_season()
        try:
            sort_by_date = args['sort_by_date'][0]
        except:
            sort_by_date = None
        keys =  util.purge_null_fields({ 'challenger_id': challenger_id,
                                         'opponent_id': opponent_id,
                                         'winner_id': winner_id,
                                         'ladder' : ladder,
                                         'season_id' : season_id,
                                         'date': str(date).split()[0] if date else None,
                                         'since': str(since).split()[0] if since else None,
                                         'pending': pending,
                                         'disputed': disputed})
        _log.info("keys = {}".format(keys))
        ms = _database.lookup_match(keys)
        matches = [self.expand_match_record(m) for m in ms]
        if sort_by_date:
            if sort_by_date == 'asc':
                matches.sort(lambda x, y: util.cmp_date_field(x, y, -1))
            elif sort_by_date == 'desc':
                matches.sort(lambda x, y: util.cmp_date_field(x, y))
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
            self.finish_failure("missing args", 400)
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
            self.finish_failure("missing args", 400)
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
            self.finish_failure("missing args", 400)
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
            self.finish_failure("missing args", 400)
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

class UpdateTournamentHandler(DynamicBaseHandler):
    def get_or_post(self, args):
        self.log_request()
        if not self.authorized(admin = True, quiet = True):
            self.redirect('/login')
        try:
            start_date = datetime.strptime(args['start_date'][0], '%Y-%m-%d')
            start_date = str(start_date).split()[0]
        except:
            start_date = None
        try:
            min_matches = int(args['min_matches'][0])
        except:
            min_matches = None
        try:
            min_opponents = int(args['min_opponents'][0])
        except:
            min_opponents = None
        _log.info("new tournament parameters: {} {}/{}".format(start_date, min_matches, min_opponents))
        if start_date != None and min_matches != None and min_opponents != None:
            _database.set_tournament_parameters(start_date, min_matches, min_opponents)
        self.redirect('/tournament_form')

    def get(self):
        args = self.get_args()
        if args == None:
            self.finish_failure("missing args", 400)
            return
        self.get_or_post(args)

    def post(self):
        start_date = self.get_argument('start_date_3') + '-' + self.get_argument('start_date_1') + '-' + self.get_argument('start_date_2')
        min_matches = self.get_argument('min_matches')
        min_opponents = self.get_argument('min_opponents')
        args = {'start_date' : [start_date], 'min_matches' : [min_matches], 'min_opponents' : [min_opponents]}
        self.get_or_post(args)

class KickSeasonHandler(DynamicBaseHandler):
    def get(self):
        self.log_request()
        args = self.get_args()
        if self.current_user['id']:
            if not self.current_user['admin']:
                self.finish_failure("test-only call for admins")
        else:
            self.finish_failure("test-only call for admins")
        dbs = args.get('db')
        if dbs:
            db = dbs[0]
        else:
            db = None
        ladders = args.get('ladder')
        if not ladders:
            ladders = ['a', 'b', 'c']
        season_tuple = _database.get_season()
        previous_season_ladder, current_season_ladder, init_points = _database.kick_season(season_tuple[4], ladders, db)
        self.finish_success({'args': args, 'season': season_tuple, 'previous_season_ladder': previous_season_ladder, 'current_season_ladder': current_season_ladder, 'init_points': init_points})

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
            sd = datetime.strptime(args['start_date'][0], '%Y-%m-%d')
            start_date = str(sd).split()[0]
        except:
            start_date = None
        try:
            ed = datetime.strptime(args['end_date'][0], '%Y-%m-%d')
            end_date = str(ed).split()[0]
        except:
            end_date = None
        try:
            td = datetime.strptime(args['tournament_date'][0], '%Y-%m-%d')
            tournament_date = str(td).split()[0]
        except:
            tournament_date = None
        _log.info("new season requested: {} --- {} (tournament: {})".format(start_date, end_date, tournament_date))
        if (start_date and not end_date) or (not start_date and end_date):
            self.finish_failure("start and end date should either be both set or both blank")
            return
        if start_date and end_date:
            if sd > ed:
                self.finish_failure("start date cannnot be after end date")
                return
        if tournament_date:
            if td < sd or td > ed:
                self.finish_failure("tournament date must be within the season")
                return
        _log.info("new season database transaction --- start")
        season_id, err = _database.new_season(start_date, end_date, title, tournament_date)
        _log.info("new season database transaction --- end")
        if season_id:
            _log.info("new season created id is {}".format(season_id))
            self.finish_success({'season_id' : season_id})
        else:
            _log.info("new season creation failure")
            self.finish_failure(err)

    def get(self):
        args = self.get_args()
        if args == None:
            self.finish_failure("missing args", 400)
            return
        self.get_or_post(args)

    def post(self):
        start_date = self.get_argument('start_date')
        end_date = self.get_argument('end_date')
        title = self.get_argument('title')
        args = {'start_date' : [start_date], 'end_date' : [end_date], 'title' : [title]}
        self.get_or_post(args)

class PlayerLadderOnDateHandler(DynamicBaseHandler):
    def get(self):
        if not self.authorized(admin = True):
            return
        args = self.get_args()
        if args == None:
            self.finish_failure("missing args", 400)
            return
        try:
            date = datetime.strptime(args['date'][0], "%Y-%m-%d")
        except:
            today = datetime.now()
            date = datetime(today.year, today.month, today.day)
        try:
            player_id = int(args['player_id'][0])
        except:
            self.finish_failure('missing or invalid player_id')
            return
        _log.info("checking player {} ladder on date {}".format(player_id, date))
        ladder = _database.player_ladder_for_date(player_id, date)
        self.finish_success({'player_id': player_id, 'date': str(date).split()[0],
                             'ladder': ladder})

def run_server(ssl_options = util.test_ssl_options, http_port = 80, https_port = 443, bounce_port = 8000, html_root = sys.prefix + '/var/jim/html', template_root = sys.prefix + '/var/jim/templates', database = sys.prefix + './jim.db', news = sys.prefix + './news.txt', bootstrap_token = 'deadbeef', player_reports_matches = False, autoreload = False):
    global _http_server
    global _https_server
    global _bounce_server
    global _log
    global _database
    global _news
    global _bootstrap_token
    global _player_reports_matches

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
    if player_reports_matches == None:
        player_reports_matches = False
    if autoreload == None:
        autoreload = False

    # list handlers for REST calls here
    handlers = [
        ('/', RootHandler),
        ('/login', LoginHandler),
        ('/login_incorrect', LoginIncorrectHandler),
        ('/logout', LogoutHandler),
        ('/date', DateHandler),
        ('/ladder', LadderHandler),
        ('/roster', RosterHandler),
        ('/profile', ProfileHandler),
        ('/add_player', AddPlayerHandler),
        ('/del_player', DelPlayerHandler),
        ('/get_player', GetPlayerHandler),
        ('/player_ladder_on_date', PlayerLadderOnDateHandler),
        ('/update_player', UpdatePlayerHandler),
        ('/add_match', AddMatchHandler),
        ('/del_match', DelMatchHandler),
        ('/get_match', GetMatchHandler),
        ('/validate_match', ValidateMatchHandler),
        ('/update_match', UpdateMatchHandler),
        ('/add_account', AddAccountHandler),
        ('/del_account', DelAccountHandler),
        ('/get_account', GetAccountHandler),
        ('/update_account', UpdateAccountHandler),
        ('/update_tournament', UpdateTournamentHandler),
        ('/new_season', NewSeasonHandler),
        ('/kick_season', KickSeasonHandler),
        ('/main_menu', MainMenuHandler),
        ('/match_form', MatchFormHandler),
        ('/match_form_restricted', MatchFormRestrictedHandler),
        ('/player_form', PlayerFormHandler),
        ('/player_form_restricted', PlayerFormRestrictedHandler),
        ('/tournament_form', TournamentFormHandler),
        ('/season_form', SeasonFormHandler),
        ('/news_form', NewsFormHandler),
        ('/account_form', AccountFormHandler)
        ]

    _bootstrap_token = bootstrap_token
    _log = util.get_syslog_logger("web")
    _database = database
    _news = news
    _player_reports_matches = player_reports_matches
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
    if autoreload:
        from tornado import autoreload
        tornado.autoreload.start();
        for dir, _, files in os.walk(template_root):
            [tornado.autoreload.watch(dir + '/' + f) for f in files if not f.startswith('.')]
        for dir, _, files in os.walk(html_root):
            [tornado.autoreload.watch(dir + '/' + f) for f in files if not f.startswith('.')]
    tornado.ioloop.IOLoop.instance().start()
    _log.info("server loop exited")
