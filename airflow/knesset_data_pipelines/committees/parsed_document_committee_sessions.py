import os
import shutil
from textwrap import dedent

import dataflows as DF

from .. import db, config


def legacy_fix(type_, row):
    session_id = str(row['CommitteeSessionID'])
    document_session_id = str(row['DocumentCommitteeSessionID'])
    ext = 'txt' if type_ == 'text' else 'csv'
    basepath = os.path.join(
        config.KNESSET_PIPELINES_DATA_PATH,
        'committees', f'meeting_protocols_{type_}', 'files',
    )
    legacy_file = os.path.join(
        basepath, session_id[0], session_id[1], f'{session_id}.{ext}'
    )
    legacy_hash_file = f'{legacy_file}.hash'
    legacy_hash_retry_file = f'{legacy_hash_file}.retry'
    new_file = os.path.join(
        basepath, document_session_id[0], document_session_id[1], f'{document_session_id}.{ext}'
    )
    new_hash_file = f'{new_file}.hash'
    new_relfile = os.path.join(
        'files', document_session_id[0], document_session_id[1], f'{document_session_id}.{ext}'
    )
    if os.path.exists(legacy_file):
        row[f'{type_}_parsed_filename'] = new_relfile
        shutil.move(legacy_file, new_file)
        if os.path.exists(legacy_hash_file):
            shutil.move(legacy_hash_file, new_hash_file)
    if os.path.exists(legacy_hash_file):
        os.remove(legacy_hash_file)
    if os.path.exists(legacy_hash_retry_file):
        os.remove(legacy_hash_retry_file)


def parse_retry(type_, error, document_session_id, retry_report):
    document_session_id = str(document_session_id)
    if error:
        ext = 'txt' if type_ == 'text' else 'csv'
        hash_file = os.path.join(
            config.KNESSET_PIPELINES_DATA_PATH,
            'committees', f'meeting_protocols_{type_}', 'files',
            document_session_id[0], document_session_id[1], f'{document_session_id}.{ext}.hash'
        )
        if os.path.exists(hash_file):
            hash_retry_file = f'{hash_file}.retry'
            if os.path.exists(hash_retry_file):
                with open(hash_retry_file) as f:
                    retry = int(f.read().strip())
            else:
                retry = 0
            retry += 1
            if retry > 10:
                print(f'document session {document_session_id} {type_} exceeded max retries')
                retry_report.append(f'session {document_session_id} {type_} exceeded max retries')
            else:
                with open(hash_retry_file, 'w') as f:
                    f.write(str(retry))
                os.remove(hash_file)
                print(f'document session {document_session_id} {type_} retry {retry}')


def process_rows(rows):
    retry_report = []
    protocol_session_rows = {}
    for row in rows:
        # this if condition should match the one in /committees/filter_document_committee_sessions.py
        if (row['GroupTypeID'] != 23
            or row['ApplicationDesc'] != 'DOC'
            or (not row["FilePath"].lower().endswith('.doc')
                and not row["FilePath"].lower().endswith('.docx'))):
            yield row
        else:
            # parse_retry('text', row['text_error'], row['DocumentCommitteeSessionID'], retry_report)
            # parse_retry('parts', row['parts_error'], row['DocumentCommitteeSessionID'], retry_report)
            protocol_session_rows.setdefault(row['CommitteeSessionID'], []).append(row)
    for session_id, rows in protocol_session_rows.items():
        if len(rows) > 1:
            good_rows = [row for row in rows if row['text_filesize'] > 0]
            if len(good_rows) > 0:
                rows = good_rows
        row = rows[0]
        legacy_fix('text', row)
        legacy_fix('parts', row)
        yield row


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
