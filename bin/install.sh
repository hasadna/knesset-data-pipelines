#!/usr/bin/env sh

set -e

if [ "${1}" == "--optimized" ]; then
    pip install -r requirements.txt
    pip install .
else
    pip install -r requirements.txt
    which antiword > /dev/null || sudo apt-get install antiword
    pip install -e .[develop]
fi
