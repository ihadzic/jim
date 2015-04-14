#/usr/bin/env python2

import web
import log
import ConfigParser

def read_config(parser):
    cfg = {}
    try:
        http_port = parser.get("web", "http_port")
    except:
        http_port = None
    try:
        https_port = parser.get("web", "https_port")
    except:
        https_port = None
    if http_port:
        cfg['http_port'] = int(http_port)
    if https_port:
        cfg['https_port'] = int(https_port)
    _log.info(cfg)
    return cfg

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
    _cfg = read_config(_config_file_parser)
    _log.info("server configuration: {}".format(_cfg))
    _log.info("starting server")
    web.run_server(log_facility = _log)
    _log.info("server exited")
else:
    _log.error("configuration error")
