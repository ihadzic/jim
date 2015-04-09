#/usr/bin/env python2

import web
import log
import ConfigParser

_log = log.TrivialLogger()
_config_file_list = ['./jim.cfg', '/etc/jim.cfg']
_config_file_parser = ConfigParser.RawConfigParser()
_config_ok = True
try:
    _config_file_list = _config_file_parser.read(_config_file_list)
except:
    _log.error("cannot parse configuration file(s)")
    _config_ok = False
if len(_config_file_list) == 0:
    _log.error("no configuration file found")
    _config_ok = False
else:
    _log.info("using configuration file {}".format(_config_file_list[0]))


if _config_ok:
    _log.info("starting server")
    web.run_server(log_facility = _log)
    _log.info("server exited")
