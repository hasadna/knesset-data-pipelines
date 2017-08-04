# Knesset data datapackage pipelines

[![Build Status](https://travis-ci.org/hasadna/knesset-data-pipelines.svg?branch=master)](https://travis-ci.org/hasadna/knesset-data-pipelines)
[![Docker Automated build](https://img.shields.io/docker/automated/jrottenberg/ffmpeg.svg)](https://hub.docker.com/r/orihoch/knesset-data-pipelines/)

Knesset data scrapers and data sync

Uses the [datapackage pipelines framework](https://github.com/frictionlessdata/datapackage-pipelines)

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

## Installing the project locally and running tests

Only the latest Python version is supported (3.6)

* `bin/install.sh`
* `bin/test.sh`

You can set some environment variables to modify behaviors, see a refernece at .env.example

## Running the dpp cli

* using docker: `bin/dpp.sh`