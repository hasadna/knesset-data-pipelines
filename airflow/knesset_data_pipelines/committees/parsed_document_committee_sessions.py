import os
from textwrap import dedent

import dataflows as DF

from .. import db, config


def parse_retry(type_, error, session_id, retry_report):
    session_id = str(session_id)
    if error:
        ext = 'txt' if type_ == 'text' else 'csv'
        hash_file = os.path.join(
            config.KNESSET_PIPELINES_DATA_PATH,
            'committees', f'meeting_protocols_{type_}', 'files',
            session_id[0], session_id[1], f'{session_id}.{ext}.hash'
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
                print(f'session {session_id} {type_} exceeded max retries')
                retry_report.append(f'session {session_id} {type_} exceeded max retries')
            else:
                with open(hash_retry_file, 'w') as f:
                    f.write(str(retry))
                os.remove(hash_file)
                print(f'session {session_id} {type_} retry {retry}')


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
            parse_retry('text', row['text_error'], row['CommitteeSessionID'], retry_report)
            parse_retry('parts', row['parts_error'], row['CommitteeSessionID'], retry_report)
            protocol_session_rows.setdefault(row['CommitteeSessionID'], []).append(row)
    for session_id, rows in protocol_session_rows.items():
        if len(rows) > 1:
            good_rows = [row for row in rows if row['text_filesize'] > 0]
            if len(good_rows) > 0:
                rows = good_rows
        yield rows[0]


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
