import util
import sqlite3
import string
import os
import bcrypt

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
      'INSERT INTO revisions (date, comment) VALUES (date("now"), "add admin account table");']

]

class Database:

    def get_db_version(self):
        self._cursor.execute('SELECT max(id) FROM REVISIONS')
        v = self._cursor.fetchall()
        if not v:
            return 0
        assert len(v) == 1
        v = v[0]
        assert len(v) == 1
        return v[0]

    def get_ladder(self, ladder):
        fields = ["first_name", "last_name", "points", "id", 'wins', 'losses', 'ladder_wins', 'ladder_losses']
        fields_string = string.join(fields, ',')
        r = [ dict(zip(fields, record)) for record in self._cursor.execute("SELECT {} FROM players WHERE ladder=? ORDER BY points DESC".format(fields_string), (ladder,)) ]
        return r

    def no_admins(self):
        check = [ record for record in self._cursor.execute("SELECT id FROM admins") ]
        if len(check) == 0:
            return True
        else:
            return False

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

    def get_roster(self):
        fields = ["first_name", "last_name", "cell_phone", "home_phone", "work_phone", "email", "id", "ladder", "company"]
        fields_string = string.join(fields, ',')
        r = [ dict(zip(fields, record)) for record in self._cursor.execute("SELECT {} FROM players WHERE active=1 ORDER BY last_name".format(fields_string)) ]
        return r

    def update_player(self, player, player_id = None):
        # construct the tuple for the database (first the straightforward ones)
        fields_tuple = self._common_player_fields
        values_tuple = tuple([ player.get(f) for f in fields_tuple ])
        # next fields that need some massage

        # set points to be the same as initial points when adding new player
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
        if player_id == None:
            check_username = player.get('username')
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
            fields_string = string.join([ f + "=?" for f in fields_tuple ], ', ')
            values_tuple += (player_id,)
            self._cursor.execute("UPDATE players SET {} WHERE id=?".format(fields_string), values_tuple)
            self._conn.commit()
            return player_id, None

    def _lookup_something(self, fields, operator, table_name, common_fields, translated_fields):
        tfk = tuple(t for t in translated_fields)
        tfs = tuple(translated_fields.get(t) for t in tfk)
        api_fields = common_fields + tfk
        select_fields = string.join(common_fields + tfs, ', ')
        match_tuple = ()
        where_list = []
        for w in fields and api_fields:
            f = fields.get(w)
            if f != None:
                match_tuple = match_tuple + (f,)
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
        return self._lookup_something(fields, operator, "players", self._common_player_fields, self._translated_player_fields)

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
        self._common_player_fields = ( 'username', 'first_name', 'last_name', 'email', 'home_phone', 'work_phone', 'cell_phone', 'company', 'ladder', 'active', 'initial_points' )
        self._translated_player_fields = { 'player_id' : 'id' }
        self._common_account_fields = ( 'username', )
        self._translated_account_fields = { 'account_id' : 'id' }
