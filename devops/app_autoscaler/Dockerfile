FROM python:3.6-alpine

RUN apk --update add ca-certificates wget curl tar bash openssl jq git

RUN pip install pyyaml

COPY *.sh /
COPY *.py /

ENTRYPOINT ["bash", "-c"]
CMD ["/daemon.sh"]
