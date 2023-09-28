import os
import traceback
from textwrap import dedent

import dataflows as DF
from pyquery import PyQuery as pq

from .common import get_committees_tree
from .. import db, config
from ..get_retry_response_content import get_retry_response_content


ALLOWED_COMMITTEE_NAME_CONTAINS = (
    'האישה',
    'בנשים',
    ' נשים',
    'הנשים',
)
WOMEN_SLUG_COMMITTEE_IDS = [2156, 2227, 4200]
URL_TEMPLATE = 'https://main.knesset.gov.il/Activity/committees/{slug}/Pages/CommitteeMaterial.aspx?ItemID={id}'


def get_committee_url_slug(committee):
    if committee['committee_id'] in WOMEN_SLUG_COMMITTEE_IDS or committee['root_committee_id'] in WOMEN_SLUG_COMMITTEE_IDS:
        return 'Women'
    else:
        print(f"WARNING! committee doesn't have a known url slug, assuming 'Women' slug: {committee['committee_id']}")
        return 'Women'


def is_allowed_committee(committee, committees):
    for name_contains in ALLOWED_COMMITTEE_NAME_CONTAINS:
        if name_contains in committee['name']:
            return True
        if committee['category_desc'] and name_contains in committee['category_desc']:
            return True
        for parent_committee_id in committee['parent_committee_ids']:
            if is_allowed_committee(committees[parent_committee_id], committees):
                return True
    return False


def iterate_new_titles():
    committees = get_committees_tree()
    committees = {
        committee_id: committee
        for committee_id, committee
        in committees.items()
        if is_allowed_committee(committee, committees)
    }
    with db.get_db_engine().connect() as conn:
        for row in conn.execute(dedent('''
            select
                sess."CommitteeSessionID" committee_session_id,
                sess."CommitteeID" committee_id
            from
                committees_kns_documentcommitteesession doc
                join committees_kns_committeesession sess
                    on sess."CommitteeSessionID" = doc."CommitteeSessionID"
            where
                doc."GroupTypeID" = 87
                and doc."FilePath" is not null
                and sess."StartDate" > '2019-01-01'
            group by sess."CommitteeSessionID", sess."CommitteeID"
        ''')):
            committee = committees.get(row.committee_id)
            if not committee:
                continue
            committee['url_slug'] = get_committee_url_slug(committee)
            assert committee['url_slug']
            for title in get_titles(committee, row):
                yield {
                    'DocumentCommitteeSessionID': 0,
                    'CommitteeSessionID': int(row.committee_session_id),
                    'CommitteeID': int(row.committee_id),
                    'FilePath': str(title['FilePath']),
                    'title': str(title['title']),
                }


def get_titles(committee, row):
    url = URL_TEMPLATE.format(slug=committee['url_slug'], id=row['committee_session_id'])
    print(f'get_titles: {url}')
    try:
        content = get_retry_response_content(url, None, None, None, retry_num=1, num_retries=10,
                                             seconds_between_retries=10,
                                             skip_not_found_errors=True)
    except Exception:
        traceback.print_exc()
        content = None
        print('failed to get background material titles for {} {}'.format(committee['url_slug'], row['committee_session_id']))
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
