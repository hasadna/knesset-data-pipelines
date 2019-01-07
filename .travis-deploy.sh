#!/usr/bin/env bash

bash .travis.sh deploy
# &&\
# docker pull orihoch/knesset-data-pipelines-jupyter:latest &&\
# docker build --cache-from orihoch/knesset-data-pipelines-jupyter:latest \
#              -t orihoch/knesset-data-pipelines-jupyter -f jupyter.Dockerfile . &&\
# docker push orihoch/knesset-data-pipelines-jupyter:latest &&\
# docker tag orihoch/knesset-data-pipelines-jupyter:latest \
#            orihoch/knesset-data-pipelines-jupyter:${TRAVIS_COMMIT} &&\
# docker push orihoch/knesset-data-pipelines-jupyter:${TRAVIS_COMMIT}
