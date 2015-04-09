#/usr/bin/env python2

import web
import ConfigParser

_config_file_list = ['./jim.cfg', '/etc/jim.cfg']
_config_file_parser = ConfigParser.RawConfigParser()
_config_ok = True
try:
    _config_file_list = _config_file_parser.read(_config_file_list)
except:
    print("cannot parse configuration file(s)")
    _config_ok = False
if len(_config_file_list) == 0:
    print("no configuration file found")
    _config_ok = False
else:
    print("using configuration file {}".format(_config_file_list[0]))

if _config_ok:
    print("starting server")
    web.run_server()
    print("server exited")
