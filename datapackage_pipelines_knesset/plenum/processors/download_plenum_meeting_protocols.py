import re

from datapackage_pipelines_knesset.common.processors.base_processor import BaseProcessor
from requests.exceptions import RequestException
import os, requests, logging, time, json
from datapackage_pipelines_knesset.common import object_storage


class DownloadPlenumMeetingProtocolsProcessor(BaseProcessor):
    def __init__(self, *args, **kwargs):
        super(DownloadPlenumMeetingProtocolsProcessor, self).__init__(*args, **kwargs)
        self._schema["fields"] = [
            {
                "name": "kns_plenum_session_id", "type": "integer",
                "description": "primary key from kns_plenumsession table"
            },
            {
                "name": "protocol_object_name", "type": "string",
                "description": "storage object name containing the downloaded protocol"
            },
            {
                "name": "protocol_extension", "type": "string",
                "description": "file extension of the downloaded protocol"
            },
        ]
        self._schema["primaryKey"] = ["kns_plenum_session_id"]
        self._all_object_names = []
        self.s3 = object_storage.get_s3()
        self.extension_regex = re.compile("[.](.{3,8})$")

    def _process(self, datapackage, resources):
        return self._process_filter(datapackage, resources)

    def _reuqests_get(self, url):
        return requests.get(url)

    def _save_url(self, url, bucket, object_name, num_retries, seconds_between_retries, retry_num=1):
        try:
            res = self._reuqests_get(url)
        except RequestException as e:
            if retry_num < num_retries:
                logging.exception(e)
                logging.info("retry {} / {}, waiting {} seconds before retrying...".format(retry_num, num_retries,
                                                                                           seconds_between_retries))
                time.sleep(seconds_between_retries)
                return self._save_url(url, bucket, object_name, num_retries, seconds_between_retries, retry_num + 1)
            else:
                raise
        if res.status_code == 200:
            object_storage.write(self.s3, bucket, object_name, res.content)
            return True
        else:
            return False

    def _get_extension(self, meeting):

        extension_match = self.extension_regex.search(meeting["url"])

        if extension_match:
            return extension_match.group(1)
        else:
            logging.warning("unknown extension: {}".format(meeting["url"]))

    def _get_protocol_storage_bucket_name(self):
        return self._parameters["bucket-name"]

    def _get_protocol_storage_object_name(self, meeting_id, extension):
        return "{}/{}.{}".format(self._parameters["bucket-name"], meeting_id, extension)

    def _filter_row(self, meeting, **kwargs):
        bucket = "plenum"
        protocol_extension = self._get_extension(meeting)
        object_name = "protocols/original/{}.{}".format(meeting["kns_plenum_session_id"],
                                                        protocol_extension)

        override_meeting_ids = os.environ.get("OVERRIDE_PLENUM_MEETING_IDS")
        if not override_meeting_ids or str(meeting["kns_plenum_session_id"]) in override_meeting_ids.split(","):

            if not object_storage.exists(self.s3, bucket, object_name):
                num_retries = self._parameters.get("num-retries", 5)
                seconds_between_retries = self._parameters.get("seconds-between-retries", 60)
                logging.info("downloading {} -> {}/ {}".format(meeting["url"], bucket, object_name))
                if not self._save_url(meeting["url"], bucket, object_name, num_retries, seconds_between_retries):
                    object_name = None
            if object_name is not None:
                # yields all meetings - both ones that were just downloaded, and meetings which were download previously
                # the only meetings not yielded are meeting which failed downloading
                yield {"kns_plenum_session_id": meeting["kns_plenum_session_id"],
                       "protocol_object_name": object_name,
                       "protocol_extension": protocol_extension}


if __name__ == '__main__':
    DownloadPlenumMeetingProtocolsProcessor.main()
