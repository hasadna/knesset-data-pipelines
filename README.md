# Knesset data pipelines

[![Build Status](https://travis-ci.org/hasadna/knesset-data-pipelines.svg?branch=master)](https://travis-ci.org/hasadna/knesset-data-pipelines)
[![Docker build](https://img.shields.io/docker/automated/jrottenberg/ffmpeg.svg)](https://hub.docker.com/r/orihoch/knesset-data-pipelines/)

Knesset data scrapers and data sync

Uses the [datapackage pipelines framework](https://github.com/frictionlessdata/datapackage-pipelines) to scrape Knesset data and aggregate to different data stores (PostgreSQL, Elasticsearch, Files)

## Available Endpoints
* public endpoints:
  * https://next.oknesset.org/pipelines/ - pipelines dashboard
  * https://next.oknesset.org/data/ - data files, also available in [json format](https://next.oknesset.org/data-json/)
* internal admin interfaces - password required
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

* Install Docker and Docker Compose (refer to Docker guides for your OS)
* fork & clone the repo
* change directory to the repo's directory
* `bin/start.sh`

This will provide:

* Pipelines dashboard: http://localhost:5000/
* PostgreSQL server: postgresql://postgres:123456@localhost:15432/postgres
* Data files under: .data-docker/

After every change in the code you should run `bin/build.sh && bin/start.sh`

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

Only the latest Python version is supported (3.6)

* `bin/install.sh`
* `bin/test.sh`

You can set some environment variables to modify behaviors, see a refernece at .env.example

## Running the dpp cli

* using docker: `bin/dpp.sh`
* locally (from an activated virtualenv): `dpp`

