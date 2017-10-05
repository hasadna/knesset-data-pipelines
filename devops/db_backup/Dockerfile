FROM google/cloud-sdk:171.0.0-alpine

RUN apk --update --no-cache add postgresql

COPY *.sh /

RUN chmod +x /*.sh

ENTRYPOINT ["/entrypoint.sh"]

ENV BIN_PATH "/"
