import os
from textwrap import dedent

import dataflows as DF

from .. import db, config


def process_rows(rows):
    protocol_session_rows = {}
    for row in rows:
        # this if condition should match the one in /committees/filter_document_committee_sessions.py
        if (row['GroupTypeID'] != 23
            or row['ApplicationDesc'] != 'DOC'
            or (not row["FilePath"].lower().endswith('.doc')
                and not row["FilePath"].lower().endswith('.docx'))):
            yield row
        else:
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
