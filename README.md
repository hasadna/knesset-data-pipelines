# Knesset data datapackage pipelines

[![Build Status](https://travis-ci.org/hasadna/knesset-data-pipelines.svg?branch=master)](https://travis-ci.org/hasadna/knesset-data-pipelines)
[![Docker Automated build](https://img.shields.io/docker/automated/jrottenberg/ffmpeg.svg)](https://hub.docker.com/r/hasadna/knesset-data-pipelines/)

Knesset data scrapers and data sync

Uses the [datapackage pipelines framework](https://github.com/frictionlessdata/datapackage-pipelines)

## Quickstart

* `make install`
* `make test`
* `dpp`

## Docker

* `make docker-build`
* `make docker-restart`
* `make docker-logs`
* goto: http://localhost:5000/
