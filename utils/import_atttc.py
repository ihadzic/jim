#!/usr/bin/env python2

import csv
import string
import sys
import sqlite3

if len(sys.argv) < 3:
    print("not enough args")
    exit(1)

infile=sys.argv[1]
database=sys.argv[2]

print("using file {}".format(infile))
print("using database {}".format(database))

players = []

def to_phone(p):
    if p[0] == '1':
        p = p[1:]
    p = p.replace(' ', '-').split('-')
    p = string.join(p, '')
    return "{}-{}-{}".format(p[0:3], p[3:6], p[6:])
        
db_handle = sqlite3.connect(database)
db = db_handle.cursor()

def add_player(player):
    # TODO for now we manually add new players
    pass

with open(infile) as csvfile:
    atttc_reader = csv.reader(csvfile, delimiter=',')
    header = atttc_reader.next()
    for row in atttc_reader:
        player = {
            'first_name': row[1].split()[0],
            'last_name' : string.join(row[1].split()[1:]),
            'email' : row[2].lower(),
            'company' : row[3].split()[0],
            'cell_phone': to_phone(row[5]),
            'username': row[9],
            'ladder': row[8].lower()
        }
        db.execute('SELECT id FROM players WHERE username=?', (player['username'],))
        v = db.fetchall()
        if len(v) == 0:
            db.execute('SELECT id FROM players where first_name=? AND last_name=?',
                       (player['first_name'], player['last_name']))
            v = db.fetchall()
            if len(v) == 0:
                db.execute('SELECT id FROM players where email=?',
                           (player['email'],))
                v = db.fetchall()
                if len(v) == 0:
                    print("new player: {} {} ({})".format(player['first_name'], player['last_name'], player['username']))
                    add_player(player)
                    continue
        player_id = v[0][0]
        db.execute('SELECT ladder,cell_phone,email from players where id=?', (player_id,))
        v = db.fetchall()
        if v[0][0] != player['ladder']:
            print('{}: wrong ladder {} should be {}'.format(player['first_name'], player['ladder'], v[0][0]))
        if v[0][1] != player['cell_phone']:
            print('{}: new cell phone {}->{}'.format(player['first_name'], v[0][1],player['cell_phone']))
            db.execute("UPDATE players SET cell_phone=? WHERE id=?", (player['cell_phone'], player_id))
        if v[0][2] != player['email']:
            print('{}: new email {}->{}'.format(player['first_name'],v[0][2],player['email']))
            db.execute('UPDATE players SET email=? WHERE id=?', (player['email'], player_id))
        db.execute("UPDATE players SET company=? WHERE id=?", (player['company'], player_id))
        db.execute("UPDATE players SET active=1 WHERE id=?", (player_id,))
        db_handle.commit()
