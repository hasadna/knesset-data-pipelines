from datapackage_pipelines_knesset.common.processors.base_processor import BaseProcessor
from knesset_data.protocols.committee import CommitteeMeetingProtocol
from datapackage_pipelines_knesset.common import object_storage
import logging


class ParseCommitteeMeetingAttendeesProcessor(BaseProcessor):

    def _process(self, datapackage, resources):
        self._schema["fields"] = [{"name": "committee_id", "type": "integer"},
                                  {"name": "meeting_id", "type": "integer"},
                                  {"name": "name", "type": "string"},
                                  {"name": "role", "type": "string"},
                                  {"name": "additional_information", "type": "string"}, ]
        return self._process_filter(datapackage, resources)

    def _filter_row(self, row, **kwargs):
        committee_id = row["kns_committee_id"]
        meeting_id = row["kns_session_id"]

        file_object_path = "protocols/parsed/{}/{}.txt".format(committee_id,meeting_id)

        if object_storage.exists("committees",file_object_path):
            yield from self.extract_attendees_from_txt_file(file_object_path,committee_id,meeting_id)

    def extract_attendees_from_txt_file(self,file_object_path,committee_id,meeting_id):

        text = object_storage.read("committees",file_object_path)


        with CommitteeMeetingProtocol.get_from_text(text) as protocol:
            attendees = protocol.attendees

        if attendees is not None:

            for key in attendees.keys():
                for attendee in attendees[key]:
                    if key == "invitees":
                        yield {"committee_id":committee_id,
                               "meeting_id":meeting_id,
                               "name":attendee["name"],
                               "role":"invitees",
                               "additional_information":attendee["role"] if "role" in attendee.keys() else ""}

                    else:
                        yield {"committee_id":committee_id,
                               "meeting_id":meeting_id,
                               "name":attendee,
                               "role":key,
                               "additional_information":""}


if __name__ == "__main__":
    ParseCommitteeMeetingAttendeesProcessor.main()
