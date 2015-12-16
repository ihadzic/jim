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
ALTER TABLE players ADD COLUMN initial_points NOT NULL DEFAULT 0;
UPDATE players SET initial_points = points;
