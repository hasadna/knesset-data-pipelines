from datapackage_pipelines_knesset.common.processors.base_processor import BaseProcessor
from knesset_data.protocols.committee import CommitteeMeetingProtocol
import os, csv


class ParseCommitteeMeetingProtocolsProcessor(BaseProcessor):

    def __init__(self, *args, **kwargs):
        super(ParseCommitteeMeetingProtocolsProcessor, self).__init__(*args, **kwargs)
        self._schema["fields"] = [{"name": "committee_id", "type": "integer"},
                                  {"name": "meeting_id", "type": "integer"},
                                  {"name": "url", "type": "string"},
                                  {"name": "protocol_file", "type": "string",
                                   "description": "relative path to the protocol file"},
                                  {"name": "text_file", "type": "string"},
                                  {"name": "parts_file", "type": "string"},]

    def _process(self, datapackage, resources):
        return self._process_filter(datapackage, resources)

    def _filter_row(self, meeting_protocol, **kwargs):
        filepath = os.path.join(self._parameters["out-path"], str(meeting_protocol["committee_id"]))
        os.makedirs(filepath, exist_ok=True)
        parts_filename = os.path.join(filepath, str(meeting_protocol["meeting_id"])+".parts.csv")
        text_filename = os.path.join(filepath, str(meeting_protocol["meeting_id"])+".txt")
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
               "url": meeting_protocol["url"],
               "protocol_file": meeting_protocol["protocol_file"],
               "text_file": text_filename,
               "parts_file": parts_filename}


if __name__ == '__main__':
    ParseCommitteeMeetingProtocolsProcessor.main()
