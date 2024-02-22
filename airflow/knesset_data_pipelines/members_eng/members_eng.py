import os
from textwrap import dedent
import traceback
import json

import dataflows as DF
from pyquery import PyQuery as pq

from .. import db, config
from ..get_retry_response_content import get_retry_response_content

def get_members_id():
    """Return an iterable of all valid mk_individual_id
    """
    return range(1, 6000)

def iterate_members():
    for member_id in get_members_id():
        URL = f"https://knesset.gov.il/WebSiteApi/knessetapi/MKs/GetMkdetailsHeader?mkId={member_id}&languageKey=en"
        print(f"getting {URL}")
        try:
            content = get_retry_response_content(
                URL, None, None, None, retry_num=1,
                num_retries=10, seconds_between_retries=10,
                skip_not_found_errors=True)
        except Exception:
            traceback.print_exc()
            print(f'failed to get {URL}')
        else:
            data = json.loads(content)
            name = data.get('Name', '')
            if not name:
                continue
            yield {
                "NameEng": name,
                "mk_individual_id": member_id,
            }

def main():
    table_name = 'member_english_names'
    temp_table_name = f'__temp__{table_name}'
    DF.Flow(
        iterate_members(),
        DF.update_resource(-1, name='member_english_names', path='member_english_names.csv'),
        DF.dump_to_path(os.path.join(config.KNESSET_PIPELINES_DATA_PATH, 'members', 'member_english_names')),
        DF.dump_to_sql(
            {temp_table_name: {'resource-name': 'member_english_names'}},
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
    
