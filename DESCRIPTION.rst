J.I.M. -- Jim Improved and Modernized
=====================================
  
This is a web-based match processing system for the ATTTC Tennis
Club, which was founded by Jim Milloy.  This system is
intended to replace an old Fox-Pro system that Jim has been using
to process results.  Hence, the name J.I.M., for "Jim Improved and
Modernized".

Background
----------

This code was written to replace an aging system that was used to score
matches and rank tennis players in a local tennis league.  The league is
called ATTTC and it draws its origins from the good old AT&T days.  It
originally gathered tennis players who worked (or used to work) for AT&T in
Northern New Jersey.  Many years (and many spin-offs and mergers) later, the
league is still alive and kicking, but it now gathers players from all
companies in the area that can be traced back to the original AT&T.  The
original name has changed from "AT&T Tennis Club", to "A Truly Terrific
Tennis Club" (ATTTC in both cases) and new generations of players have
joined us.

The software that was used to process matches and rank players stopped
working on modern machines, so we decided to write a new one from
scratch.  The system is written as a web application and to run it,
all you need is a Linux machine with a network connection to act as a
server and a web browser to interact with the system.  More likely,
you will want to install the server on an instance in the Amazon cloud
(or a similar service).

License
-------

Unless indicated otherwise, the code in this repository is licensed
under the MIT license. See `LICENSE.txt` file for details.

Installation
------------

### Ubuntu
The installation instructions assume that you are using Ubuntu,
though it should be straightforward to adapt it to any other
distribution.  First, you will need several packages (install them
using the `apt-get install` command): `git`, `libffi-dev`,
`python-dev`, `python-virtualenv`, `python-pip`, `sqlite3`.  You
can also install `python-tornado`, but if you don't it will be
pulled by `pip` as a dependency (there are several other Python
packages that `pip` will pull or update at installation time).

The code is written for Python 2, so make sure that it is available
on your system (it typically is on all versions of Ubuntu).

### Fedora
For Fedora 24, use

  dnf install git gitk python-pip python2-virtualenv

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

   `~/jim_env/lib/python2.7/site-packages/jim/jim.cfg`

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
a real (signed) certificate, which is explained in the next subsection.

### Deployment

For real deployment (whether an official site for use with ATTTC or for experimentation
and pre-deployment testing) you will need a machine to host the service. This section
will assume that the host is an Amazon Web Services (AWS) cloud instance, but the same
instructions will work with any other hosting provider or on a dedicated private
machine with permanent Internet connection.

If deploying on an Amazon Cloud platform, create an AWS instance (use
Ubuntu image) and follow these instructions.

1. Install prerequisite packages (see the previous section).

2. Become `root`:

   `sudo su -`

3. Install the J.I.M. package:

   `pip install git+https://github.com/ihadzic/jim.git`

   Note that this time you are not installing into a virtual environment but as a system-wide
   installation, which is the reason why you had to become `root` in the previous step.

   The installed files will be in the following directories:

   `static HTML: /usr/local/var/jim/html`

   `HTML templates: /usr/local/var/jim/templates`

4. Create the directory for the database:

   `mkdir /usr/local/var/jim/database/`

5. Create the configuration file in `/etc/jim.cfg` and populate it with the following content:

    ```
    [web]
    http_port = <set_the_http_port>
    https_port = <set_the_https_port>
    html_root = /usr/local/var/jim/html
    template_root = /usr/local/var/jim/templates
    bootstrap_token = <set_the_bootstrap_token>
    certs_path = /usr/local/var/jim/certs

    [db]
    db_file = /usr/local/var/jim/database/jim.db
    news_file = /usr/local/var/jim/database/news.txt
    ```

6. Register the domain name for your service with your favorite DNS provider. If you decide
   to skip this step, you can still use the service by specifying the IP address,
   but you will also have to use a self-signed certificate because you cannot go through
   the signing process without the registered domain.

7. Obtain signed SSL certificates and put them in `/usr/local/var/jim/certs`. The private key
   file must be called `key.pem` (please do not use the pass phrase) and the site certificate
   must be called `cert.pem`. The signing process is specific to the Certificate Authority
   (CA) from which you will be getting the certificate, but in the process you will have to
   generate the Certificate (see the README.txt file in the directory) followed by generating
   the Certificate Signing Request file (CSR) and submit it to CA which will provide
   the signed certificate to you. You can decide to skip the signing process and use
   self-signed certificates, but then you will have to add the security exception
   in your browser or use cleartext (http) connections. The latter should be done only
   for testing and experimentation.

8. Set up the network rules in AWS dashboard such that at least `https` port is open and
   routed to the correct port on your instance. You can also open up the `http` port, but
   only if your instance is used for testing and experimentation. The official system should
   not accept cleartext connections.

9. You are now ready to run the service, just type (as root):

   `jim`

   and the service will start in the background and run as a daemon (the lack of the `-n`
   option will make the service run as a daemon). If you prefer to run the service
   as a non-privileged user (instead of as `root`) then you have to make sure that
   all files under `/usr/locatl/var/jim` are owned by the user that will own the service
   and you cannot use the privileged TCP port (80 for `http` and 443 for `https`).
   You can still set up the network rules in AWS dashboard to translate the incoming
   privileged port to a non-privileged.

10. To verify that the service is running look at the system log using `journalctl` command.
    You should see the log messages from the service.

11. Optionally, add starting of tje `jim` service to boot scripts so that it comes back
    up if you reboot the instance.


Usage
-----

When you bring up the service for the first time, you should point your browser
to the site and do the bootstrap login. Log in using `bootstrap` for username
and the bootstrap token that you selected in the configuration file
for the password.

After you log in, you should immediately select "Manage Admins" and create an
administrator account. After the first administrator account is created
you the `bootstrap` login will be automatically disabled. The `bootstrap`
login is a one-time backdoor until the first administrator account is created.

If you delete all administrator accounts, the `bootstrap` login will start to
work again, but in general you should avoid doing that.

There are two types of users. Administrator (which you have just created
if you are following these instructions) is a user that cannot play matches
(and thus is not included in the ladder), but can enter matches and player
information for any player, add players, delete players, etc. Player is a
regular user that plays matches and shows on the ladder. Players cannot enter
matches for others and can modify only their own data (TODO: this feature
has not been implemented yet). Players can also view the ladder, matches, and
roster. Initially, players have accounts only to see the ladder and roster,
while matches are still reported using the old way (E-mail to administrator).
Later, the plan is to allow players to enter their own matches.

If you are just testing the system, create one administrator and log in as
that user.  You will get the menu of operations that an administrator can
perform.  Explore the system and add a few players (regular users) and add some
matches.  Watch the ladder change as you enter matches.  Now log out and log
in as a player.  You will see a more limited set of options and fewer menus. 
The interface should be intuitive and entering players and matches should be
straightforward.

Development
-----------

The easiest environment to do the development in is to run everything on
a local machine in your home directory using the Python virtual environment.
After making (and possibly commiting to Git) code changes (add a feature,
fix a bug, etc.), upgrade the installation using `pip`. Type this in the top
of your source code directory in your virtual environment:

`pip install --upgrade .`

This will update the installation as well as the dependency packages. If you are not
on the network and you know that you have all dependencies already installed you can
type this instead:

`pip install --upgrade --no-dependencies .`

Run the `jim` executable in the foreground:

`jim -n`

and point the browser to `https://localhost:<port>`. If you are using default configuration,
the system will look for the database file in the current working directory. So make
sure that you always run the executable in the same directory. Otherwise a new
empty database will be created when you run.

Once you are ready to deploy your changes to a public server, `ssh` to the server
and `pip install --upgrade` the code on the server. Restart the `jim` daemon following
the upgrade.

Guidelines for Contributing
---------------------------

If you plan to contribute to this code (whether or not you play tennis in the ATTTC league),
here are some guidelines you should adhere to.

### License

The code in this repository is licensed under MIT License, so please make sure that you
understand its terms and any implications it may have on the distribution
of the code that you are contributing. I am not a lawyer and cannot provide any legal
advice.

Any patch that you contribute must include the "Signed-off-by: Your Name <your@email>"
line at the end. What that means is that you should type `git commit -s` when committing
your code. By including the "Signed-off-by" you are making a statement that you
either own the code that you are contributing (i.e., you are the original author)
or that you received it from an original author or a third party under license terms
that allow you to distribute it or contribute it to an MIT-licensed open-source project.
This is a normal practice in most free and open-source projects and should come as no
surprise to anyone who has worked on community software development.

If you write software for a living, it is your responsibility to make sure that your
employer has no objection to you contributing to a public open-source project on your
own time. In most cases your contributions will be your own (i.e., hobby-contributions)
and not of your employer, so unless you have explicitly permission from your company,
the "Author" line of your patches should identify you as a private individual, not as
an employee of your company. This further means that you should use your personal
E-mail for all patches, not your work E-mail. Different companies have different
policies with regard to their employees contributing to public projects (even if
it is on their own time), so if in doubt check. At the end of the day, it is your
responsibility, not mine.

### Coding Practices

Short version: Please keep it simple and stupid (KISS) and be neat!

Long version: This system is no rocket science.  It is not meant to serve
half a billion users nor push terabytes of data to the world.  It's a simple
database-101 project married with a web front-end.  So simple, working, and
easy-to-follow is more important than fancy.  No need for three dozen
frameworks and a pile of hyped-up technologies.  If you look at the code,
you will notice that it's very simple: Python + Tornado + SQLite at the
server side and hand-crafted HTML and Javascript at the client side.  I
don't even bother using asynchronous methods in Tornado, not because I don't
know them (I do), but because the expected traffic does not justify doing
anything fancier.

Please be neat and tidy.  This applies to the code itself and to patches as
a series of changes to the code.  You are using Git, which allows you to
commit things locally, and rework and tidy-up your patches before sending
the pull request.

One patch must change one small logical unit and must be accompanied by a meaningful
commit message that explains what the patch is about. The commit message must be in
canonical format:

```
affected unit: short message

elaborate message that explains the what's, why's,
and hows (unless the patch is trivial and obvious)

Signed-off-by: Your Name <your@email>
```

A monster-patch that contains a dozen unrelated changes accompanied with a
meaningless commit message, such as "my latest stuff from Monday, it works!"
is not very useful for other contributors and I won't merge it.

You should never mix the cleanup work with substance work. Do the cleanup
in a separate patch and then follow with the substance. If, as part
of your work you need to refactor or rework some functions, do the rework
in a series of preparatory function-neutral patches and then follow with
a patch that changes the actual function. This makes reviewing the
code easier, because your friendly integrator can focus on one small
patch when trying to understand what you are doing instead of looking
at one monster-patch that touches every single file with dozen unrelated
changes.

The size of the patch should be the smallest that makes sense, but you should
avoid changes that completely break the build or ability to run. It is a normal
part of development to inadvertently introduce bugs, but intentional break
such as changing the function signature without reconciling with the callers
(in the same patch) is bad. Such a practice completely defeats the ability to
bisect the tree if we are searching for a regression, so please don't do it.
In other words, each patch should be the minimum set of changes that
achieves transitive closure of the dependency graph.

The order of patches matters. If, for example, you need to modify the
database schema, introduce a new function in the backend, modify the
code to use the new function, and add stuff to front-end to give user
the access to the new feature, then do it in that order and make the
database schema upgrade a separate patch, from implementation of the
new function, which is a separate patch from caller rework, which in
turn is the separate patch from front-end rework. If, in this example,
you pick the opposite order, you may be forced to either intentionally
break the build and existing functionality or bundle everything into
one monster-patch.

If, while working on a feature, you stumble upon something unrelated
that's broken and decide to fix it, while you are at it, please do not
bundle the fix into the rest of your work. Make the fix a separate patch
unless your main work is already modifying the affected section
of the code. Use 'git add -p' to selectively stage hunks that logically
belong to different patches.

People who come from an SVN or a CVS background may find this practice
burdening and may even question its merits. The problem is that being
a centralized system, SVN or CVS institute a fear that if you commit
something you will break everyone else. That encourages postponing
the commit until everything is tested and verified, which in turns
forces the user to create massive monster-commits that nobody
(not even the author) can figure out what they actually include.
Searching for regression is a nightmare in such an environment.
In Git, you cannot break anyone except yourself and you can amend
and cleanup patches as many times as you want before your stuff
is merged. So take advantage of it. In SVN or CVS, the system forces
you to be messy. In Git, being messy or tidy is solely the result
of your own merits.
