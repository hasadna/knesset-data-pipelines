#!/usr/bin/env bash

echo Deleting committees dist cache hashes
find data/committees/dist/dist/ -type f -name '*.hash' -print -delete | wc -l

echo Deleting people committee meeting attendees cache hashes
find data/people/committees/meeting-attendees/cache_hash/ -type f -name '*.txt.json' -print -delete | wc -l
