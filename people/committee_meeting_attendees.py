from datapackage_pipelines.wrapper import process
import logging, requests, os
from knesset_data.protocols.committee import CommitteeMeetingProtocol
import hashlib, json


BASE_HASH_OBJ = hashlib.md5()
with open('../Pipfile.lock') as f:
    BASE_HASH_OBJ.update(str(json.load(f)['default']['knesset-data']['hashes']).encode())


def process_row(row, row_index, spec, resource_index, parameters, stats):
    if spec['name'] == 'kns_committeesession':
        row.update(mks=None, invitees=None, legal_advisors=None, manager=None)
        if (
            (not parameters.get("filter-meeting-id") or int(row["CommitteeSessionID"]) in parameters["filter-meeting-id"])
            and (not parameters.get("filter-committee-id") or int(row["CommitteeID"]) in parameters["filter-committee-id"])
            and (not parameters.get("filter-knesset-num") or int(row["KnessetNum"]) in parameters["filter-knesset-num"])
        ):
            if row["text_parsed_filename"]:
                new_cache_hash, old_cache_hash, cache_hash_path, cache_hash_row = None, None, None, None
                if os.environ.get('KNESSET_PIPELINES_DATA_PATH'):
                    m = BASE_HASH_OBJ.copy()
                    m.update(str(row['text_crc32c']).encode())
                    m.update(str(row['parts_crc32c']).encode())
                    new_cache_hash = m.hexdigest()
                    cache_hash_path = os.path.join(os.environ['KNESSET_PIPELINES_DATA_PATH'],
                                                   'people/committees/meeting-attendees/cache_hash/{}.json'.format(row["text_parsed_filename"]))
                    if os.path.exists(cache_hash_path):
                        with open(cache_hash_path) as f:
                            cache_data = json.load(f)
                            old_cache_hash = cache_data['hash']
                            cache_hash_row = cache_data['row']
                if cache_hash_path and old_cache_hash and old_cache_hash == new_cache_hash:
                    row.update(**cache_hash_row)
                else:
                    logging.info('getting attendees for meeting {}'.format(row['CommitteeSessionID']))
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
                            text = res.content.decode("utf-8")
                    update_row = dict(mks=None, invitees=None, legal_advisors=None, manager=None)
                    if text:
                        with CommitteeMeetingProtocol.get_from_text(text) as protocol:
                            attendees = protocol.attendees
                            if attendees:
                                update_row = dict(mks=attendees['mks'],
                                                  invitees=attendees['invitees'],
                                                  legal_advisors=attendees['legal_advisors'],
                                                  manager=attendees['manager'],
                                                  financial_advisors=attendees.get('financial_advisors', []))
                                row.update(**update_row)
                    if cache_hash_path:
                        os.makedirs(os.path.dirname(cache_hash_path), exist_ok=True)
                        with open(cache_hash_path, 'w') as f:
                            json.dump({'hash': new_cache_hash,
                                       'row': update_row}, f)
    return row


def modify_datapackage(datapackage, parameters, stats):
    for descriptor in datapackage['resources']:
        if descriptor['name'] == 'kns_committeesession':
            descriptor['schema']['fields'] += [{"name": "mks", "type": "array"},
                                               {"name": "invitees", "type": "array"},
                                               {"name": "legal_advisors", "type": "array"},
                                               {"name": "manager", "type": "array"},
                                               {"name": "financial_advisors", "type": "array"}]
    return datapackage


if __name__ == '__main__':
    process(modify_datapackage, process_row)
