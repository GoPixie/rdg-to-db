Import UK Rail data to CSV. Other planned backends are postgresql and mysql ([open-track schema](https://github.com/open-track/dtd2mysql))

[![Build Status](https://travis-ci.org/GoPixie/rdg-to-db.svg?branch=master)](https://travis-ci.org/GoPixie/rdg-to-db)

## Prerequisites

Register with RDG to get login credentials at https://dtdportal.atocrsp.org/ (or http://data.atoc.org/ for the `./download --datadotatoc` option)

```
sudo apt install python3 python3-venv

```
## Setup

```
python3 -m venv .virtual && source .virtual/bin/activate && pip install -r requirements.txt
```
Optionally store RDG username/password:

```
./setup
```


## Data download

run
```
./download
```
to download all available feeds to ./feeds/ subfolder


This will typically result in the following directory structure depending on what feeds you are subscribed to:

 * /rgb-to-db
     * /feeds
         * RJFAF565.ZIP
         * RJTTF634.ZIP
         * RJTTC634.ZIP
         * RJFAC565.ZIP
         * RJRG0472.ZIP
         * .versions

The .versions file holds a record of past downloads and is used to find the most recently downloaded zip file.

Unless otherwise specified in local.cfg ('keep_old' setting), old downloaded ZIP files will be deleted when new files become available

## Applying partial 'update only' files (TODO)

Some files such as `RJTTC634.ZIP` above (note the `C`) contain only changes that are to be applied to the larger `F` ZIP files. This is not currently applied, but is a planned feature.


## Data transform

run
```
./transform
```
to convert files from fixed width format to CSV format and save them in the ./feeds/csv/ subfolder

Conversion is based on definitions found in the [`file-fields.json`](file-fields.json) file which is in turn transcribed from definitions found in RDG documents [SP0035](https://www.raildeliverygroup.com/our-services/rail-data/fares-data.html) (fares), [RSPS5046](https://www.raildeliverygroup.com/our-services/rail-data/timetable-data.html) (timetables) & [RSPS5047](https://www.raildeliverygroup.com/our-services/rail-data/routeing-guide-data.html) (routeing guide).

run
```
./transform --target=postgresql
```
to transfer CSV files to a PostgreSQL database and create some useful views.

Tables are created with primary keys taken from [`field-pks.json`](field-pks.json) and are populated directly from CSV files using the fast postgresql COPY command.  Views built on top of the raw table make use of PostgreSQL [daterange](https://www.postgresql.org/docs/9.2/static/rangetypes.html) for start_date/end_date pairs, and denormalize data from adjunct table into sql arrays. See [`model.py`](model.py) for an example of how the route_code view can be accessed through Python/[SqlAlchemy](http://www.sqlalchemy.org/).


## TODO

 - Partial 'update only' files
 - Set of minimal test ZIP files containing records for each record type
 - mysql backend for ([open-track schema](https://github.com/open-track/dtd2mysql))
 - database functions or views which [calculate UK Fares](https://github.com/open-track/fares-service-php/wiki/Fare-Lookup) for a given origin/destination pair!

## Contributing

Pull requests and updates to [`file-fields.json`](file-fields.json) very welcome. New backends can be added by creating something similar to `csv.py` in [/targets/](targets) (and updating imports at [/targets/__init__.py](targets/__init__.py))

Test syntax according to .editorconfig and [pep8](https://www.python.org/dev/peps/pep-0008/):

    pip install flake8
    npm install -g eclint

    flake8 $( git grep -l '^#!/usr/bin/env python3' && git ls-files '*.py' ) --max-line-length=99
    eclint check --indent_size -1 $( git ls-files )
