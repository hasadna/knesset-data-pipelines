from datapackage_pipelines_knesset.common.processors.base_processor import BaseProcessor
import os, requests, logging, time
from requests.exceptions import RequestException
from datapackage_pipelines_knesset.common.db import get_session
from sqlalchemy import *


class DownloadCommitteeMeetingProtocolsProcessor(BaseProcessor):

    def __init__(self, *args, **kwargs):
        super(DownloadCommitteeMeetingProtocolsProcessor, self).__init__(*args, **kwargs)
        self._schema["fields"] = [{"name": "committee_id", "type": "integer"},
                                  {"name": "meeting_id", "type": "integer"},
                                  {"name": "url", "type": "string"},
                                  {"name": "protocol_file", "type": "string",
                                   "description": "relative path to the protocol file"}]
        self._db_session = self._get_session()
        self._db_meta = MetaData(bind=self._db_session.connection())
        self._db_meta.reflect()
        self._db_meetings = self._db_meta.tables.get(self._parameters["meetings-table"])

    def _get_session(self):
        return get_session()

    def _process(self, datapackage, resources):
        return self._process_filter(datapackage, resources)

    def _process_cleanup(self):
        self._db_session.commit()
        super(DownloadCommitteeMeetingProtocolsProcessor, self)._process_cleanup()

    def _reuqests_get(self, url):
        return requests.get(url)

    def _save_url_to_file(self, url, filename, num_retries, seconds_between_retries, retry_num=1):
        try:
            res = self._reuqests_get(url)
        except RequestException as e:
            if retry_num < num_retries:
                logging.exception(e)
                logging.info("retry {} / {}, waiting {} seconds before retrying...".format(retry_num, num_retries, seconds_between_retries))
                time.sleep(seconds_between_retries)
                return self._save_url_to_file(url, filename, num_retries, seconds_between_retries, retry_num+1)
            else:
                raise
        res.raise_for_status()
        with open(filename, "wb") as f:
            f.write(res.content)

    def _has_protocol_text(self, meeting):
        if self._db_meetings is not None:
            row = self._db_meetings.select().where(self._db_meetings.c.id == meeting["id"]).execute().fetchone()
            if row is not None and row[self._db_meetings.c.protocol_text]:
                return True

    def _filter_row(self, meeting, **kwargs):
        pre = "skipping protocol download for committee {} meeting {}: ".format(meeting["committee_id"],
                                                                                meeting["id"])
        if not meeting["url"]:
            logging.info("{} no url".format(pre))
        elif (os.environ.get("OVERRIDE_COMMITTEE_MEETING_IDS")
              and str(meeting["id"]) not in os.environ["OVERRIDE_COMMITTEE_MEETING_IDS"].split(",")):
            logging.info("{} not in OVERRIDE_COMMITTEE_MEETING_IDS".format(pre))
        elif self._has_protocol_text(meeting):
            logging.info("{} has protocol_text".format(pre))
        else:
            filepath = os.path.join(self._parameters["out-path"], str(meeting["committee_id"]))
            os.makedirs(filepath, exist_ok=True)
            filename = os.path.join(filepath, str(meeting["id"])+".doc")
            num_retries = self._parameters.get("num-retries", 5)
            seconds_between_retries = self._parameters.get("seconds-between-retries", 60)
            self._save_url_to_file(meeting["url"], filename, num_retries, seconds_between_retries)
            yield {"committee_id": meeting["committee_id"],
                   "meeting_id": meeting["id"],
                   "url": meeting["url"],
                   "protocol_file": filename}

if __name__ == '__main__':
    DownloadCommitteeMeetingProtocolsProcessor.main()
