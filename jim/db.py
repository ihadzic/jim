import sqlite3
import logging

def _get_db_version(c):
    c.execute('select max(id) from revisions;')
    v = c.fetchone()
    if not v:
        v = 0
    return v

class Database:

    def __init__(self, db_file):
        self._log = logging.getLogger("db")
        if os.path.isfile(db_file):
            _log.info("found database file {}".format(db_file))
            new_db = False
        else:
            _log.info("database file not found, creating {}".format(db_file))
            new_db = False
        self._conn = sqlite3.connect(db_file)
        self._cursor = self._conn.cursor()
        if new_db:
            db_version = 0
        else:
            db_version = _get_db_version(self._cursor)
        _log.info("DB version is {}".format(db_version))
