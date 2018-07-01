from datapackage_pipelines.wrapper import ingest, spew
import logging, requests, os
from knesset_data.protocols.committee import CommitteeMeetingProtocol


parameters, datapackage, resources = ingest()
aggregations = {"stats": {}}
kns_committeesession_resource, kns_committeesession_descriptor = None, None


for descriptor, resource in zip(datapackage["resources"], resources):
    if descriptor["name"] == "kns_committeesession":
        kns_committeesession_descriptor, kns_committeesession_resource = descriptor, resource
    else:
        for row in resource:
            pass


def get_kns_committeesession_resource():
    for committeesession_row in kns_committeesession_resource:
        if (
            (not parameters.get("filter-meeting-id") or int(committeesession_row["CommitteeSessionID"]) in parameters["filter-meeting-id"])
            and (not parameters.get("filter-committee-id") or int(committeesession_row["CommitteeID"]) in parameters["filter-committee-id"])
            and (not parameters.get("filter-knesset-num") or int(committeesession_row["KnessetNum"]) in parameters["filter-knesset-num"])
        ):
            # text_file_name	                                            text_file_size
            # data/committees/meeting_protocols_text/files/5/7/570611.txt	72817
            if committeesession_row["text_filename"]:
                text = None
                if os.environ.get('KNESSET_PIPELINES_DATA_PATH'):
                    protocol_text_path = os.path.join(os.environ['KNESSET_PIPELINES_DATA_PATH'],
                                                      'committees/meeting_protocols_text/{}'.format(committeesession_row["text_filename"]))
                    if os.path.exists(protocol_text_path) and os.path.getsize(protocol_text_path) > 0:
                        with open(protocol_text_path) as f:
                            text = f.read()
                else:
                    protocol_text_url = "https://storage.googleapis.com/knesset-data-pipelines/data/committees/meeting_protocols_text/{}".format(committeesession_row["text_filename"])
                    res = requests.get(protocol_text_url)
                    if res.status_code == 200:
                        text = requests.get(protocol_text_url).content.decode("utf-8")
                if text:
                    with CommitteeMeetingProtocol.get_from_text(text) as protocol:
                        committeesession_row.update(protocol.attendees)
                    yield committeesession_row


kns_committeesession_descriptor["schema"]["fields"] += [{"name": "mks", "type": "array"},
                                                        {"name": "invitees", "type": "array"},
                                                        {"name": "legal_advisors", "type": "array"},
                                                        {"name": "manager", "type": "array"},]


spew(dict(datapackage, resources=[kns_committeesession_descriptor]),
     [get_kns_committeesession_resource()],
     aggregations["stats"])
