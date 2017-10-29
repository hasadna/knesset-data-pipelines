from datapackage_pipelines_knesset.common.processors.base_processor import BaseProcessor
from knesset_data.protocols.committee import CommitteeMeetingProtocol
from datapackage_pipelines_knesset.common import object_storage
from datapackage_pipelines_knesset.common import db

class ParseCommitteeMeetingSpeakersProcessor(BaseProcessor):

    def _process(self, datapackage, resources):
        self._schema["fields"] = [{"name": "committee_id", "type": "integer"},
                                  {"name": "meeting_id", "type": "integer"},
                                  {"name": "name", "type": "string"} ]
        self.s3 = object_storage.get_s3()
        self.existing_rows = db.ExistingRows("committee-meeting-speakers", primary_key="meeting_id")
        return self._process_filter(datapackage, resources)

    def _filter_row(self, row, **kwargs):
        committee_id = row["kns_committee_id"]
        meeting_id = row["kns_session_id"]

        file_object_path = "protocols/parsed/{}/{}.txt".format(committee_id, meeting_id)

        if not self.existing_rows.contains(meeting_id) and object_storage.exists(self.s3, "committees", file_object_path):
            yield from self.extract_speakers_from_txt_file(file_object_path,committee_id,meeting_id)

    def extract_speakers_from_txt_file(self,file_object_path,committee_id,meeting_id):

        text = object_storage.read(self.s3, "committees", file_object_path).decode()


        with CommitteeMeetingProtocol.get_from_text(text) as protocol:
            speakers = protocol.speakers

        if speakers is not None:

            for speaker in speakers:
                yield {"committee_id":committee_id,
                       "meeting_id":meeting_id,
                       "name":speaker }


if __name__ == "__main__":
    ParseCommitteeMeetingSpeakersProcessor.main()