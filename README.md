# Knesset data pipelines

[![Build Status](https://travis-ci.org/hasadna/knesset-data-pipelines.svg?branch=master)](https://travis-ci.org/hasadna/knesset-data-pipelines)

Knesset data scrapers and data sync

Uses the [datapackage pipelines framework](https://github.com/frictionlessdata/datapackage-pipelines) to scrape Knesset data and aggregate to different data stores (PostgreSQL, Elasticsearch, Files)

## Available Endpoints
* public endpoints:
  * https://next.oknesset.org/pipelines/ - pipelines dashboard
  * Metabase dashboards for quick friendly visualizations of the data in DB:
    * [ועדות](http://next.oknesset.org/metabase/public/dashboard/57604bd2-73f3-4fbc-943f-53bf45287641)
    * [חקיקה](http://next.oknesset.org/metabase/public/dashboard/edf65569-8ca3-41cb-a917-39951c80b9bc)
    * [הצעות חוק](http://next.oknesset.org/metabase/public/dashboard/0c78c5f7-2d1b-4d99-9800-0c7495e2f7be)
    * [מליאה](http://next.oknesset.org/metabase/public/dashboard/deb07e12-4a50-4023-b298-576af358c0ea)
  * Data reference html pages:
    * https://minio.oknesset.org/bills/aggregations/knesset_data_bills.html
    * https://minio.oknesset.org/laws/aggregations/knesset_data_laws.html
    * https://minio.oknesset.org/plenum/aggregations/knesset_data_plenum.html
    * https://minio.oknesset.org/committees/aggregations/knesset_data_committees.html
  * Graphana dashboards for metrics / analytics:
    * [Knesset Dataservice Processors Metrics](https://next.oknesset.org/grafana/dashboard/db/knesset-dataservice-pipelines)
* internal admin interfaces - password required
  * https://next.oknesset.org/metabase/ - user friendly DB queries and dashboards
  * https://minio.oknesset.org/ - object storage
  * https://next.oknesset.org/adminer/ - for admin DB access
    * in adminer UI login screen, you should choose:
      * System: PostgreSQL
      * Server: db
      * Username, Password, Database: **secret**
  * https://next.oknesset.org/flower/ - celery tasks management
  * https://next.oknesset.org/grafana/ - Web UI for graphing metrics (via InfluxDB)
* deployment of this environment was done using Kubernetes (K8S) on Google Container Engine (GKE)
  * [deployment details and devops documentation](https://github.com/hasadna/knesset-data-pipelines/blob/master/devops/k8s/)

## Contributing

Looking to contribute? check out the [Help Wanted Issues](https://github.com/hasadna/knesset-data-pipelines/issues?q=is%3Aissue+is%3Aopen+label%3A%22help+wanted%22) or the [Noob Friendly Issues](https://github.com/hasadna/knesset-data-pipelines/issues?q=is%3Aissue+is%3Aopen+label%3A%22noob+friendly%22) for some ideas.

### Running the full pipelines environment using docker

#### A note for windows users:
Using windows with our docker environment is not currently recomended or supported. The build process seems to fail on numerous issues.
We suggest that windows users either dual-boot to Linux, or run Linux in virtualbox. Best supported version is Ubuntu 17.04
If you wish to use windows, do so at your own risk, and please update this README file with instructions if you succeed.

#### Instructions for running on Ubuntu (other distros and mac should follow a similar process):

* Install Docker
  * Ubuntu - [Docker Official Docs - Ubuntu installation](https://docs.docker.com/engine/installation/linux/docker-ce/ubuntu) - The recommended method is "Install using the repository")
  * Mac - https://store.docker.com/editions/community/docker-ce-desktop-mac
* Install docker-compose
  * Ubuntu - `sudo apt install docker-compose`
  * Mac - should be installed as part of the toolbox
* Make sure docker-compose is at version 1.13.0 or higher: `docker-compose --version`
  * If not, upgrade docker compose (refer to [Docker-compose Official Docs](https://docs.docker.com/compose/install/#install-compose))
* fork & clone the repo
* change directory to the repo's directory
* `sudo bin/start.sh`
* verify all dockers started correctly: `sudo docker ps` (should show 3 images running - app, db, redis)

This will provide:

* Pipelines dashboard: http://localhost:5000/
* PostgreSQL server, pre-populated with data: postgresql://postgres:123456@localhost:15432/postgres
* Minio object storage: http://localhost:9000/
  * Access Key = `admin`
  * Secret = `12345678`
* Adminer - DB Web UI: http://localhost:18080/
  * Database Type = PostgreSQL
  * Host = db
  * Port = 5432
  * Database = postgres
  * User = postgres
  * Password = 123456

After every change in the code you should run `sudo bin/build.sh && sudo bin/start.sh`


### Installing the project locally and running tests

You should have an activated python 3.6 virtualenv, following procedure will work on Ubuntu 17.04:
```
curl -kL https://raw.github.com/saghul/pythonz/master/pythonz-install | bash
echo '[[ -s $HOME/.pythonz/etc/bashrc ]] && source $HOME/.pythonz/etc/bashrc' >> ~/.bashrc
source ~/.bashrc
sudo apt-get install build-essential zlib1g-dev libbz2-dev libssl-dev libreadline-dev libncurses5-dev libsqlite3-dev libgdbm-dev libdb-dev libexpat-dev libpcap-dev liblzma-dev libpcre3-dev
pythonz install 3.6.2
sudo pip install virtualenvwrapper
echo 'export WORKON_HOME=$HOME/.virtualenvs; export PROJECT_HOME=$HOME/Devel; source /usr/local/bin/virtualenvwrapper.sh' >> ~/.bashrc
source ~/.bashrc
cd knesset-data-pipelines
mkvirtualenv -a `pwd` -p $HOME/.pythonz/pythons/CPython-3.6.2/bin/python3.6 knesset-data-pipelines
```

Before running any knesset-data-pipelines script, be sure to activate the virtualenv

You can do that by running `workon knesset-data-pipelines`

Once you are inside a Python 3.6 virtualenv, you can run the following:
* `bin/install.sh`
* `bin/test.sh`

You can set some environment variables to modify behaviors, see a refernece at .env.example

### Running the dpp cli

* using docker: `bin/dpp.sh`
* locally (from an activated virtualenv): `dpp`

### Run all pipelines at once

**Warning** this might seriously overload your CPU, use with caution..

```
docker-compose up -d redis db minio
source .env.example
for PIPELINE in `dpp | tail -n+2 | cut -d" " -f2 -`; do
    dpp run "${PIPELINE}" &
done
```

### Debugging committee meeting protocols

You should have the committee and session id of a meeting that you want to investigate

In this example the session id is `284231` and committee id is `196`

* Ensure an empty DB
  * `sudo rm -rf .data-docker/postgresql`
* Start the docker compose environment
  * `bin/start.sh`
* Wait ~20 seconds to ensure environment started properly
* Parse the protocols of the specific meeting / session id
  * `OVERRIDE_COMMITTEE_MEETING_IDS=284231 bin/dpp.sh run ./committees/committee-meeting-protocols`
* Check the parsed files in minio
  * minio default username=`admin`, password=`12345678`
  * original downloaded .doc: `284231.doc` - http://localhost:9000/minio/committees/protocols/original/196/
  * parsed files: `284231.txt` / `284231.csv` - http://localhost:9000/minio/committees/protocols/parsed/196/

### Updating the DB

The db image is updated with new data from time to time, to recreate the DB from scratch with latest data:

```
docker-compose stop db && sudo rm -rf .data-docker/postgresql/ && docker-compose up -d db
```
