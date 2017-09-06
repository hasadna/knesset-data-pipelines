FROM orihoch/knesset-data-pipelines-base:v1.0.5

COPY requirements.txt /requirements.txt
RUN pip install -r /requirements.txt

RUN mkdir /knesset
WORKDIR /knesset
COPY . /knesset/

ENV PYTHONUNBUFFERED 1
ENV PIPELINES_BIN_PATH /knesset/bin
ENV RTF_EXTRACTOR_BIN /knesset/bin/rtf_extractor.py

RUN cd /knesset && pip install .

ENTRYPOINT ["/knesset/docker-run.sh"]

EXPOSE 5000
VOLUME /knesset/data
