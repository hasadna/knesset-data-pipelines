#!/usr/bin/env bash

# dump all databases without roles

pg_dumpall --lock-wait-timeout=300000 --clean | grep -v 'DROP ROLE ' | grep -v 'CREATE ROLE ' | grep -v 'ALTER ROLE '
