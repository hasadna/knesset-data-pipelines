from datapackage_pipelines.wrapper import process
import logging, requests, os
from knesset_data.protocols.committee import CommitteeMeetingProtocol


def process_row(row, row_index, spec, resource_index, parameters, stats):
    if spec['name'] == 'kns_committeesession':
        row.update(mks=None, invitees=None, legal_advisors=None, manager=None)
        if (
            (not parameters.get("filter-meeting-id") or int(row["CommitteeSessionID"]) in parameters["filter-meeting-id"])
            and (not parameters.get("filter-committee-id") or int(row["CommitteeID"]) in parameters["filter-committee-id"])
            and (not parameters.get("filter-knesset-num") or int(row["KnessetNum"]) in parameters["filter-knesset-num"])
        ):
            if row["text_parsed_filename"]:
                text = None
                if os.environ.get('KNESSET_PIPELINES_DATA_PATH'):
                    protocol_text_path = os.path.join(os.environ['KNESSET_PIPELINES_DATA_PATH'],
                                                      'committees/meeting_protocols_text/{}'.format(row["text_parsed_filename"]))
                    if os.path.exists(protocol_text_path) and os.path.getsize(protocol_text_path) > 0:
                        with open(protocol_text_path) as f:
                            text = f.read()
                else:
                    protocol_text_url = "https://storage.googleapis.com/knesset-data-pipelines/data/committees/" \
                                        "meeting_protocols_text/{}".format(row["text_parsed_filename"])
                    res = requests.get(protocol_text_url)
                    if res.status_code == 200:
                        text = requests.get(protocol_text_url).content.decode("utf-8")
                if text:
                    with CommitteeMeetingProtocol.get_from_text(text) as protocol:
                        attendees = protocol.attendees
                        if attendees:
                            row.update(mks=attendees['mks'], invitees=attendees['invitees'],
                                       legal_advisors=attendees['legal_advisors'], manager=attendees['manager'])
    return row


def modify_datapackage(datapackage, parameters, stats):
    for descriptor in datapackage['resources']:
        if descriptor['name'] == 'kns_committeesession':
            descriptor['schema']['fields'] += [{"name": "mks", "type": "array"},
                                               {"name": "invitees", "type": "array"},
                                               {"name": "legal_advisors", "type": "array"},
                                               {"name": "manager", "type": "array"}, ]
    return datapackage


if __name__ == '__main__':
    process(modify_datapackage, process_row)
