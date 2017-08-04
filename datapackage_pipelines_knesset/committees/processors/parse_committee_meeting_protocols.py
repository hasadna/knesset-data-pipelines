from datapackage_pipelines_knesset.common.processors.base_processor import BaseProcessor
from knesset_data.protocols.committee import CommitteeMeetingProtocol
import os, csv, json


class ParseCommitteeMeetingProtocolsProcessor(BaseProcessor):

    def __init__(self, *args, **kwargs):
        super(ParseCommitteeMeetingProtocolsProcessor, self).__init__(*args, **kwargs)
        self._schema["fields"] = [{"name": "committee_id", "type": "integer"},
                                  {"name": "meeting_id", "type": "integer"},
                                  {"name": "protocol_file", "type": "string",
                                   "description": "relative path to the protocol file"},
                                  {"name": "text_file", "type": "string"},
                                  {"name": "parts_file", "type": "string"},]
        self._all_filenames = []

    def _process(self, datapackage, resources):
        return self._process_filter(datapackage, resources)

    def _get_filename(self, relpath):
        return os.path.join(self._parameters["out-path"], relpath)

    def _filter_row(self, meeting_protocol, **kwargs):
        parts_relpath = os.path.join(str(meeting_protocol["committee_id"]), "{}.csv".format(meeting_protocol["meeting_id"]))
        text_relpath = os.path.join(str(meeting_protocol["committee_id"]), "{}.txt".format(meeting_protocol["meeting_id"]))
        parts_filename = self._get_filename(parts_relpath)
        text_filename = self._get_filename(text_relpath)
        if parts_relpath not in self._all_filenames:
            self._all_filenames += [parts_relpath, text_relpath]
            os.makedirs(os.path.dirname(parts_filename), exist_ok=True)
        with CommitteeMeetingProtocol.get_from_filename(meeting_protocol["protocol_file"]) as protocol:
            with open(text_filename, "w") as f:
                f.write(protocol.text)
            with open(parts_filename, "w") as f:
                csv_writer = csv.writer(f)
                csv_writer.writerow(["header", "body"])
                for part in protocol.parts:
                    csv_writer.writerow([part.header, part.body])
        yield {"committee_id": meeting_protocol["committee_id"],
               "meeting_id": meeting_protocol["meeting_id"],
               "protocol_file": meeting_protocol["protocol_file"],
               "text_file": text_filename,
               "parts_file": parts_filename}

    def _process_cleanup(self):
        filename = self._get_filename("datapackage.json")
        with open(filename, "w") as f:
            descriptor = {"name": "_", "path": self._all_filenames}
            descriptor.update(**self._parameters.get("data-resource-descriptor", {}))
            json.dump({"name": "_", "resources": [descriptor]}, f)

if __name__ == '__main__':
    ParseCommitteeMeetingProtocolsProcessor.main()
