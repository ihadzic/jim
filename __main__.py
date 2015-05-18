#/usr/bin/env python2

import logging
import web
import ConfigParser

def read_config(parser):
    cfg = {}
    try:
        cfg['http_port'] = int(parser.get("web", "http_port"))
    except:
        cfg['http_port'] = None
    try:
        cfg['https_port'] = int(parser.get("web", "https_port"))
    except:
        cfg['https_port'] = None
    try:
        cfg['html_root'] = parser.get("web", "html_root")
    except:
        cfg['html_root'] = None
    try:
        cfg['template_root'] = parser.get("web", "template_root")
    except:
        cfg['template_root'] = None
    _log.info(cfg)
    return cfg

logging.basicConfig(level=logging.DEBUG)
_log = logging.getLogger("main")
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
    web.run_server(http_port = _cfg.get('http_port'), https_port = _cfg.get('https_port'), html_root = _cfg.get('html_root'))
    _log.info("server exited")
else:
    _log.error("configuration error")
