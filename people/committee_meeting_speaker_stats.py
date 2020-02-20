from datapackage_pipelines.wrapper import ingest, spew
from datapackage_pipelines.utilities.resources import PROP_STREAMING
import logging, requests, os
from knesset_data.protocols.committee import CommitteeMeetingProtocol
import hashlib, json
from kvfile import KVFile
from dataflows import Flow, load
import csv
from fuzzywuzzy import fuzz
import traceback


BASE_HASH_OBJ = hashlib.md5()
with open('../people/committee_meeting_speaker_stats.py', 'rb') as f:
    BASE_HASH_OBJ.update(f.read())


speaker_stats_kv = KVFile()


mk_individual_factions = {}
mk_individual_names = {}


def speaker_stats_resource():
    for k, row in speaker_stats_kv.items():
        # logging.info(row)
        row['CommitteeSessionID'], row['parts_crc32c'], row['part_index'] = k.split('-')
        yield row


def add_speaker_stats_row(row):
    key = '{}-{}-{}'.format(row['CommitteeSessionID'], row['parts_crc32c'], row['part_index'])
    value = {k: v for k, v in row.items() if k not in ['CommitteeSessionID', 'parts_crc32c', 'part_index']}
    speaker_stats_kv.set(key, value)


def parse_part_header(part, session, parameters):
    header = part['header']
    category = ''
    mk_individual_id = None
    mk_individual_faction = None
    if 'יו"ר' in header:
        category = 'chairperson'
        header = header.replace('היו"ר', '')
        header = header.replace('יו"ר', '')
        mk_individual_id, mk_individual_faction = get_mk_individual_id_faction(header, session)
    else:
        for mk in session['mks']:
            if fuzz.token_set_ratio(mk, header, full_process=True) > parameters['MK_MATCH_RATIO']:
                category = 'mk'
                mk_individual_id, mk_individual_faction = get_mk_individual_id_faction(mk, session)
                break
        if category == '':
            for legal_advisor in session['legal_advisors']:
                if fuzz.token_set_ratio(legal_advisor, header, full_process=True) > parameters['LEGAL_ADVISOR_MATCH_RATIO']:
                    category = 'legal_advisor'
                    break
    return category, header.strip(), mk_individual_id, mk_individual_faction


def get_invitee_name_role(header, session, parameters):
    for invitee in session['invitees']:
        name = invitee.get('name', '')
        role = invitee.get('role', '')
        name_role = ' - '.join([name, role])
        if fuzz.token_set_ratio(header, name_role, full_process=True) > parameters['INVITEE_MATCH_RATIO']:
            return name_role
    return ''


def add_speaker_stats_from_parts(protocol_parts, row, stats, parameters):
    speaker_stats_rows = []
    for part_index, part in enumerate(protocol_parts):
        part_categories = set()
        part_category, header, mk_individual_id, mk_individual_faction = parse_part_header(part, row, parameters)
        if part_category:
            part_categories.add(part_category)
        name_role = get_invitee_name_role(header, row, parameters)
        if name_role:
            misrad_hamishpatim_role_name = 'משרד המשפטים'
            for cat in [
                {
                    'name': misrad_hamishpatim_role_name,
                    'role_name_match_strings': ['משרד המשפטים'],
                },
                {
                    'name': 'משרד ממשלתי אחר',
                    'role_name_match_strings': ['משרד ה', 'משרד ל', 'המשרד ל'],
                    'not_role': misrad_hamishpatim_role_name,
                    'match_ratio': parameters['NAME_ROLE_OFFICE_MATCH_RATIO']
                },
                {
                    'name': 'משפטן',
                    'role_name_match_strings': [
                        'יועץ משפטי', 'יועמ"ש', 'עו"ד', 'יועצת משפטית', 'עורך דין', 'עורכת דין', 'יעוץ משפטי'
                    ],
                }
            ]:
                if cat.get('not_role') and cat['not_role'] in part_categories:
                    continue
                for s in cat['role_name_match_strings']:
                    if fuzz.token_set_ratio(s, name_role, full_process=True) > cat.get('match_ratio', parameters['NAME_ROLE_DEFAULT_MATCH_RATIO']):
                        part_categories.add(cat['name'])
        speaker_stats_row = {
            'CommitteeSessionID': row['CommitteeSessionID'],
            'parts_crc32c': row['parts_crc32c'],
            'part_index': part_index,
            'header': header,
            'body_length': len(part['body']) if part['body'] else 0,
            'body_num_words': len(part['body'].split(' ')) if part['body'] else 0,
            'part_categories': ','.join(part_categories),
            'name_role': name_role,
            'mk_individual_id': mk_individual_id,
            'mk_individual_faction': mk_individual_faction
        }
        stats['num_parts'] += 1
        add_speaker_stats_row(speaker_stats_row)
        speaker_stats_rows.append(speaker_stats_row)
    return speaker_stats_rows


def get_mk_individual_faction(mk_id, session):
    for faction in mk_individual_factions.get(mk_id, []):
        if faction['start_date'] < session['StartDate'].date():
            if not faction['finish_date'] or faction['finish_date'] > session['StartDate'].date():
                return faction['name']
    return None


def get_mk_individual_id_faction(name, session):
    for tmp_name, tmp_id in mk_individual_names.items():
        if fuzz.token_set_ratio(tmp_name, name, full_process=True) > 85:
            faction = get_mk_individual_faction(tmp_id, session)
            if faction:
                return tmp_id, faction
    return None, None


def process_row(row, row_index, spec, resource_index, parameters, stats):
    if spec['name'] == 'mk_individual_factions':
        mk_individual_factions.setdefault(row['mk_individual_id'], []).append({
            'name': row['faction_name'],
            'start_date': row['start_date'],
            'finish_date': row['finish_date'],
        })
    elif spec['name'] == 'mk_individual_names':
        for name in row['names']:
            mk_individual_names[name] = row['mk_individual_id']
    elif spec['name'] == 'kns_committeesession':
        if (
            (not parameters.get("filter-meeting-id") or int(row["CommitteeSessionID"]) in parameters["filter-meeting-id"])
            and (not parameters.get("filter-committee-id") or int(row["CommitteeID"]) in parameters["filter-committee-id"])
            and (not parameters.get("filter-knesset-num") or int(row["KnessetNum"]) in parameters["filter-knesset-num"])
        ):
            if row['parts_parsed_filename'] and row['parts_crc32c']:
                if stats['num_sessions'] % 1000 == 1:
                    logging.info(stats)
                stats['num_sessions'] += 1
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
                    if cache_hash_rows and len(cache_hash_rows) > 0:
                        # logging.info('loading {} parts from cache, first part: {}'.format(len(cache_hash_rows), cache_hash_rows[0]))
                        for cache_hash_row in cache_hash_rows:
                            stats['num_parts_from_cache'] += 1
                            add_speaker_stats_row(cache_hash_row)
                    # else:
                        # logging.warning('loading 0 parts from cache')
                else:
                    protocol_parts = []
                    if os.environ.get('KNESSET_PIPELINES_DATA_PATH'):
                        protocol_parts_path = os.path.join(os.environ['KNESSET_PIPELINES_DATA_PATH'],
                                                           'committees/meeting_protocols_parts/{}'.format(row["parts_parsed_filename"]))
                        # logging.info('loading from protocol parts: {}'.format(protocol_parts_path))
                        if os.path.exists(protocol_parts_path) and os.path.getsize(protocol_parts_path) > 0:
                            try:
                                with open(protocol_parts_path) as protocol_parts_file:
                                    for i, part_row in enumerate(csv.reader(protocol_parts_file)):
                                        if i > 0:
                                            protocol_parts.append({'header': part_row[0], 'body': part_row[1]})
                                # protocol_parts = Flow(load(protocol_parts_path)).results()[0][0]
                            except Exception as e:
                                logging.exception('exception parsing protocol parts for CommitteeSessionID {}'.format(row["CommitteeSessionID"]))
                                protocol_parts = []
                        # else:
                        #     logging.warning('path does not exist: {}'.format(protocol_parts_path))
                    else:
                        protocol_parts_url = "https://storage.googleapis.com/knesset-data-pipelines/data/committees/" \
                                             "meeting_protocols_parts/{}".format(row["parts_parsed_filename"])
                        # logging.info('loading from protocol parts url: {}'.format(protocol_parts_url))
                        protocol_parts = Flow(load(protocol_parts_url)).results()[0][0]
                    if len(protocol_parts) > 0:
                        # logging.info('Loaded {} protocol parts, first part: {}'.format(len(protocol_parts), protocol_parts[0]))
                        try:
                            speaker_stats_rows = add_speaker_stats_from_parts(protocol_parts, row, stats, parameters)
                        except Exception:
                            logging.error('Failed to get speaker stats rows for {}'.format(row["parts_parsed_filename"]))
                            traceback.print_exc()
                            speaker_stats_rows = []
                    else:
                        # logging.info("Loaded 0 protocol parts")
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
                    ('body_num_words', 'number'),
                    ('part_categories', 'string'),
                    ('name_role', 'string'),
                    ('mk_individual_id', 'number'),
                    ('mk_individual_faction', 'string'),
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
    stats = {
        'num_parts': 0,
        'num_parts_from_cache': 0,
        'num_sessions': 0
    }
    parameters, datapackage, resource_iterator = ingest(debug=False)
    datapackage = modify_datapackage(datapackage, parameters, stats)
    new_iter = generic_process_resources(resource_iterator, parameters, stats, process_row)
    spew(datapackage, new_iter, stats)


if __name__ == '__main__':
    process()
