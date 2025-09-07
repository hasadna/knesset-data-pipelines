import os
import shutil
from textwrap import dedent
from collections import defaultdict

import dataflows as DF

from .. import db, config


def parse_retry_error(type_, error, document_session_id, group_type_id, application_desc, stats):
    if error:
        document_session_id = str(document_session_id)
        group_type_id = str(group_type_id)
        application_desc = str(application_desc)
        ext = 'txt' if type_ == 'text' else 'csv'
        download_filepath = os.path.join(
            config.KNESSET_PIPELINES_DATA_PATH,
            'committees', 'download_document_committee_session', 'files', group_type_id,
            document_session_id[0], document_session_id[1], f'{document_session_id}.{application_desc}'
        )
        parsed_filepath = os.path.join(
            config.KNESSET_PIPELINES_DATA_PATH,
            'committees', f'meeting_protocols_{type_}', 'files',
            document_session_id[0], document_session_id[1], f'{document_session_id}.{ext}.hash'
        )
        hash_filepath = f'{parsed_filepath}.hash'
        retry_filepath = f'{parsed_filepath}.retry'
        if os.path.exists(retry_filepath):
            with open(retry_filepath, 'r') as f:
                retry_num = int(f.read().strip())
        else:
            retry_num = 0
        if retry_num >= 10:
            print(f'parse_retry_error({type_}): document session id {document_session_id} exceeded max retries')
            stats[f'parse_retry_error({type_}): exceeded max retries'] += 1
        else:
            retry_num += 1
            print(f'parse_retry_error({type_}): document session id {document_session_id} retry {retry_num}')
            stats[f'parse_retry_error({type_}): will retry'] += 1
        for filepath in [download_filepath, parsed_filepath, hash_filepath]:
            if os.path.exists(filepath):
                os.remove(filepath)
        with open(retry_filepath, 'w') as f:
            f.write(str(retry_num))


def update_row_stats(row, stats):
    document_session_id = str(row['DocumentCommitteeSessionID'])
    download_filepath = os.path.join(
        config.KNESSET_PIPELINES_DATA_PATH,
        'committees', 'download_document_committee_session', row['download_filename']
    )
    if os.path.exists(download_filepath):
        stats['download exists'] += 1
    for type_ in ['text', 'parts']:
        filepath = os.path.join(
            config.KNESSET_PIPELINES_DATA_PATH,
            'committees', f'meeting_protocols_{type_}', 'files',
            document_session_id[0], document_session_id[1], f'{document_session_id}.{"txt" if type_ == "text" else "csv"}'
        )
        if os.path.exists(filepath):
            stats[f'{type_} exists'] += 1
        if os.path.exists(f'{filepath}.hash'):
            stats[f'{type_} hash exists'] += 1


def process_rows(rows):
    stats = defaultdict(int)
    protocol_session_rows = {}
    for row in rows:
        stats['total_rows'] += 1
        # this if condition should match the one in /committees/filter_document_committee_sessions.py
        if (row['GroupTypeID'] != 23
            or row['ApplicationDesc'] != 'DOC'
            or (not row["FilePath"].lower().endswith('.doc')
                and not row["FilePath"].lower().endswith('.docx'))):
            yield row
        else:
            stats['protocol_rows'] += 1
            update_row_stats(row, stats)
            parse_retry_error('text', row['text_error'], row['DocumentCommitteeSessionID'], row['GroupTypeID'], row['ApplicationDesc'], stats)
            parse_retry_error('parts', row['parts_error'], row['DocumentCommitteeSessionID'], row['GroupTypeID'], row['ApplicationDesc'], stats)
            protocol_session_rows.setdefault(row['CommitteeSessionID'], []).append(row)
    for session_id, rows in protocol_session_rows.items():
        if len(rows) > 1:
            good_rows = [row for row in rows if row['text_filesize'] > 0]
            if len(good_rows) > 0:
                rows = good_rows
        row = rows[0]
        stats['yielded_protocol_rows'] += 1
        yield row
    for k, v in stats.items():
        print(f'{k}: {v}')


def main():
    table_name = 'committees_parsed_document_committee_sessions'
    temp_table_name = f'__temp__{table_name}'
    DF.Flow(
        DF.load(os.path.join(config.KNESSET_PIPELINES_DATA_PATH, 'committees', 'kns_documentcommitteesession', 'datapackage.json')),
        process_rows,
        DF.dump_to_path(os.path.join(config.KNESSET_PIPELINES_DATA_PATH, 'committees', table_name)),
        DF.dump_to_sql(
            {temp_table_name: {'resource-name': 'kns_documentcommitteesession'}},
            db.get_db_engine(),
            batch_size=100000,
        ),
    ).process()
    with db.get_db_engine().connect() as conn:
        with conn.begin():
            conn.execute(dedent(f'''
                drop table if exists {table_name};
                alter table {temp_table_name} rename to {table_name};
            '''))
