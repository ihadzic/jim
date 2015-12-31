#!/usr/bin/env python2

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

def purge_null_fields(d):
    return { f:d[f] for f in d if d[f] != None}
