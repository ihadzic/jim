#/usr/bin/env python2

import logging
import web
import ConfigParser
import os
import db
import sys

_log = None
# This is default (test-only) certificate located in ./certs directory.
# default certificate is self-signed, so we don't have 'ca_cert' field
# in the dictionary. Normally, we need one to point to the 'CA'
_test_ssl_options = { 'certfile' : sys.prefix + '/var/jim/certs/cert.pem', 'keyfile': sys.prefix + '/var/jim/certs/key.pem' }

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
    try:
        cfg['db_file'] = parser.get("db", "db_file")
    except:
        cfg['db_file'] = "./jim.db"
    try:
        cfg['bootstrap_token'] = parser.get("web", "bootstrap_token")
    except:
        cfg['bootstrap_token'] = 'jimimproved'
    try:
        cfg['certs_path'] = parser.get("web", "certs_path")
    except:
        cfg['certs_path'] = None
    _log.info(cfg)
    return cfg

def main():
    global _log
    logging.basicConfig(level=logging.DEBUG)
    _log = logging.getLogger("main")
    config_file_list = ['./jim.cfg', '/etc/jim.cfg', os.path.dirname(os.path.realpath(__file__)) + '/jim.cfg']
    config_file_parser = ConfigParser.RawConfigParser()
    config_ok = True
    try:
        config_file_list = config_file_parser.read(config_file_list)
    except:
        _log.error("cannot parse configuration file(s)")
        config_ok = False
    if len(config_file_list) == 0:
        _log.error("no configuration file found")
        config_ok = False
    else:
        _log.info("using configuration file {}".format(config_file_list[0]))
    if config_ok:
        cfg = read_config(config_file_parser)
        _log.info("server configuration: {}".format(cfg))
        _log.info("starting server")
        database = db.Database(cfg.get('db_file'))
        certs_path = cfg.get('certs_path')
        if certs_path:
            ssl_options = { 'certfile' : certs_path + '/cert.pem',
                            'keyfile': certs_path + '/key.pem' }
        else:
            ssl_options = _test_ssl_options
        web.run_server(ssl_options = ssl_options, http_port = cfg.get('http_port'), https_port = cfg.get('https_port'), html_root = cfg.get('html_root'), database = database, bootstrap_token = cfg.get('bootstrap_token'))
        _log.info("server exited")
    else:
        _log.error("configuration error")

if __name__ == "__main__":
    main()
