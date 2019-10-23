from datapackage_pipelines.wrapper import ingest, spew
from datapackage_pipelines.utilities.resources import PROP_STREAMING
import logging, requests, os
from knesset_data.protocols.committee import CommitteeMeetingProtocol
import hashlib, json
from kvfile import KVFile
from dataflows import Flow, load


BASE_HASH_OBJ = hashlib.md5()
with open('../people/committee_meeting_speaker_stats.py', 'rb') as f:
    BASE_HASH_OBJ.update(f.read())


speaker_stats_kv = KVFile()


def speaker_stats_resource():
    for k, row in speaker_stats_kv.items():
        row['CommitteeSessionID'], row['parts_crc32c'], row['part_index'] = k.split('-')
        yield row


def add_speaker_stats_row(row):
    key = '{}-{}-{}'.format(row['CommitteeSessionID'], row['parts_crc32c'], row['part_index'])
    value = {k: v for k, v in row.items() if k not in ['CommitteeSessionID', 'parts_crc32c', 'part_index']}
    speaker_stats_kv.set(key, value)


def add_speaker_stats_from_parts(protocol_parts, row):
    speaker_stats_rows = []
    for part_index, part in enumerate(protocol_parts):
        speaker_stats_row = {
            'CommitteeSessionID': row['CommitteeSessionID'],
            'parts_crc32c': row['parts_crc32c'],
            'part_index': part_index,
            'header': part['header'],
            'body_length': len(part['body']) if part['body'] else 0,
            'part_category': ''
        }
        add_speaker_stats_row(speaker_stats_row)
        speaker_stats_rows.append(speaker_stats_row)
    return speaker_stats_rows


def process_row(row, row_index, spec, resource_index, parameters, stats):
    if spec['name'] == 'kns_committeesession':
        if (
            (not parameters.get("filter-meeting-id") or int(row["CommitteeSessionID"]) in parameters["filter-meeting-id"])
            and (not parameters.get("filter-committee-id") or int(row["CommitteeID"]) in parameters["filter-committee-id"])
            and (not parameters.get("filter-knesset-num") or int(row["KnessetNum"]) in parameters["filter-knesset-num"])
        ):
            if row['parts_parsed_filename'] and row['parts_crc32c']:
                new_cache_hash, old_cache_hash, cache_hash_path, cache_hash_rows = None, None, None, None
                if os.environ.get('KNESSET_PIPELINES_DATA_PATH'):
                    m = BASE_HASH_OBJ.copy()
                    m.update(str(row['parts_crc32c']).encode())
                    new_cache_hash = m.hexdigest()
                    cache_hash_path = os.path.join(os.environ['KNESSET_PIPELINES_DATA_PATH'],
                                                   'people/committees/meeting-speaker-stats/cache_hash/{}.json'.format(row["parts_parsed_filename"]))
                    if os.path.exists(cache_hash_path):
                        with open(cache_hash_path) as f:
                            cache_data = json.load(f)
                            old_cache_hash = cache_data['hash']
                            cache_hash_rows = cache_data['rows']
                if cache_hash_path and old_cache_hash and old_cache_hash == new_cache_hash:
                    for row in cache_hash_rows:
                        add_speaker_stats_row(row)
                else:
                    protocol_parts = []
                    if os.environ.get('KNESSET_PIPELINES_DATA_PATH'):
                        protocol_parts_path = os.path.join(os.environ['KNESSET_PIPELINES_DATA_PATH'],
                                                           'committees/meeting_protocols_parts/{}'.format(row["parts_parsed_filename"]))
                        if os.path.exists(protocol_parts_path) and os.path.getsize(protocol_parts_path) > 0:
                            protocol_parts = Flow(load(protocol_parts_path)).results()[0][0]
                    else:
                        protocol_parts_url = "https://storage.googleapis.com/knesset-data-pipelines/data/committees/" \
                                             "meeting_protocols_parts/{}".format(row["parts_parsed_filename"])
                        protocol_parts = Flow(load(protocol_parts_url)).results()[0][0]
                    if len(protocol_parts) > 0:
                        speaker_stats_rows = add_speaker_stats_from_parts(protocol_parts, row)
                    else:
                        speaker_stats_rows = []
                    if cache_hash_path:
                        os.makedirs(os.path.dirname(cache_hash_path), exist_ok=True)
                        with open(cache_hash_path, 'w') as f:
                            json.dump({'hash': new_cache_hash,
                                       'rows': speaker_stats_rows}, f)
    return row


def modify_datapackage(datapackage, parameters, stats):
    datapackage['resources'].append({
        'name': 'speaker_stats',
        'path': 'speaker_stats.csv',
        PROP_STREAMING: True,
        "schema": {
            "fields": [
                {"name": n, "type": t} for n, t in [
                    ('CommitteeSessionID', 'number'),
                    ('parts_crc32c', 'string'),
                    ('part_index', 'number'),
                    ('header', 'string'),
                    ('body_length', 'number'),
                    ('part_category', 'string'),
                ]
            ]
        }
    })
    return datapackage


def generic_process_resource(rows,
                             spec,
                             resource_index,
                             parameters,
                             stats,
                             process_row):
    for row_index, row in enumerate(rows):
        row = process_row(row, row_index,
                          spec, resource_index,
                          parameters, stats)
        if row is not None:
            yield row


def generic_process_resources(resource_iterator, parameters, stats, process_row):
    for resource_index, resource in enumerate(resource_iterator):
        rows = resource
        spec = resource.spec
        yield generic_process_resource(rows, spec, resource_index, parameters, stats, process_row)
        yield speaker_stats_resource()


def process():
    stats = {}
    parameters, datapackage, resource_iterator = ingest(debug=False)
    datapackage = modify_datapackage(datapackage, parameters, stats)
    new_iter = generic_process_resources(resource_iterator, parameters, stats, process_row)
    spew(datapackage, new_iter, stats)


if __name__ == '__main__':
    process()
