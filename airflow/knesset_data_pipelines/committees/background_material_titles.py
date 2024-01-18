import os
import traceback
from textwrap import dedent

import dataflows as DF
from pyquery import PyQuery as pq

from .common import get_committees_tree
from .. import db, config
from ..get_retry_response_content import get_retry_response_content


def iterate_new_titles():
    committees = get_committees_tree()
    with db.get_db_engine().connect() as conn:
        for row in list(conn.execute(dedent('''
            select
                sess."CommitteeSessionID" committee_session_id,
                sess."CommitteeID" committee_id,
                sess."SessionUrl" session_url
            from
                committees_kns_documentcommitteesession doc
                join committees_kns_committeesession sess
                    on sess."CommitteeSessionID" = doc."CommitteeSessionID"
            where
                doc."GroupTypeID" = 87
                and doc."FilePath" is not null
            group by sess."CommitteeSessionID", sess."CommitteeID", sess."SessionUrl"
        '''))):
            committee = committees.get(row.committee_id)
            if not committee:
                continue
            for title in get_titles(committee, row):
                yield {
                    'DocumentCommitteeSessionID': 0,
                    'CommitteeSessionID': int(row.committee_session_id),
                    'CommitteeID': int(row.committee_id),
                    'FilePath': str(title['FilePath']),
                    'title': str(title['title']),
                }


def get_titles_from_committee_material(committee, row, committee_material_url):
    print(f'get_titles_from_committee_material: {committee_material_url}')
    try:
        content = get_retry_response_content(
            f'https://main.knesset.gov.il{committee_material_url}', None, None, None, retry_num=1, num_retries=10,
            seconds_between_retries=10,
            skip_not_found_errors=True
        )
    except Exception:
        traceback.print_exc()
        content = None
        print(f'failed to get background material titles for {committee_material_url}')
    if content:
        page = pq(content)
        yielded_rows = set()
        for aelt in map(pq, page.find('a')):
            file_path = aelt.attr('href')
            if file_path and file_path.strip().startswith('https://fs.knesset.gov.il/'):
                title = aelt.text()
                row = {'FilePath': file_path, 'title': title}
                if f'{row["FilePath"]}--{row["title"]}' not in yielded_rows:
                    yield row
                    yielded_rows.add(f'{row["FilePath"]}--{row["title"]}')
        if len(yielded_rows) > 0:
            print(f'got {len(yielded_rows)} titles')


def get_titles(committee, row):
    print(f'get_titles: {row.session_url}')
    try:
        session_content = get_retry_response_content(
            row.session_url, None, None, None, retry_num=1, num_retries=10,
            seconds_between_retries=10, skip_not_found_errors=True
        )
    except Exception:
        traceback.print_exc()
        session_content = None
        print(f'failed to get background material titles session url for {row.session_url}')
    if session_content:
        page = pq(session_content)
        yielded_rows = set()
        for aelt in map(pq, page.find('a')):
            contents = ''.join(map(str, aelt.contents()))
            if 'חומר' in contents and 'רקע' in contents and aelt.attr.href.strip().endswith(f'CommitteeMaterial.aspx?ItemID={row.committee_session_id}'):
                yield from get_titles_from_committee_material(committee, row, aelt.attr.href.strip())


def main():
    table_name = 'committees_document_background_material_titles'
    temp_table_name = f'__temp__{table_name}'
    DF.Flow(
        iterate_new_titles(),
        DF.update_resource(-1, name='document_background_material_titles', path='document_background_material_titles.csv'),
        DF.dump_to_path(os.path.join(config.KNESSET_PIPELINES_DATA_PATH, 'committees', 'background_material_titles')),
        DF.dump_to_sql(
            {temp_table_name: {'resource-name': 'document_background_material_titles'}},
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
