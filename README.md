# Knesset data datapackage pipelines

[![Build Status](https://travis-ci.org/hasadna/knesset-data-pipelines.svg?branch=master)](https://travis-ci.org/hasadna/knesset-data-pipelines)
[![Docker Automated build](https://img.shields.io/docker/automated/jrottenberg/ffmpeg.svg)](https://hub.docker.com/r/hasadna/knesset-data-pipelines/)

Knesset data scrapers and data sync

Uses the [datapackage pipelines framework](https://github.com/frictionlessdata/datapackage-pipelines)

## Running the full pipelines environment using docker

* Install Docker and Docker Compose (refer to Docker guides for your OS)
* `make docker-start`

This will provide:

* Pipelines dashboard: http://localhost:5000/
* PostgreSQL server: postgresql://postgres:123456@localhost:15432/postgres
* Data files under: .data-docker/

After every change in the code you should run `make docker-build && make docker-start`

## Running the project locally

Only the latest Python version is supported (3.6)

* `make install`
* `make test`
* `dpp`

You can set some environment variables to modify behaviors, see a refernece at .env.example
