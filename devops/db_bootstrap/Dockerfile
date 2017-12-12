FROM sameersbn/postgresql:9.6-2

COPY redacted-17-12-12.sql /redacted.sql
# RUN wget "http://storage.googleapis.com/kdp-production-db-backups/redacted-17-12-12.sql" -O /redacted.sql

COPY entrypoint.sh /db-bootstrap-entrypoint.sh

ENTRYPOINT ["/db-bootstrap-entrypoint.sh"]
