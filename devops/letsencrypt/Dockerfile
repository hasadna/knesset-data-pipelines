FROM ubuntu

RUN apt-get update
RUN apt-get install -y mc software-properties-common
RUN add-apt-repository -y ppa:certbot/certbot
RUN apt-get update
RUN DEBIAN_FRONTEND=noninteractive apt-get install -y certbot

VOLUME /var/log/letsencrypt
VOLUME /etc/letsencrypt
VOLUME /nginx-html

COPY issue_cert.sh /issue_cert.sh
COPY renew_certs.sh /renew_certs.sh
COPY entrypoint.sh /entrypoint.sh

ENV TERM xterm

ENTRYPOINT ["/entrypoint.sh"]
