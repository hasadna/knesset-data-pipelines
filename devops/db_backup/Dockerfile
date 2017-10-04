FROM google/cloud-sdk:171.0.0-alpine

RUN apk --update --no-cache add postgresql

COPY entrypoint.sh /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
