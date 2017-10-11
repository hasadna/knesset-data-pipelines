FROM sameersbn/postgresql:9.6-2

ENV PG_DATADIR /var/lib/postgresql/data
ENV PG_CERTDIR /var/ssl

WORKDIR /var/ssl

RUN set -xe \
    && openssl genrsa -des3 -out server.key -passout pass:foo 1024 \
    && openssl rsa -passin pass:foo -in server.key -out server.key \
    && chmod og-rwx server.key \
    && chown postgres.postgres server.key \
    && openssl req -new -key server.key -days 3650 -out server.crt -x509 -subj '/CN=postgres' \
    && cp server.crt root.crt

RUN /etc/init.d/postgresql reload

#RUN set -xe \
#    && openssl genrsa -des3 -out client.key -passout pass:foo 1024 \
#    && openssl rsa -passin pass:foo -in client.key -out client.key \
#    && openssl req -new -key client.key -out client.csr -subj '/CN=postgres' \
#    && openssl x509 -req -in client.csr -CA root.crt -CAkey server.key -out client.crt -CAcreateserial

WORKDIR /var/lib/postgresql/data

COPY pg_hba.conf /var/lib/postgresql/pg_hba.conf
COPY postgresql.conf /var/lib/postgresql/postgresql.conf

