#!/usr/bin/env bash

export CLOUDSDK_CORE_DISABLE_PROMPTS=1

if [ ! -d "$HOME/google-cloud-sdk/bin" ]; then
    rm -rf $HOME/google-cloud-sdk
    curl https://sdk.cloud.google.com | bash
fi

source "${HOME}/google-cloud-sdk/path.bash.inc"
gcloud version
gcloud --quiet components update kubectl
