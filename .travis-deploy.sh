#!/usr/bin/env bash

bash .travis.sh deploy
DEPLOY_RES=$?
echo DEPLOY_RES=$DEPLOY_RES

docker tag orihoch/knesset-data-pipelines knesset-data-pipelines &&\
docker build -t orihoch/knesset-data-pipelines:full-latest -f Dockerfile.full . &&\
docker tag orihoch/knesset-data-pipelines:full-latest orihoch/knesset-data-pipelines:full-${TRAVIS_COMMIT} &&\
docker push orihoch/knesset-data-pipelines:full-latest &&\
docker push orihoch/knesset-data-pipelines:full-${TRAVIS_COMMIT}
FULL_RES=$?
echo FULL_RES=$FULL_RES

[ "${DEPLOY_RES}" != "0" ] && echo failed deploy && exit 1
[ "${FULL_RES}" != "0" ] && echo failed full docker build/push && exit 1

echo Great Success!
exit 0
