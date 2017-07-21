#!/usr/bin/env bash

if [ "${DOCKER_USERNAME}" != "" ] && [ "${DOCKER_PASSWORD}" != "" ]; then
    docker --version
    docker login -u="${DOCKER_USERNAME}" -p="${DOCKER_PASSWORD}"
    make docker-build
    if [ "${TRAVIS_TAG}" != "" ]; then
        TAG="${TRAVIS_TAG}"
    else
        TAG="${TRAVIS_BRANCH}"
    fi
    docker push orihoch/knesset-data-pipelines:${TAG}
fi

echo "OK"
