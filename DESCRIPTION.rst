J.I.M. -- Jim Improved and Modernized
=====================================

This is a web-based match processing system for ATTTC tennis club
founded by Jim Milloy. It is intended to replace old Fox-Pro
system that Jim uses to process results. Hence, the name
J.I.M for Jim Improved and Modernized.

Background
----------

I wrote this code to replace the aging system used to score
matches and rank tennis players in the tennis league that
I play in. The league is called ATTTC and it draws origins from
good old AT&T. It originally gathered tennis players who worked
(or used to work) for AT&T in Northern NJ at the time.
Many years (and many spin-offs and mergers) later, the league is still
alive and kicking, but it now gathers players from all companies in the
area that can be traced back to original AT&T. The original name has
changed from "AT&T Tennis Club", to "A Truly Terrific Tennis Club"
(ATTTC in both cases) and new generations of players have joined us.

The software that was used to process matches and rank players stopped
working on modern machines, so I decided to write a new one from scratch.
It is written as a web application and to run it, all you need is a Linux
machine with a network connection to act as a server and a web browser
to interact with the system. More likely, you will want to install
the server on an instance in the Amazon cloud (or similar service).

Installation
------------

The installation instructions assume that you are using Ubuntu, though
it should be straight forward to adapt it to any other distribution.
First, you will need several packages (install them using `apt-get install`
command): `libffi-dev`, `python-dev`, `python-virtualenv`, `python-pip`,
`sqlite3`. You can also install `python-tornado`, but if you don't it
will be pulled by `pip` as a dependency (there are several other Python
packages that `pip` will pull or update at installation time).

The code is written for Python 2, so make sure that it is available on your
system (it typically is on all versions of Ubuntu).

### Development and Testing

For development and testing, it is easiest to use Python virtual environment and
run the code as as a foreground process in your terminal window. First do the one-time
setup:

1. Clone the repository:

   `git clone https://github.com/ihadzic/jim.git`

2. Setup the virtual environment in your home directory:

   `virtualenv ~/jim_env`

   If your system has both Python 2 and Python 3 installed, then make sure you create an environment
   for Python 2 using `-p python2` option.

3. Activate the virtual environment:

   `. ~/jim_env/bin/activate`

4. Install using `pip`

   `cd jim/`
   `pip install .`

Here, we assumed that `jim/` is the directory into which you cloned the repository.

5. Edit this file and customize any parameters as you see fit:

   `~jim_env/lib/python2.7/site-packages/jim/jim.cfg`

   Note that if you want to run it as a regular user, you must use TCP ports above
   1024 (non privileged ports) and the path to the database file must be writable
   by the user that you want to run as. By default, the path to the database is
   is relative to the current working directory, so if you leave it like that
   then make sure you always run the tests in the same directory (otherwise you
   will end up creating a new database for each directory in which you run).

6. Fire it up in the foreground:

   `jim -n`

   When you run for the first time, you will see a lot of messages fly by (most
   of them will be the SQL commands as it creates the database schema), but it should
   finish with this message:

   `INFO:web:starting server loop`

7. Try if it works by pointing your browser to:

   `https://localhost:<https_port>`

   Where `<https_port>` is the TCP port that you picked when you edited the configuration file.
   Alternatively you can use `http` (cleartext) connection along with the TCP port that you
   specified in the configuration file for `http` connections.

You should see the login screen and the server and a bunch of log messages in the terminal
window. If you get to this point, your service works! We will explain the usage in subsequent
sections.

Note that if you are using `https` connection, the certificates will be invalid and you
will have to accept the security exception. This is because the default certificate
(located in `certs/` directory and installed under `<environment>/var/jim/certs/`) is
just a self-singed placeholder. In real deployment you will have to obtain and install
real (signed) certificate, which is explained in the next subsection.

### Deployment (using AWS)

TODO


Usage
-----

TODO

Development
-----------

Guidelines for Contributing
---------------------------
