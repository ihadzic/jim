import logging

_log = logging.getLogger("rules")

def set_results(cgames, ogames):
    for i in range(0, len(ogames)):
        yield (cgames[i], ogames[i])

def process_match(cid, oid, cgames, ogames):
    if cid == oid:
        return None, "players cannot play against themselves"
    if len(cgames) != len(ogames):
        return None, "two players cannot play different number of games"
    if len(cgames) > 3:
        return None, "cannot play more than three sets"
    if len(cgames) < 2:
        return None, "must play at least two sets"
    cwset = 0
    owset = 0
    for s in set_results(cgames, ogames):
        if s in [(6, 0), (6, 1), (6, 2), (6, 3), (6, 4), (7, 5), (7, 6)]:
            if cwset < 2 and owset < 2:
                cwset = cwset + 1
            else:
                _log.error("spurious set detected #1")
                return None, "third set played after a player already won two sets"
        elif s in [(0, 6), (1, 6), (2, 6), (3, 6), (4, 6), (5, 7), (6, 7)]:
            if cwset < 2 and owset < 2:
                owset = owset + 1
            else:
                _log.error("spurious set detected #2")
                return None, "third set played after a player already won two sets"
        else:
            return None, "invalid set score: {}".format(s)
    _log.info("cwset={}, owset={}".format(cwset, owset))
    if cwset == 2 and owset in [0, 1]:
        return cid, None
    elif owset == 2 and cwset in [0, 1]:
        return oid, None
    else:
        return None, "invalid match score: ({}, {})".format(cwset, owset)
