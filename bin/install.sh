#!/usr/bin/env sh

set -e

pip install -r requirements.txt
which antiword > /dev/null || sudo apt-get install antiword
pip install -e .[develop]
