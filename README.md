Import UK Rail data to a Postgresql Backend

## Prerequisites

Register with RDG to get login credentials at http://data.atoc.org/

```
sudo apt install python3 python3-venv

```
## Setup

```
python3 -m venv .virtual && source .virtual/bin/activate && pip install -r requirements.txt
```

## Data download

run
```
./download_raw
```
to download and unzip fares feed to ./feeds/fares subfolder