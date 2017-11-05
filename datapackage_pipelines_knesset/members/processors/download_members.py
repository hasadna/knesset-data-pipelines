from datapackage_pipelines_knesset.common.processors.base_processor import BaseProcessor
from requests.exceptions import RequestException
import os, requests, logging, time, json
from datapackage_pipelines_knesset.common import object_storage


class DownloadMembersProcessor(BaseProcessor):
    def __init__(self, *args, **kwargs):
        super(DownloadMembersProcessor, self).__init__(*args, **kwargs)
        self._schema["fields"] = [
            {
                "name": "kns_person_id", "type": "integer",
                "description": "primary key from kns_person table"
            }
        ]
        self._schema["primaryKey"] = ["kns_person_id"]
        self._all_object_names = []
        self.s3 = object_storage.get_s3()

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


if __name__ == '__main__':
    DownloadMembersProcessor.main()
