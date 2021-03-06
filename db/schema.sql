/*
 * Version 1
 * Only revisions table
 */
CREATE TABLE revisions (id INTEGER PRIMARY KEY NOT NULL, date DATE, comment TEXT);
INSERT INTO revisions (date, comment) VALUES (date("now"), "empty database");

/*
 * Version 2
 * Add the players table
 */
CREATE TABLE players (id INTEGER PRIMARY KEY  NOT NULL, last_name TEXT, first_name TEXT, username TEXT UNIQUE, password_hash TEXT, password_seed TEXT, cell_phone TEXT, home_phone TEXT, work_phone TEXT, email TEXT, company TEXT, ladder TEXT, active BOOL NOT NULL  DEFAULT false, points INTEGER NOT NULL  DEFAULT 0);
INSERT INTO revisions (date, comment) VALUES (date("now"), "add players");

/*
 * Version 3
 * Add field for tracking initial points only
 */
ALTER TABLE players ADD COLUMN initial_points INTEGER NOT NULL DEFAULT 0;
UPDATE players SET initial_points = points;
INSERT INTO revisions (date, comment) VALUES (date("now"), "add init_points column");

/*
 * Version 4
 * Add wins, losses, ladder_wins, and ladder_losses fields
 */
ALTER TABLE players ADD COLUMN wins INTEGER NOT NULL DEFAULT 0;
ALTER TABLE players ADD COLUMN losses INTEGER NOT NULL DEFAULT 0;
ALTER TABLE players ADD COLUMN ladder_wins INTEGER NOT NULL DEFAULT 0;
ALTER TABLE players ADD COLUMN ladder_losses INTEGER NOT NULL DEFAULT 0;
INSERT INTO revisions (date, comment) VALUES (date("now"), "add wins and losses count");

/*
 * Version 5
 * Add admin accounts
 */
CREATE TABLE admins (id INTEGER PRIMARY KEY NOT NULL, username TEXT, password_hash TEXT);
INSERT INTO revisions (date, comment) VALUES (date("now"), "add admin account table");

/*
 * Version 6
 * Add matches
 */
PRAGMA foreign_keys = ON;
CREATE TABLE matches (id INTEGER PRIMARY KEY NOT NULL, challenger_id INTEGER NOT NULL REFERENCES players(id), opponent_id INTEGER NOT NULL REFERENCES players(id), winner_id INTEGER NOT NULL REFERENCES players(id), cpoints INTEGER NOT NULL, opoints INTEGER NOT NULL, cgames TEXT NOT NULL, ogames TEXT NOT NULL, date DATE NOT NULL, tournament BOOL NOT NULL DEFAULT FALSE, retired BOOL NOT NULL DEFAULT FALSE, forfeited BOOL NOT NULL DEFAULT FALSE);
INSERT INTO revisions (date, comment) VALUES (date("now"), "add matches table");

/*
 * Version 7
 * Each player needs separate win/loss counter for each ladder
 * Obsoletes ladder_wins and ladder_losses columns
 */
ALTER TABLE players ADD COLUMN a_wins INTEGER NOT NULL DEFAULT 0;
ALTER TABLE players ADD COLUMN a_losses INTEGER NOT NULL DEFAULT 0;
ALTER TABLE players ADD COLUMN b_wins INTEGER NOT NULL DEFAULT 0;
ALTER TABLE players ADD COLUMN b_losses INTEGER NOT NULL DEFAULT 0;
ALTER TABLE players ADD COLUMN c_wins INTEGER NOT NULL DEFAULT 0;
ALTER TABLE players ADD COLUMN c_losses INTEGER NOT NULL DEFAULT 0;
INSERT INTO revisions (date, comment) VALUES (date("now"), "separate win/loss counter for each ladder");

/*
 * Version 8
 * Match needs ladder information associated with it.
 */
ALTER TABLE matches ADD COLUMN ladder TEXT;
INSERT INTO revisions (date, comment) VALUES (date("now"), "add ladder to match entry");

/*
 * Version 9
 * Add matches view augmented with player names
 */
CREATE VIEW matches_with_names as select matches.*, p1.last_name, p2.last_name from matches join players p1 on p1.id = matches.challenger_id join players p2 on p2.id = matches.opponent_id;
INSERT INTO revisions (date, comment) VALUES (date("now"), "added matches view with player names");

/*
 * Version 10
 * Add seasons table
 */
CREATE TABLE seasons (id INTEGER PRIMARY KEY NOT NULL, title TEXT UNIQUE, start_date DATE, end_date DATE, active BOOL NOT NULL DEFAULT FALSE);
INSERT INTO seasons (title, active) VALUES ("default test season", 1);
ALTER TABLE matches ADD COLUMN season_id INTEGER REFERENCES seasons(id);
UPDATE matches set season_id=1;
INSERT INTO revisions (date, comment) VALUES (date("now"), "added seasons");

/*
 * Version 11
 * Add playerarchive table
 */
CREATE TABLE player_archive (id INTEGER PRIMARY KEY  NOT NULL, season_id INTEGER REFERENCES seasons(id), player_id INTEGER REFERENCES players(id), ladder TEXT, active BOOL NOT NULL  DEFAULT false, points INTEGER NOT NULL  DEFAULT 0, initial_points NOT NULL DEFAULT 0, wins INTEGER NOT NULL DEFAULT 0, losses INTEGER NOT NULL DEFAULT 0, a_wins INTEGER NOT NULL DEFAULT 0, a_losses INTEGER NOT NULL DEFAULT 0, b_wins INTEGER NOT NULL DEFAULT 0, b_losses INTEGER NOT NULL DEFAULT 0, c_wins INTEGER NOT NULL DEFAULT 0, c_losses INTEGER NOT NULL DEFAULT 0);
INSERT INTO revisions (date, comment) VALUES (date("now"), "added player_archive");

/*
 * Version 12
 * Add tokens table
 */
CREATE TABLE tokens (id INTEGER PRIMARY KEY NOT NULL, token TEXT NOT NULL, type TEXT NOT NULL, expires DATE NOT NULL, since DATE);
INSERT INTO revisions (date, comment) VALUES (date("now"), "added tokens table");

/*
 * Version 13
 * Add user location
 */
ALTER TABLE players ADD COLUMN location TEXT;
ALTER TABLE players ADD COLUMN note TEXT;
INSERT INTO revisions (date, comment) VALUES (date("now"), "added note and location");

/*
 * Version 14
 * Add user location
 */
ALTER TABLE players ADD COLUMN wlocation TEXT;
INSERT INTO revisions (date, comment) VALUES (date("now"), "added work location");

/*
 * Version 15
 * Add tournament qualification flag
 */
ALTER TABLE players ADD COLUMN tournament_qualified_override INTEGER NOT NULL DEFAULT 0;
ALTER TABLE player_archive ADD COLUMN tournament_qualified_override INTEGER NOT NULL DEFAULT 0;
INSERT INTO revisions (date, comment) VALUES (date("now"), "fields needed for tournament qualification");

/*
 * Version 16
 * Add tournament qualification criteria
 */
ALTER TABLE seasons ADD COLUMN tournament_date DATE;
ALTER TABLE seasons ADD COLUMN tournament_min_matches INTEGER NOT NULL DEFAULT 9;
ALTER TABLE seasons ADD COLUMN tournament_min_opponents INTEGER NOT NULL DEFAULT 5;
INSERT INTO revisions (date, comment) VALUES (date("now"), "more fields needed for tournament qualification");

/*
 * Version 17
 * Add promotion dates
 */
ALTER TABLE players ADD COLUMN a_promotion DATE;
ALTER TABLE players ADD COLUMN b_promotion DATE;
ALTER TABLE players ADD COLUMN c_promotion DATE;
INSERT INTO revisions (date, comment) VALUES (date("now"), "add ladder promotion dates");

/*
 * Version 18
 * Add pending and disputed flags for matches
 */
ALTER TABLE matches ADD COLUMN disputed BOOL NOT NULL DEFAULT FALSE;
ALTER TABLE matches ADD COLUMN pending BOOL NOT NULL DEFAULT FALSE;
INSERT INTO revisions (date, comment) VALUES (date("now"), "add disputed and pending flags");

/*
 * Version 19
 * Add previous season id, needed to calculate the initial points
 */
ALTER TABLE seasons ADD COLUMN prev_id INTEGER;
INSERT INTO revisions (date, comment) VALUES (date("now"), "add previous season id to the seasons table");

/*
 * Version 20
 * Add 'kicked' flag to the seasons table
 */
ALTER TABLE seasons ADD COLUMN kicked NOT NULL DEFAULT TRUE;
INSERT INTO revisions (date, comment) VALUES (date("now"), "add kicked flag to the seasons table");
