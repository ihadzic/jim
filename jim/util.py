#!/usr/bin/env python2

import sys
import logging

# This is default (test-only) certificate located in ./certs directory.
# default certificate is self-signed, so we don't have 'ca_cert' field
# in the dictionary. Normally, we need one to point to the 'CA'
test_ssl_options = { 'certfile' : sys.prefix + '/var/jim/certs/cert.pem', 'keyfile': sys.prefix + '/var/jim/certs/key.pem' }


def str_to_bool(s):
    if s.lower() in ['true', 'yes', '1', 't', 'on']:
        return True
    elif s.lower() in ['false', 'no', '0', 'f', 'off']:
        return False
    else:
        return None

def int_or_none(x):
    if x == None:
        return None
    else:
        return int(x)

def bool_or_none(s):
    if s == None:
        return None
    else:
        return str_to_bool(s)

def purge_null_fields(d):
    return { f:d[f] for f in d if d[f] != None}

_handler = None

def get_syslog_logger(name):
    global _handler
    logger = logging.getLogger("main")
    if not _handler:
        _handler = logging.handlers.SysLogHandler(address='/dev/log')
    logger.addHandler(_handler)
    return logger
