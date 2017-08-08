Import UK Rail data to a Postgresql Backend

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
