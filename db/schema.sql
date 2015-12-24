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
