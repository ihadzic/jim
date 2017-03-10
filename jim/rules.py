#!/usr/bin/env python2
#
# Copyright (c) 2016, Ilija Hadzic <ilijahadzic@gmail.com>
#
# MIT License, see LICENSE.txt for details

import util
from datetime import datetime

_log = None

def init():
    global _log
    _log = util.get_syslog_logger("rules")

def set_results(cgames, ogames):
    assert len(ogames) == len(cgames)
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

# Rule 6.4: No Shows - If a player does not show up for a match within 15 minutes of
# the scheduled start time, the opponent wins the match by forfeit and should
# report the match as a 6-0, 6-0 victory, with a check mark in the space
# provided on the match report form to indicate that it was a forfeit. The non-showing
# person will not be awarded any points but will be charged with one loss.
# The person who showed up will be awarded 30 points and one win. There will be no
# between ladder movement as a result of this match report.
def process_forfeit(cid, oid, cgames, ogames):
    if len(cgames) != 2:
        return None, None, None, "forfeited match score must have exactly two sets"
    elif cgames[0] == 6 and ogames[0] == 0 and cgames[1] == 6 and ogames[1] == 0:
        # challenger won by forfeit
        return cid, 30, 0, None
    elif cgames[0] == 0 and ogames[0] == 6 and cgames[1] == 0 and ogames[1] == 6:
        # opponent won by forfeit
        return oid, 0, 30, None
    else:
        return None, None, None, "forfeited match score must be 6-0, 6-0"

def process_match(cid, oid, cgames, ogames, retired = False, forfeited = False, date = None, tournament = False):
    # TODO: tournament flag is just a placeholder for now
    if not date:
        date = datetime.now()
    if date > datetime.now():
        return None, None, None, "match date cannot be in the future"
    if cid == oid:
        return None, None, None, "players cannot play against themselves"
    if len(cgames) != len(ogames):
        return None, None, None, "two players cannot play different number of games"
    if len(cgames) > 3:
        return None, None, None, "cannot play more than three sets"
    if len(cgames) < 2:
        return None, None, None, "must play at least two sets"
    if forfeited and retired:
        return None, None, None, "cannot retire and forfeit at the same time"
    cwset = 0
    owset = 0
    if forfeited:
        return process_forfeit(cid, oid, cgames, ogames)
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
        # challenger points credited to loser only if match completed
        if retired:
            return oid, loser_points(cgames, False), winner_points(), None
        else:
            return oid, loser_points(cgames, True), winner_points(), None
    else:
        return None, None, None, "invalid match score: ({}, {})".format(cwset, owset)

# Rule 4.2.4
# - No more than 3 of your first 9 matches may be against the same opponent.
# - After the first 9 matches no more that 1/3 of your matches may be against
#   the same opponent.
def match_limit_reached(p1_vs_p2, p1, p2):
    if p1 < 9:
        if p1_vs_p2 > 3:
            return True
    elif p1_vs_p2 * 3 > p1:
            return True
    if p2 < 9:
        if p1_vs_p2 > 3:
            return True
    elif p1_vs_p2 * 3 > p2:
            return True
    return False

# Rule ?
#
# At the beginning of the season, the players are given
# points that reflect their rank in the previous season
def get_init_points(active_players, prev_season_ladder):
    # intersect_players_id_list contains the sorted list of player IDs that
    # are active in this season and have played in the previous season;
    # the list is sorted by the previous season rankings
    active_players_id_list = [ player.get('id') for player in active_players ]
    intersect_players_id_list = [ player.get('player_id') for player in prev_season_ladder if player.get('player_id') in active_players_id_list ]
    max_points = len(intersect_players_id_list)
    assigned_points = [(max_points - util.min_or_default([i for i in range(len(intersect_players_id_list)) if intersect_players_id_list[i] == player_id], max_points)) for player_id in active_players_id_list]
    return assigned_points
