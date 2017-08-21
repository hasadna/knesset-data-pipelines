from datapackage_pipelines_knesset.common.processors.base_processor import BaseProcessor
from knesset_data.protocols.committee import CommitteeMeetingProtocol
import os

class ParseCommitteeMeetingAttendeesProcessor(BaseProcessor):

    def _process(self, datapackage, resources):
        self._schema["fields"] = [{"name": "committee_id", "type": "integer"},
                                  {"name": "meeting_id", "type": "integer"},
                                  {"name": "name", "type": "string"},
                                  {"name": "role", "type": "string"},
                                  {"name": "additional_information", "type": "string"}, ]
        return self._process_filter(datapackage, resources)

    def _filter_row(self, row, **kwargs):
        committee_id = row["committee_id"]
        meeting_id = row["id"]

        protocol_path = os.path.join(self._parameters["input-path"],str(committee_id),"%s.txt" % meeting_id)
        if os.path.exists(protocol_path):
            yield from self.extract_attendees_from_txt_file(protocol_path,committee_id,meeting_id)

    def extract_attendees_from_txt_file(self,filepath,committee_id,meeting_id):
        text = ""
        with open(filepath,"r") as f:
            text = f.read()

        attendees = CommitteeMeetingProtocol.get_from_text(text).attendees
        for key in attendees.keys():
            for attendee in attendees[key]:
                if key == "invitees":
                    yield {"committee_id":committee_id,
                           "meeting_id":meeting_id,
                           "name":attendee["name"],
                           "role":"invitees",
                           "additional_information":attendee["role"]}

                else:
                    yield {"committee_id":committee_id,
                           "meeting_id":meeting_id,
                           "name":attendee,
                           "role":key,
                           "additional_information":""}


if __name__ == "__main__":
    ParseCommitteeMeetingAttendeesProcessor.main()
