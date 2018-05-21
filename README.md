# LINZ License Update Script


## Introduction

This is a general purpose script for using the Koordinates python client
to update the licenses of a set of layers within a Koordinates site, created
for LINZ to facilitate migration of data from CCBY-3.0 licenses to CCBY-4.0


## Installation

Initialise a python virtual environment and install dependancies like so:

```
virtualenv venv
. venv/bin/activate
pip install -r requirements.txt
```

This script uses verion 0.4.1 of the [Koordinates Python Client Library](http://koordinates-python.readthedocs.io/en/stable/).


## Running

The script requires a site host (e.g. data.linz.govt.nz), a key with valid permissions, a license ID and
a CSV file with an "ID" column that denotes the IDs of layers to be updated. The script will create and 
publish new versions of the nominated data with the updated license.

Optionally, a `reference` can be supplied (text displayed in the layer's version history) and if `dry_run` 
is provided, no changes are made.

### Example Usage

```
. venv/bin/activate
python license-updater.py --host data.linz.govt.nz --t [key] --license 171 --reference "Licence updated to CCBY 4.0" input-layer-ids.csv
```