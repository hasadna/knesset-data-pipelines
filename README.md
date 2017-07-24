# Knesset data datapackage pipelines

[![Build Status](https://travis-ci.org/hasadna/knesset-data-pipelines.svg?branch=master)](https://travis-ci.org/hasadna/knesset-data-pipelines)
[![Docker Automated build](https://img.shields.io/docker/automated/jrottenberg/ffmpeg.svg)](https://hub.docker.com/r/hasadna/knesset-data-pipelines/)

Pipelines for data sync for knesset-data

Uses the [datapackage pipelines framework](https://github.com/frictionlessdata/datapackage-pipelines)

## Overview

This project provides pipelines scrape and store knesset data

## Installation

Docker is the easiest way to install and run the environment locally.

After you [Install Docker](https://docs.docker.com/engine/installation/) you can start the app:

* `make docker-restart`

## Usage

* go to: http://localhost:5000/
* the datapackage-pipelines framework runs the pipelines automatically according to the pipelines configurations

## Development

Check out the [contribution guide](CONTRIBUTING.md)
