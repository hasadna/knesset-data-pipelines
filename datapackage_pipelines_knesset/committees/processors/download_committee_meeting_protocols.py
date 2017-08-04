from datapackage_pipelines_knesset.common.processors.base_processor import BaseProcessor
from requests.exceptions import RequestException
import os, requests, logging, time, json


class DownloadCommitteeMeetingProtocolsProcessor(BaseProcessor):

    def __init__(self, *args, **kwargs):
        super(DownloadCommitteeMeetingProtocolsProcessor, self).__init__(*args, **kwargs)
        self._schema["fields"] = [{"name": "committee_id", "type": "integer"},
                                  {"name": "meeting_id", "type": "integer"},
                                  {"name": "protocol_file", "type": "string",
                                   "description": "relative path to the protocol file"}]
        self._all_filenames = []

    def _process(self, datapackage, resources):
        return self._process_filter(datapackage, resources)

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

    def _get_filename(self, relpath):
        return os.path.join(self._parameters["out-path"], relpath)

    def _filter_row(self, meeting, **kwargs):
        # pre = "skipping protocol download for committee {} meeting {}: ".format(meeting["committee_id"],
        #                                                                         meeting["id"])
        if not meeting["url"]:
            pass
            # logging.info("{} no url".format(pre))
        elif (os.environ.get("OVERRIDE_COMMITTEE_MEETING_IDS")
              and str(meeting["id"]) not in os.environ["OVERRIDE_COMMITTEE_MEETING_IDS"].split(",")):
            pass
            # logging.info("{} not in OVERRIDE_COMMITTEE_MEETING_IDS".format(pre))
        else:
            relpath = os.path.join(str(meeting["committee_id"]), "{}.doc".format(meeting["id"]))
            filename = self._get_filename(relpath)
            if os.path.exists(filename):
                pass
                # logging.info("{} has protocol_text".format(pre))
            else:
                if relpath not in self._all_filenames:
                    self._all_filenames.append(relpath)
                    os.makedirs(os.path.dirname(filename), exist_ok=True)
                num_retries = self._parameters.get("num-retries", 5)
                seconds_between_retries = self._parameters.get("seconds-between-retries", 60)
                self._save_url_to_file(meeting["url"], filename, num_retries, seconds_between_retries)
                yield {"committee_id": meeting["committee_id"],
                       "meeting_id": meeting["id"],
                       "protocol_file": filename}

    def _process_cleanup(self):
        filename = self._get_filename("datapackage.json")
        with open(filename, "w") as f:
            descriptor = {"name": "_", "path": self._all_filenames}
            descriptor.update(**self._parameters.get("data-resource-descriptor", {}))
            json.dump({"name": "_", "resources": [descriptor]}, f)


if __name__ == '__main__':
    DownloadCommitteeMeetingProtocolsProcessor.main()
