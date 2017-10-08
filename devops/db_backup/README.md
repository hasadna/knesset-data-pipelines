# DB restore and backup scripts

### environment variables

* `BACKUP_INITIAL_DELAY_SECONDS` - how long to wait before starting (default = 15 seconds)
* `RESTORE_GS_URL` - if set, runs a one time restore job from this google storage url and then exits

##### Backup daemon variables

* `BACKUP_INTERVAL_SECONDS` - how many seconds to wait between backups (default = 86400 = 1 day)
* `BACKUP_MAX_RETRIES` = (default=5)
* `BACKUP_SECONDS_BETWEEN_RETRIES` (default=5)
* `BACKUP_FILE_TEMPLATE` = (default=%y-%m-%d-%H-%M)

##### Postgresql variables

You can set any of the Postgresql client environment variables, see https://www.postgresql.org/docs/current/static/libpq-envars.html

Usually you will want to set the following:
* `PGPASSWORD` - Postgresql password
* `PGHOST` - Postgresql host name
* `PGPORT` - Postgresql port
* `PGUSER` - Postgresql user

##### Google Cloud Storage variables

* `GOOGLE_AUTH_SECRET_KEY_FILE` - path to secret key for authentication
* `SERVICE_ACCOUNT_ID` - Google cloud service account id
* `CLOUDSDK_CORE_PROJECT` - Google cloud project id
* `CLOUDSDK_COMPUTE_ZONE` - Google cloud zone
* `STORAGE_BUCKET_NAME` - Google cloud storage bucket name (should be created beforehand)
