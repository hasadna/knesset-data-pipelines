# Knesset data datapackage pipelines

Pipelines for data sync for knesset-data

Uses the [datapackage pipelines framework](https://github.com/frictionlessdata/datapackage-pipelines)

## Overview

This project provides pipelines scrape and store knesset data

## Installation

Docker is used to get the full environment that runs the sync pipelines. see [README-DOCKER](README-DOCKER.md) for more details, tips and common problems with Docker

* [Install Docker](https://docs.docker.com/engine/installation/) (tested with version 17.03)
* [Install Docker Compose](https://docs.docker.com/compose/install/)

Once you have docker you can run the following to build and start the app:

* `make docker-clean-start`

see [README-DOCKER](README-DOCKER.md) for more details

## Usage

* go to: http://localhost:5000/
* the datapackage-pipelines framework runs the pipelines automatically according to the pipelines configurations

## Development

Check out the [contribution guide](CONTRIBUTING.md)
