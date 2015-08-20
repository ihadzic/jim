import logging

_log = logging.getLogger("rules")

def set_results(cgames, ogames):
    for i in range(0, len(ogames)):
        yield (cgames[i], ogames[i])

# Rule 6.1: Winner receives 30 points.
def winner_points():
    return 30

# Rule 6.2: Loser receives a minimum of 5 points or up to a maximum of 20 points
# calculated as follows
#    Game points      - 2 points for each game won.
#    Challenge points - 2 points for a challenge resulting in a completed
#                         match, if the loser was the challenger.
def loser_points(games_won, challenge_points = False):
    points = 2 * sum(games_won) + (2 if challenge_points else 0)
    if points > 20:
        points = 20
    if points < 5:
        points = 5
    return points

def process_match(cid, oid, cgames, ogames):
    if cid == oid:
        return None, None, None, "players cannot play against themselves"
    if len(cgames) != len(ogames):
        return None, None, None, "two players cannot play different number of games"
    if len(cgames) > 3:
        return None, None, None, "cannot play more than three sets"
    if len(cgames) < 2:
        return None, None, None, "must play at least two sets"
    cwset = 0
    owset = 0
    for s in set_results(cgames, ogames):
        if s in [(6, 0), (6, 1), (6, 2), (6, 3), (6, 4), (7, 5), (7, 6)]:
            if cwset < 2 and owset < 2:
                cwset = cwset + 1
            else:
                _log.error("spurious set detected #1")
                return None, None, None, "third set played after a player already won two sets"
        elif s in [(0, 6), (1, 6), (2, 6), (3, 6), (4, 6), (5, 7), (6, 7)]:
            if cwset < 2 and owset < 2:
                owset = owset + 1
            else:
                _log.error("spurious set detected #2")
                return None, None, None, "third set played after a player already won two sets"
        else:
            return None, None, None, "invalid set score: {}".format(s)
    _log.info("cwset={}, owset={}".format(cwset, owset))
    if cwset == 2 and owset in [0, 1]:
        # challenger won
        return cid, winner_points(), loser_points(ogames, False), None
    elif owset == 2 and cwset in [0, 1]:
        # opponent (non-challenger) won
        # TODO: if challenger retired do not credit challenge points
        return oid, loser_points(cgames, True), winner_points(), None
    else:
        return None, None, None, "invalid match score: ({}, {})".format(cwset, owset)
