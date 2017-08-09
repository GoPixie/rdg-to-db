Import UK Rail data to CSV. Other planned backends are postgresql and mysql ([open-track schema](https://github.com/open-track/dtd2mysql))

[![Build Status](https://travis-ci.org/GoPixie/rdg-to-db.svg?branch=master)](https://travis-ci.org/GoPixie/rdg-to-db)

## Prerequisites

Register with RDG to get login credentials at https://dtdportal.atocrsp.org/ (or http://data.atoc.org/)

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
         * RJFA-FULL-LATEST.ZIP
         * RJTTF634.ZIP
         * RJTT-FULL-LATEST.ZIP
         * RJTTC634.ZIP
         * RJFAC565.ZIP
         * RJRG0472.ZIP
         * RJRG-FULL-LATEST.ZIP

The 'FULL-LATEST' versions are hard links that always point to the most recently downloaded zip file.

## Applying partial 'update only' files (TODO)

Some files such as `RJTTC634.ZIP` above (note the `C`) contain only changes that are to be applied to the larger `F` ZIP files. This is not currently applied, but is a planned feature.


## Data transform

run
```
./transform
```
to convert files from fixed width format to CSV format and save them in the ./feeds/csv/ subfolder

Conversion is based on definitions found in the [`file-fields.json`](file-fields.json) file which is in turn transcribed from definitions found in RDG documents [SP0035](https://www.raildeliverygroup.com/our-services/rail-data/fares-data.html) (fares), [RSPS5046](https://www.raildeliverygroup.com/our-services/rail-data/timetable-data.html) (timetables) & [RSPS5047](https://www.raildeliverygroup.com/our-services/rail-data/routeing-guide-data.html) (routeing guide).


## TODO

 - Partial 'update only' files
 - Set of minimal test ZIP files containing records for each record type
 - mysql backend for ([open-track schema](https://github.com/open-track/dtd2mysql))
 - postgresql backend using [daterange](https://www.postgresql.org/docs/9.2/static/rangetypes.html) and denormalizing output
 - database functions or views which [calculate UK Fares](https://github.com/open-track/fares-service-php/wiki/Fare-Lookup) for a given origin/destination pair!

## Contributing

Pull requests and updates to [`file-fields.json`](file-fields.json) very welcome. New backends can be added by creating something similar to `csv.py` in [/targets/](targets) (and updating imports at [/targets/__init__.py](targets/__init__.py))

Test syntax according to .editorconfig and [pep8](https://www.python.org/dev/peps/pep-0008/):

    pip install flake8
    npm install -g eclint

    flake8 $( git grep -l '^#!/usr/bin/env python3' && git ls-files *.py ) --max-line-length=99
    eclint check $( git ls-files )
