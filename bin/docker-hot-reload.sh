#!/usr/bin/env sh

[ "$1" == "" ] && echo bin/docker-hot-reload.sh '<new_code_path>' && exit 1

cp -fR /$1/pipelines/* ./ &&\
rm -fr /$1 &&\
pipenv install --system --deploy --ignore-pipfile &&\
pip install -U . &&\
kill -HUP 1 &&\
echo Great Success && exit 0

echo Failed Hot Reload
exit 1
