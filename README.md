# Knesset data pipelines

[![Build Status](https://travis-ci.org/hasadna/knesset-data-pipelines.svg?branch=master)](https://travis-ci.org/hasadna/knesset-data-pipelines)
[![Docker build](https://img.shields.io/docker/automated/jrottenberg/ffmpeg.svg)](https://hub.docker.com/r/orihoch/knesset-data-pipelines/)

Knesset data scrapers and data sync

Uses the [datapackage pipelines framework](https://github.com/frictionlessdata/datapackage-pipelines) to scrape Knesset data and aggregate to different data stores (PostgreSQL, Elasticsearch, Files)

## Available Endpoints
* public endpoints:
  * https://next.oknesset.org/pipelines/ - pipelines dashboard
  * https://next.oknesset.org/data/ - data files, also available in [json format](https://next.oknesset.org/data-json/)
  * Metabase dashboards for quick friendly visualizations of the data in DB, for example [committees dashboard](https://next.oknesset.org/metabase/public/dashboard/57604bd2-73f3-4fbc-943f-53bf45287641)
* internal admin interfaces - password required
  * https://next.oknesset.org/metabase/ - user friendly DB queries and dashboards
  * https://next.oknesset.org/adminer/ - for admin DB access
    * in adminer UI login screen, you should choose:
      * System: PostgreSQL
      * Server: db
      * Username, Password, Database: **secret**
  * https://next.oknesset.org/flower/ - celery tasks management
* deployment of this environment was done using Kubernetes (K8S) on Google Container Engine (GKE)
  * [deployment details and devops documentation](https://github.com/hasadna/knesset-data-pipelines/blob/master/devops/K8S.md)

## Contributing

Looking to contribute? check out the [Help Wanted Issues](https://github.com/hasadna/knesset-data-pipelines/issues?q=is%3Aissue+is%3Aopen+label%3A%22help+wanted%22) or the [Noob Friendly Issues](https://github.com/hasadna/knesset-data-pipelines/issues?q=is%3Aissue+is%3Aopen+label%3A%22noob+friendly%22) for some ideas.

## Running the full pipelines environment using docker

#### A note for windows users: 
Using windows with docker is not currently recomended or supported. The build process seems to fail on numerous issues.
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
* PostgreSQL server: postgresql://postgres:123456@localhost:15432/postgres
* Data files under: .data-docker/

After every change in the code you should run `sudo bin/build.sh && sudo bin/start.sh`

## Using Redash to view the data

Redash is a Web UI which allows to make queries against the DB.

It's the main interface for both developers and users of the project that want to get the data.

You can run a local redash instance by running:

* `bin/start_redash.sh`
* redash is available at: http://localhost:5010
* setup an admin user
* add a datasource:
  * Name: knesset_data
  * Type: PostgreSQL
  * Host: knessetdatapipelines_db_1
  * Password: 123456
  * User: postgres
  * Database Name: postgres
  * Port: 5432
* now you can make queries (once pipelines run and load some data to the DB)

## Installing the project locally and running tests

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

## Running the dpp cli

* using docker: `bin/dpp.sh`
* locally (from an activated virtualenv): `dpp`
