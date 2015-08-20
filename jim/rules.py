def process_match(cid, oid, cgames, ogames):
    if cid == oid:
        return None, "players cannot play against themselves"
    if len(cgames) != len(ogames):
        return None, "two players cannot play different number of games"
    if len(cgames) > 3:
        return None, "cannot play more than three sets"
    if len(cgames) < 2:
        return None, "must play at least two sets"
    # TODO: really process the match
    return 42, None
