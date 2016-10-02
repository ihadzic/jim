#!/usr/bin/env python2
#
# Copyright (c) 2016, Ilija Hadzic <ilijahadzic@gmail.com>
#
# MIT License, see LICENSE.txt for details

import util
import rules
import sqlite3
import string
import os
import bcrypt
import random
from datetime import datetime

# each time the schema is changed, add a new entry here
# the last transaction must be adding to revisions table
# this will advance the schema version, next time the
# program starts the transactions in this table will
# be played from the current revision number to the end
# of the table
_schema = [

    [ 'CREATE TABLE revisions (id INTEGER PRIMARY KEY NOT NULL, date DATE, comment TEXT);',
      'INSERT INTO revisions (date, comment) VALUES (date("now"), "empty database");' ],

    [ 'CREATE TABLE players (id INTEGER PRIMARY KEY  NOT NULL, last_name TEXT, first_name TEXT, username TEXT UNIQUE, password_hash TEXT, password_seed TEXT, cell_phone TEXT, home_phone TEXT, work_phone TEXT, email TEXT, company TEXT, ladder TEXT, active BOOL NOT NULL  DEFAULT false, points INTEGER NOT NULL  DEFAULT 0);',
      'INSERT INTO revisions (date, comment) VALUES (date("now"), "add players table");'],

    [ 'ALTER TABLE players ADD COLUMN initial_points INTEGER NOT NULL DEFAULT 0;',
      'UPDATE players SET initial_points = points;',
      'INSERT INTO revisions (date, comment) VALUES (date("now"), "add init_points column");'],

    [ 'ALTER TABLE players ADD COLUMN wins INTEGER NOT NULL DEFAULT 0;',
      'ALTER TABLE players ADD COLUMN losses INTEGER NOT NULL DEFAULT 0;',
      'ALTER TABLE players ADD COLUMN ladder_wins INTEGER NOT NULL DEFAULT 0;',
      'ALTER TABLE players ADD COLUMN ladder_losses INTEGER NOT NULL DEFAULT 0;',
      'INSERT INTO revisions (date, comment) VALUES (date("now"), "add wins and losses count");'],

    [ 'CREATE TABLE admins (id INTEGER PRIMARY KEY NOT NULL, username TEXT, password_hash TEXT);',
      'INSERT INTO revisions (date, comment) VALUES (date("now"), "add admin account table");'],

    [ 'CREATE TABLE matches (id INTEGER PRIMARY KEY NOT NULL, challenger_id INTEGER NOT NULL REFERENCES players(id), opponent_id INTEGER NOT NULL REFERENCES players(id), winner_id INTEGER NOT NULL REFERENCES players(id), cpoints INTEGER NOT NULL, opoints INTEGER NOT NULL, cgames TEXT NOT NULL, ogames TEXT NOT NULL, date DATE NOT NULL, tournament BOOL NOT NULL DEFAULT FALSE, retired BOOL NOT NULL DEFAULT FALSE, forfeited BOOL NOT NULL DEFAULT FALSE);',
      'INSERT INTO revisions (date, comment) VALUES (date("now"), "add matches table");'],

    [ 'ALTER TABLE players ADD COLUMN a_wins INTEGER NOT NULL DEFAULT 0;',
      'ALTER TABLE players ADD COLUMN a_losses INTEGER NOT NULL DEFAULT 0;',
      'ALTER TABLE players ADD COLUMN b_wins INTEGER NOT NULL DEFAULT 0;',
      'ALTER TABLE players ADD COLUMN b_losses INTEGER NOT NULL DEFAULT 0;',
      'ALTER TABLE players ADD COLUMN c_wins INTEGER NOT NULL DEFAULT 0;',
      'ALTER TABLE players ADD COLUMN c_losses INTEGER NOT NULL DEFAULT 0;',
      'INSERT INTO revisions (date, comment) VALUES (date("now"), "separate win/loss counter for each ladder");'],

    [ 'ALTER TABLE matches ADD COLUMN ladder TEXT;',
      'INSERT INTO revisions (date, comment) VALUES (date("now"), "add ladder to match entry");'],

    [ 'CREATE VIEW matches_with_names as select matches.*, p1.last_name, p2.last_name from matches join players p1 on p1.id = matches.challenger_id join players p2 on p2.id = matches.opponent_id;',
      'INSERT INTO revisions (date, comment) VALUES (date("now"), "added matches view with player names");'],

    [ 'CREATE TABLE seasons (id INTEGER PRIMARY KEY NOT NULL, title TEXT UNIQUE, start_date DATE, end_date DATE, active BOOL NOT NULL DEFAULT FALSE);',
      'INSERT INTO seasons (title, active) VALUES ("default test season", 1);',
      'ALTER TABLE matches ADD COLUMN season_id INTEGER REFERENCES seasons(id);',
      'UPDATE matches SET season_id=1;',
      'INSERT INTO revisions (date, comment) VALUES (date("now"), "added seasons");'],

    [ 'CREATE TABLE player_archive (id INTEGER PRIMARY KEY  NOT NULL, season_id INTEGER REFERENCES seasons(id), player_id INTEGER REFERENCES players(id), ladder TEXT, active BOOL NOT NULL  DEFAULT false, points INTEGER NOT NULL  DEFAULT 0, initial_points NOT NULL DEFAULT 0, wins INTEGER NOT NULL DEFAULT 0, losses INTEGER NOT NULL DEFAULT 0, a_wins INTEGER NOT NULL DEFAULT 0, a_losses INTEGER NOT NULL DEFAULT 0, b_wins INTEGER NOT NULL DEFAULT 0, b_losses INTEGER NOT NULL DEFAULT 0, c_wins INTEGER NOT NULL DEFAULT 0, c_losses INTEGER NOT NULL DEFAULT 0);',
      'INSERT INTO revisions (date, comment) VALUES (date("now"), "added player_archive");'],
    ['CREATE TABLE tokens (id INTEGER PRIMARY KEY NOT NULL, token TEXT NOT NULL, type TEXT NOT NULL, expires DATE NOT NULL, since DATE);',
     'INSERT INTO revisions (date, comment) VALUES (date("now"), "added tokens table");'],
    ['ALTER TABLE players ADD COLUMN location TEXT;',
     'ALTER TABLE players ADD COLUMN note TEXT;',
     'INSERT INTO revisions (date, comment) VALUES (date("now"), "added note and location");'],
    [ 'ALTER TABLE players ADD COLUMN wlocation TEXT;',
      'INSERT INTO revisions (date, comment) VALUES (date("now"), "added work location");'],
    [ 'ALTER TABLE players ADD COLUMN tournament_qualified_override INTEGER NOT NULL DEFAULT 0;',
      'ALTER TABLE player_archive ADD COLUMN tournament_qualified_override INTEGER NOT NULL DEFAULT 0;',
      'INSERT INTO revisions (date, comment) VALUES (date("now"), "fields needed for tournament qualification");'],
    [ 'ALTER TABLE seasons ADD COLUMN tournament_date DATE;',
      'ALTER TABLE seasons ADD COLUMN tournament_min_matches INTEGER NOT NULL DEFAULT 9;',
      'ALTER TABLE seasons ADD COLUMN tournament_min_opponents INTEGER NOT NULL DEFAULT 5;',
      'INSERT INTO revisions (date, comment) VALUES (date("now"), "more fields needed for tournament qualification");'],
    [ 'ALTER TABLE players ADD COLUMN a_promotion DATE;',
      'ALTER TABLE players ADD COLUMN b_promotion DATE;',
      'ALTER TABLE players ADD COLUMN c_promotion DATE;',
      'INSERT INTO revisions (date, comment) VALUES (date("now"), "add ladder promotion dates");']
]

class Database:

    def _compare_ladders(self, l1, l2):
        if self._ladder_weights.get(l1) == self._ladder_weights.get(l2):
            return 0
        if self._ladder_weights.get(l1) > self._ladder_weights.get(l2):
            return 1
        if self._ladder_weights.get(l1) < self._ladder_weights.get(l2):
            return -1

    def player_ladder_for_date(self, player_id, date):
        self._cursor.execute('SELECT a_promotion, b_promotion, c_promotion, ladder FROM players WHERE id=?', (player_id,))
        v = self._cursor.fetchall()
        if len(v) == 0:
            self._log.error("player {} not found".format(player_id))
            return None
        assert len(v) == 1
        a_promotion, b_promotion, c_promotion, ladder = v[0]
        a_prm, b_prm, c_prm = None, None, None
        if ladder.lower() == 'a':
            if not a_promotion:
                # A-player that has been in A-ladder forever
                a_prm = datetime.min
                if b_promotion or c_promotion:
                    self._log.warning("expected None for a-ladder player {}, got: b_promotion={}, c_promotion={}".format(player_id, b_promotion, c_promotion))
                b_promotion = None
                c_promotion = None
            else:
                # A-player that entered A-ladder at some point
                a_prm = datetime.strptime(a_promotion, '%Y-%m-%d')
            if not b_promotion:
                # A-player that has been in B forever before being
                # promoted to A or started directly in A
                b_prm = datetime.min
                if c_promotion:
                    self._log.warning("expected None for a-ladder player {}, got: c_promotion={}".format(player_id, c_promotion));
                c_promotion = None;
            else:
                # A-player that entered B at some point
                b_prm = datetime.strptime(b_promotion, '%Y-%m-%d')
            if not c_promotion:
                # A player that has been in C forever before being promoted
                # to A or B or started directly in either B or C
                c_prm = datetime.min
            else:
                c_prm = datetime.strptime(c_promotion, '%Y-%m-%d')
        elif ladder.lower() == 'b':
            # B-player, can't have A-promotion date, period
            if a_promotion:
                self._log.warning("expected None for b-ladder player {}, got: a_promotion={}".format(player_id, a_promotion))
            a_promotion = None
            a_prm = datetime.max
            if not b_promotion:
                # B-player that has been in B forever
                b_prm = datetime.min
                if c_promotion:
                    self._log.warning("expected None for b-ladder player {}, got: c_prmotion={}".format(player_id, c_promotion))
                c_promotion = None
            else:
                # B-player that has entered B at some point
                b_prm = datetime.strptime(b_promotion, '%Y-%m-%d')
            if not c_promotion:
                # B-player that has been in C forever before promoted to B or
                # started directly in B
                c_prm = datetime.min
            else:
                # B-player that has been at some point promoted to C
                c_prm = datetime.strptime(c_promotion, '%Y-%m-%d')
        elif ladder.lower() == 'c':
            if a_promotion or b_promotion:
                self._log.warning("expected None for c-ladder player {}, got: a_promotion={}, b_promotion={}".format(player_id, a_promotion, b_promotion))
            a_promotion = None
            b_promotion = None
            a_prm = datetime.max
            b_prm = datetime.max
            if not c_promotion:
                # C-player that has been in C forever or started in C
                c_prm = datetime.min
            else:
                # C-player that has been promoted to C at some point
                c_prm = datetime.strptime(c_promotion, '%Y-%m-%d')
        else:
            if ladder.lower() != "unranked":
                self._log.warning("expected unranked player ladder, got: {}".format(ladder.lower()))
            return "unranked"
        assert (a_prm and b_prm and c_prm) is not None
        self._log.info("checking player {} for {} in ranges {}-{}-{}".format(player_id, date, c_prm, b_prm, a_prm))
        if date >= a_prm:
            ladder = "a"
        elif date >= b_prm and date < a_prm:
            ladder = "b"
        elif date >= c_prm and date < b_prm:
            ladder = "c"
        else:
            ladder = "unranked"
        self._log.info("player {} was in ladder {} on {}".format(player_id, ladder, date))
        return ladder

    def get_season(self):
        self._cursor.execute('SELECT id, start_date, end_date, title FROM seasons WHERE active=1')
        v = self._cursor.fetchall()
        assert len(v) == 1
        v = v[0]
        return v

    def set_tournament_parameters(self, start_date, min_matches, min_opponents):
        season_id, _, _, _ = self.get_season()
        self._cursor.execute("UPDATE seasons SET tournament_date=?, tournament_min_matches=?, tournament_min_opponents=? WHERE id=?", (start_date, min_matches, min_opponents, season_id))
        self._conn.commit()

    def get_tournament_parameters(self):
        self._cursor.execute('SELECT tournament_min_matches, tournament_min_opponents, tournament_date FROM seasons WHERE active=1')
        v = self._cursor.fetchall()
        assert len(v) == 1
        return v[0]

    def get_match_and_opponent_count(self, player_id):
        # all-opponent set cardinal number is the number of different opponents the player had
        self._cursor.execute('SELECT COUNT(*) FROM (SELECT opponent_id FROM matches WHERE challenger_id=? UNION SELECT challenger_id FROM matches WHERE opponent_id=?)', (player_id, player_id))
        v = self._cursor.fetchall()
        assert len(v) == 1
        num_opponents_tuple = v[0]
        # very similar query, but without unique union will give us all matches played
        self._cursor.execute('SELECT COUNT(*) FROM (SELECT opponent_id FROM matches WHERE challenger_id=? UNION ALL SELECT challenger_id FROM matches WHERE opponent_id=?)', (player_id, player_id))
        v = self._cursor.fetchall()
        assert len(v) == 1
        num_matches_tuple = v[0]
        return num_matches_tuple + num_opponents_tuple

    def new_token(self, token_type, since_date, expires_date):
        token_value = None
        while not token_value:
            token_value = "".join([random.choice(string.ascii_letters + string.digits) for _ in xrange(32)])
            self._cursor.execute('SELECT id FROM tokens WHERE token=?', (token_value,))
            v = self._cursor.fetchall()
            if len(v) > 0:
                token_value = None
        token_tuple = (token_type, since_date, expires_date, token_value)
        self._cursor.execute("INSERT INTO tokens (type, since, expires, token) VALUES (?, ?, ?, ?)", token_tuple)
        self._conn.commit()
        return token_value, self._cursor.lastrowid, None

    def new_season(self, start_date, end_date, title, tournament_date = None):
        if not tournament_date:
            tournament_date = end_date
        self._cursor.execute("SELECT id FROM seasons WHERE title=?", (title,))
        titles = self._cursor.fetchall()
        if len(titles):
            return None, "Season title already in use"
        self._cursor.execute("SELECT seasons.id, players.id, ladder, points, initial_points, players.active, wins, losses, a_wins, a_losses, b_wins, b_losses, c_wins, c_losses FROM players LEFT JOIN seasons WHERE seasons.active=1")
        archived_players = self._cursor.fetchall()
        self._log.debug("archived {} players".format(len(archived_players)))
        for ap in archived_players:
            self._log.debug("  {}".format(ap))
            self._cursor.execute("INSERT INTO player_archive (season_id, player_id, ladder, points, initial_points, active, wins, losses, a_wins, a_losses, b_wins, b_losses, c_wins, c_losses) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", ap)
        season_value_tuple = (start_date, end_date, tournament_date, title, 1)
        self._cursor.execute("UPDATE seasons set active=0")
        self._cursor.execute("UPDATE players set active=0, points=0, initial_points=0, wins=0, losses=0, a_wins=0, a_losses=0, b_wins=0, b_losses=0, c_wins=0, c_losses=0,  tournament_qualified_override=0")
        self._log.debug("new season value tuple: {}".format(season_value_tuple))
        self._cursor.execute("INSERT INTO seasons (start_date, end_date, tournament_date, title, active) VALUES (?, ?, ?, ?, ?)", season_value_tuple)
        self._conn.commit()
        return self._cursor.lastrowid, None

    def get_db_version(self):
        self._cursor.execute('SELECT max(id) FROM REVISIONS')
        v = self._cursor.fetchall()
        if not v:
            return 0
        assert len(v) == 1
        v = v[0]
        assert len(v) == 1
        return v[0]

    def get_recent_matches(self, ladder, since):
        season_id, _, _, _ = self.get_season()
        keys = { 'ladder': ladder, 'since': since, 'season_id': season_id}
        return self.lookup_match(keys)

    def get_ladder(self, ladder = None, player_id = None):
        fields = ["first_name", "last_name", "points", "id", "wins", "losses", "a_wins", "a_losses", "b_wins", "b_losses", "c_wins", "c_losses",  "tournament_qualified_override"]
        fields_string = string.join(fields, ',')
        query_fields = ['active=1']
        query_values = []
        if ladder:
            query_fields += [ "ladder=?" ]
            query_values += [ ladder ]
        if player_id:
            query_fields += [ "id=?" ]
            query_values += [ player_id ]
        query_string = string.join(query_fields, ' and ')
        r = [ dict(zip(fields, record)) for record in self._cursor.execute("SELECT {} FROM players WHERE {} ORDER BY points DESC".format(fields_string, query_string), tuple(query_values)) ]
        er = [ self._expand_with_tournament_flag(record) for record in r ]
        return er

    def no_admins(self):
        check = [ record for record in self._cursor.execute("SELECT id FROM admins") ]
        if len(check) == 0:
            return True
        else:
            return False

    def check_token(self, token, token_type):
        self._log.debug("check_token: {}".format(token))
        self._cursor.execute("SELECT since, expires FROM tokens WHERE token=? and type=?", (token, token_type))
        v = self._cursor.fetchall()
        self._log.debug("check_token: {}".format(v))
        if len(v) == 0:
            return False, None, None
        assert len(v) == 1
        return True, v[0][0], v[0][1]

    def check_password(self, username, password, table):
        self._log.debug("check_password: {} in {}".format(username, table))
        fields = ["id", "password_hash"]
        fields_string = string.join(fields, ',')
        r = [ dict(zip(fields, record)) for record in self._cursor.execute("SELECT {} FROM {} WHERE username=?".format(fields_string, table), (username,)) ]
        assert len(r) < 2
        if len(r) == 0:
            self._log.debug("check_password: {} not found in {}".format(username, table))
            return None
        else:
            if bcrypt.hashpw(str(password), str(r[0].get('password_hash'))) == str(r[0].get('password_hash')):
                self._log.debug("check_password: {} authenticated in {}".format(username, table))
                return r[0].get('id')
            else:
                self._log.debug("check_password: {} in {} password check failed".format(username, table))
                return None

    def _expand_with_tournament_flag(self, player):
        qualified = False
        player_id = player.get('id')
        qualified_override = player.get('tournament_qualified_override')
        if player_id != None and qualified_override != None:
            if qualified_override == 0:
                min_matches, min_opponents, _ = self.get_tournament_parameters()
                matches, opponents = self.get_match_and_opponent_count(player_id)
                qualified = (matches >= min_matches and opponents >= min_opponents)
            elif qualified_override > 0:
                qualified = True
        player.update({'tournament_qualified': qualified})
        return player

    def get_roster(self):
        fields = ["first_name", "last_name", "cell_phone", "home_phone", "work_phone", "email", "id", "ladder", "company", "location", "wlocation", "tournament_qualified_override"]
        fields_string = string.join(fields, ',')
        r = [ dict(zip(fields, record)) for record in self._cursor.execute("SELECT {} FROM players WHERE active=1 ORDER BY last_name".format(fields_string)) ]
        er = [ self._expand_with_tournament_flag(record) for record in r ]
        return er

    def update_player(self, player, player_id = None):
        # first override initial points if necessary
        reset_points = False
        if player_id == None:
            # on add, treat None for initial points as zero
            if player.get('initial_points') == None:
                player.update({'initial_points' : 0})
            reset_points = True
        else:
            # on update, treat None as "leave unchanged", otherwise set
            if player.get('initial_points') == None:
                self._cursor.execute("SELECT initial_points FROM players WHERE id=?", (player_id,))
                initial_points = self._cursor.fetchall()
                if len(initial_points) == 0:
                    # REVISIT: ugly hack, we have a similar check later down in this function
                    # but we have to have another one here
                    return -1, "player ID not found"
                initial_points = initial_points[0][0]
                player.update({'initial_points' : initial_points})
            else:
                reset_points = True
        # now construct the tuple for the database (first the straightforward ones)
        fields_tuple = self._common_player_fields
        values_tuple = tuple([ player.get(f) for f in fields_tuple ])
        # next fields that need some massage
        if reset_points:
            # set points to be the same as initial points when adding new player
            # or updating the existing player, but the user has set them
            fields_tuple = fields_tuple + ('points',)
            values_tuple = values_tuple + (player.get('initial_points'),)
        player_password = player.get('password')
        if player_password:
            fields_tuple = fields_tuple + ('password_hash',)
            password_hash = bcrypt.hashpw(player_password, bcrypt.gensalt())
            values_tuple = values_tuple + (password_hash,)
        assert(len(fields_tuple) == len(values_tuple))
        values_pattern = ('?,' * len(values_tuple))[:-1]
        self._log.debug("update_player: fields are {}".format(fields_tuple))
        self._log.debug("update_player: values are {}".format(values_tuple))
        check_username = player.get('username')
        if player_id == None:
            check = [ record for record in self._cursor.execute("SELECT id FROM players WHERE username=? COLLATE NOCASE", (check_username,))] + [ record for record in self._cursor.execute("SELECT id FROM admins WHERE username=? COLLATE NOCASE", (check_username,))]
            if len(check) > 0:
                return -1, "username conflict"
            self._cursor.execute("INSERT INTO players {} VALUES ({})".format(fields_tuple, values_pattern), values_tuple)
            self._conn.commit()
            return self._cursor.lastrowid, None
        else:
            check = [ record for record in self._cursor.execute("SELECT id FROM players WHERE id=?", (player_id,)) ]
            if len(check) == 0:
                return -1, "player ID not found"
            check = [ record for record in self._cursor.execute("SELECT id FROM players WHERE not id=? and username=?", (player_id, check_username)) ]
            if len(check) != 0:
                return -1, "username conflict"
            fields_string = string.join([ f + "=?" for f in fields_tuple ], ', ')
            values_tuple += (player_id,)
            self._cursor.execute("UPDATE players SET {} WHERE id=?".format(fields_string), values_tuple)
            self._conn.commit()
            return player_id, None

    def _lookup_something(self, fields, operator, table_name, common_fields, translated_fields, special_fields = {}):
        tfk = tuple(t for t in translated_fields)
        tfs = tuple(translated_fields.get(t) for t in tfk)
        sfk = tuple(special_fields.keys())
        api_fields = common_fields + tfk + sfk
        select_fields = string.join(common_fields + tfs, ', ')
        match_tuple = ()
        where_list = []
        for w in api_fields:
            f = fields.get(w)
            if f != None:
                match_tuple = match_tuple + (f,)
                if w in sfk:
                    # special field: translates and has custom operator
                    # safe to do without the check, because sfk has all keys and keys are invariant
                    wt = special_fields.get(w).get('field')
                    c_operator = special_fields.get(w).get('operator')
                    self._log.debug('_lookup_something: special field: {} --> {} , {}'.format(w, wt, c_operator))
                    where_list = where_list + ['{} {} ?'.format(wt, c_operator)]
                else:
                    # direct or translated field: operator is always '='
                    wt = translated_fields.get(w)
                    where_list = where_list + ['{} = ?'.format(wt if wt else w)]
        where_string = string.join(where_list, ' OR ' if operator == 'or' else ' AND ')
        self._log.debug("_lookup_something: where string is {}".format(where_string))
        self._log.debug("_lookup_something: match tuple is {}".format(match_tuple))
        self._log.debug("_lookup_something: select fields are {}".format(select_fields))
        self._log.debug("_lookup_something: api fields are {}".format(api_fields))
        self._log.debug("_lookup_something: table is {}".format(table_name))
        if where_string:
            r = [ dict(zip(api_fields, record)) for record in self._cursor.execute("SELECT {} FROM {} WHERE {} COLLATE NOCASE".format(select_fields, table_name, where_string), match_tuple) ]
        else:
            r = [ dict(zip(api_fields, record)) for record in self._cursor.execute("SELECT {} FROM {}".format(select_fields, table_name)) ]
        self._log.debug("_lookup_something: result is {}".format(r))
        return [util.purge_null_fields(e) for e in r]

    def lookup_player(self, fields, operator):
        players = self._lookup_something(fields, operator, "players", self._common_player_fields, self._translated_player_fields)
        for p in players:
            p.pop('initial_points')
        return players

    def lookup_match(self, fields):
        # ladder is special: it can be searched, but it is generated when match is added
        # so it's not listed in the common fields tuple; we add it for search
        modified_common_match_fields = self._common_match_fields + ('ladder', 'last_name', '`last_name:1`', )
        res = self._lookup_something(fields, "and", "matches_with_names", modified_common_match_fields, self._translated_match_fields, self._special_match_fields)
        for r in res:
            r['challenger_last_name'] = r.pop('last_name')
            r['opponent_last_name'] = r.pop('`last_name:1`')
        return res

    def delete_player(self, player_id):
        self._log.debug("delete_player: trying to delete player with ID {}".format(player_id))
        try:
            self._cursor.execute("DELETE FROM players WHERE id=?", (player_id,))
            self._conn.commit()
        except:
            self._log.error("delete_player: failed to delete player with ID {}".format(player_id))
            return False
        return True

    def update_account(self, account, old_username = None):
        # construct tuples for the database
        fields_tuple = ('username', 'password_hash')
        password_hash = bcrypt.hashpw(account.get('password'), bcrypt.gensalt())
        values_tuple = (account.get('username'), password_hash)
        values_pattern = ('?,' * len(values_tuple))[:-1]
        self._log.debug("update_account: fields are {}".format(fields_tuple))
        self._log.debug("update_account: values are {}".format(values_tuple))
        if old_username == None:
            check_username = account.get('username')
            check = [ record for record in self._cursor.execute("SELECT id FROM players WHERE username=? COLLATE NOCASE", (check_username,))] + [ record for record in self._cursor.execute("SELECT id FROM admins WHERE username=? COLLATE NOCASE", (check_username,))]
            if len(check) > 0:
                return -1, "username conflict"
            self._cursor.execute("INSERT INTO admins {} VALUES ({})".format(fields_tuple, values_pattern), values_tuple)
            self._conn.commit()
            return self._cursor.lastrowid, None
        else:
            check = [ record for record in self._cursor.execute("SELECT id FROM admins WHERE username=?", (old_username,)) ]
            if len(check) == 0:
                return -1, "account not found"
            elif len(check) > 1:
                return -1, "cowardly refusing to modify conflicting accounts"
            fields_string = string.join([ f + "=?" for f in fields_tuple ], ', ')
            values_tuple += (old_username,)
            self._cursor.execute("UPDATE admins SET {} WHERE username=?".format(fields_string), values_tuple)
            self._conn.commit()
            return check[0][0], None

    def lookup_account(self, fields, operator):
        return self._lookup_something(fields, operator, "admins", self._common_account_fields, self._translated_account_fields)

    def delete_account(self, username):
        self._log.debug("delete_account: trying to delete account {}".format(username))
        check = [ record for record in self._cursor.execute("SELECT id FROM admins WHERE username=?", (username,)) ]
        if len(check) == 0:
            return -1, "account not found"
        elif len(check) > 1:
            return -1, "cowardly refusing to delete conflicting accounts"
        try:
            self._cursor.execute("DELETE FROM admins WHERE username=?", (username,))
            self._conn.commit()
        except:
            err = "failed to delete account {}".format(username)
            self._log.error("delete_account: {}".format(err))
            return -1, err
        return check[0][0], None

    def add_match(self, match):
        self._log.debug("add_match: {}".format(match))
        season_id, start_date, end_date, _ = self.get_season()
        # if query came in with season_id, override it to current season, if
        # it came in without season_id, set it
        match['season_id'] = season_id
        match_date = match.get('date')
        _, _, tournament_date = self.get_tournament_parameters()
        self._log.info("season id is {} ({}:{})".format(season_id, start_date, end_date))
        self._log.info("match date is {}".format(match_date))
        self._log.info("tournament date is {}".format(tournament_date))
        md = datetime.strptime(match_date, '%Y-%m-%d')
        try:
            td = datetime.strptime(tournament_date, '%Y-%m-%d')
        except:
            td = None
        if start_date != None and end_date != None:
            # enforce season dates if they exist
            sd = datetime.strptime(start_date, '%Y-%m-%d')
            ed = datetime.strptime(end_date, '%Y-%m-%d')
            if md > ed or md < sd:
                return -1, None, None, "match date out of season date-range"
        fields_tuple = self._common_match_fields
        values_tuple = tuple([ match.get(f) for f in fields_tuple ])
        assert(len(fields_tuple) == len(values_tuple))
        winner_id = match.get("winner_id")
        challenger_id = match.get("challenger_id")
        opponent_id = match.get("opponent_id")
        self._cursor.execute("SELECT id FROM matches WHERE season_id=? AND ((challenger_id=? AND opponent_id=?) OR (challenger_id=? AND opponent_id=?))", (season_id, challenger_id, opponent_id, opponent_id, challenger_id))
        challenger_vs_opponent = len(self._cursor.fetchall()) + 1
        self._cursor.execute("SELECT id FROM matches WHERE season_id=? AND (challenger_id=? OR opponent_id=?)", (season_id, challenger_id, challenger_id))
        challenger_matches = len(self._cursor.fetchall()) + 1
        self._cursor.execute("SELECT id FROM matches WHERE season_id=? AND (challenger_id=? OR opponent_id=?)", (season_id, opponent_id, opponent_id))
        opponent_matches = len(self._cursor.fetchall()) + 1
        self._log.info("match limit inputs {} {} {}".format(challenger_matches, opponent_matches, challenger_vs_opponent))
        if rules.match_limit_reached(challenger_vs_opponent, challenger_matches, opponent_matches):
            return -1, None, None, 'match limit reached for this pair of players'
        loser_id = opponent_id if winner_id == challenger_id else challenger_id
        # check that referred player IDs are valid
        check = [ record for record in self._cursor.execute("SELECT ladder, last_name FROM players WHERE id=? and active=1", (opponent_id,)) ]
        if len(check) == 0:
            return -1, None, None, "invalid opponent ID (is the player active?)"
        else:
            opponent_ladder = check[0][0]
            opponent_last_name = check[0][1]
        check = [ record for record in self._cursor.execute("SELECT ladder, last_name FROM players WHERE id=? and active=1", (challenger_id,)) ]
        if len(check) == 0:
            return -1, None, None, "invalid challenger ID (is the player active?)"
        else:
            challenger_ladder = check[0][0]
            challenger_last_name = check[0][1]
        if td:
            if md >= td and opponent_ladder != challenger_ladder:
                return -1, None, None, "inter-ladder matches not allowed during the tournament"
        check = [ record for record in self._cursor.execute("SELECT id FROM players WHERE id=?", (winner_id,)) ]
        if len(check) == 0:
            return -1, None, None, "invalid winner ID"
        winner_ladder = challenger_ladder if winner_id == challenger_id else opponent_ladder
        loser_ladder = challenger_ladder if winner_id == opponent_id else opponent_ladder
        if self._compare_ladders(opponent_ladder, challenger_ladder) >= 0:
            match_ladder = opponent_ladder
        else:
            return -1, None, None, "Challenger must be from lower ladder"
        winner_last_name = challenger_last_name if winner_id == challenger_id else opponent_last_name
        loser_last_name = challenger_last_name if winner_id == opponent_id else opponent_last_name
        self._log.debug("winner is {} from ladder {}; loser is {} from ladder {}".format(winner_last_name, winner_ladder, loser_last_name, loser_ladder))
        if winner_ladder in ["beginner", "unranked"] and loser_ladder in ["beginner", "unranked"]:
            return -1, None, None, "Unranked or beginner players cannot play each other"
        # promotion to higher ladder, if winner came from lower ladder
        if self._compare_ladders(winner_ladder, loser_ladder) < 0:
            winner_ladder = loser_ladder
            # if winner is promoted, the points reset to zero they will be updated to 30
            # in subsequent operations within this transaction
            self._cursor.execute("UPDATE players SET points=0 WHERE id=?", (winner_id,))
            # record the promotion date
            if winner_ladder == 'a':
                self._cursor.execute("UPDATE players SET a_promotion=? WHERE id=?", (match_date, winner_id))
            elif winner_ladder == 'b':
                self._cursor.execute("UPDATE players SET b_promotion=? WHERE id=?", (match_date, winner_id))
            elif winner_ladder == 'c':
                self._cursor.execute("UPDATE players SET c_promotion=? WHERE id=?", (match_date, winner_id))
        self._log.debug("add_match: fields are {}".format(fields_tuple))
        self._log.debug("add_match: values are {}".format(values_tuple))
        # loser in beginner or unranked ladder gets no points
        if not (loser_id == challenger_id and challenger_ladder in ["unranked", "beginner"]):
            self._cursor.execute("UPDATE players SET points=points+? WHERE id=?",
                                 (match.get('cpoints'), challenger_id))
        if not (loser_id == opponent_id and opponent_ladder in ["unranked", "beginner"]):
            self._cursor.execute("UPDATE players SET points=points+? WHERE id=?",
                                 (match.get('opoints'), opponent_id))
        # record wins and losses counters
        self._cursor.execute("UPDATE players SET wins=wins+1 WHERE id=?", (winner_id,))
        self._cursor.execute("UPDATE players SET losses=losses+1 WHERE id=?", (loser_id,))
        if match_ladder == 'a':
            self._cursor.execute("UPDATE players SET a_wins=a_wins+1 WHERE id=?", (winner_id,))
            self._cursor.execute("UPDATE players SET a_losses=a_losses+1 WHERE id=?", (loser_id,))
        elif match_ladder == 'b':
            self._cursor.execute("UPDATE players SET b_wins=b_wins+1 WHERE id=?", (winner_id,))
            self._cursor.execute("UPDATE players SET b_losses=b_losses+1 WHERE id=?", (loser_id,))
        elif match_ladder == 'c':
            self._cursor.execute("UPDATE players SET c_wins=c_wins+1 WHERE id=?", (winner_id,))
            self._cursor.execute("UPDATE players SET c_losses=c_losses+1 WHERE id=?", (loser_id,))
        # writing winner ladder will make sure that possible promotion is recorded
        self._cursor.execute("UPDATE players SET ladder=? WHERE id=?", (winner_ladder, winner_id))
        # finally, record the match (add calculated ladder column and season column)
        fields_tuple = fields_tuple + ('ladder',)
        values_tuple = values_tuple + (match_ladder,)
        values_pattern = ('?,' * len(values_tuple))[:-1]
        insert_query = "INSERT INTO matches {} VALUES ({})".format(fields_tuple, values_pattern)
        self._log.debug("query: {}".format(insert_query))
        self._log.debug("values: {}".format(values_tuple))
        self._cursor.execute(insert_query, values_tuple)
        self._conn.commit()
        return self._cursor.lastrowid, winner_last_name, loser_last_name, None

    def __init__(self, db_file):
        self._log = util.get_syslog_logger("db")
        if os.path.isfile(db_file):
            self._log.info("found database file {}".format(db_file))
            new_db = False
        else:
            self._log.info("database file not found, creating {}".format(db_file))
            new_db = True
        self._conn = sqlite3.connect(db_file)
        self._cursor = self._conn.cursor()
        self._cursor.execute('PRAGMA foreign_keys = ON;')
        self._conn.commit()
        if new_db:
            db_version = 0
        else:
            db_version = self.get_db_version()
        self._log.info("DB version is {}".format(db_version))
        v = db_version
        for t in _schema[db_version:]:
            v = v + 1
            self._log.debug("upgrading schema to version {}".format(v))
            for q in t:
                self._log.info("  {}".format(q))
                self._cursor.execute(q)
        self._conn.commit()
        db_version = self.get_db_version()
        assert db_version == v
        self._common_player_fields = ( 'username', 'first_name', 'last_name', 'email', 'home_phone', 'work_phone', 'cell_phone', 'company', 'ladder', 'active', 'initial_points', 'location', 'wlocation', 'note', 'tournament_qualified_override', 'a_promotion', 'b_promotion', 'c_promotion' )
        self._translated_player_fields = { 'player_id' : 'id' }
        self._common_account_fields = ( 'username', )
        self._translated_account_fields = { 'account_id' : 'id' }
        self._common_match_fields = ('challenger_id', 'opponent_id', 'winner_id', 'cpoints', 'opoints', 'cgames', 'ogames', 'date', 'retired', 'forfeited', 'season_id')
        self._translated_match_fields = { }
        self._special_match_fields = {'since': {'field': 'date', 'operator': '>='}}
        self._ladder_weights = {'a': 3, 'b': 2, 'c':1, 'unranked':0}
