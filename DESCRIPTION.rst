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

Install using pip. You may also need to install python-dev
and libffi-dev packages. On Ubuntu install as:

apt get install libffi-dev

apt get install python-dev

