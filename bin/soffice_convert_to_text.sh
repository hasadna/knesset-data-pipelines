#!/usr/bin/env sh

if ! which soffice > /dev/null; then
    echo "you should install libre office headless, something like this:"
    echo "apt-get install libreoffice --no-install-recommends --no-install-suggests"
    exit 1
elif [ "${*}" == "" ]; then
    echo "usage: bin/soffice_convert_to_text.sh <OUT_DIR> <RTF_FILENAME>"
else
    soffice --headless --convert-to txt --outdir ${1} ${2}
    exit 0
fi
