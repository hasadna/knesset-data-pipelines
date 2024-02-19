import os
import traceback
from textwrap import dedent

import dataflows as DF
from pyquery import PyQuery as pq

from .. import db, config
from ..get_retry_response_content import get_retry_response_content

URL = "https://main.knesset.gov.il/en/MK/APPS/mk/mk-personal-details"

def iterate_members():
    for member_id in range(1, 121):
        try:
            content = get_retry_response_content(
                f"{URL}/{member_id}", None, None, None, retry_num=1,
                num_retries=10, seconds_between_retries=10,
                skip_not_found_errors=True)
        except Exception:
            treaceback.print_exc()
            content = None
            print(f'failed to get {URL}/{member_id}')
        else:
            page = pq(content)
            # Hmm, the page is rendered by javascript, so the get_retry_response is empty
            import pdb;pdb.set_trace()

def main():
    table_name = 'member_english_names'
    temp_table_name = f'__temp__{table_name}'
    DF.Flow(
        iterate_members(),
        DF.update_resource(-1, name='member_english_name', path='member_english_name.csv'),
        DF.dump_to_path(os.path.join(config.KNESSET_PIPELINES_DATA_PATH, 'members', 'memger_english_names')),
        DF.dump_to_sql(
            {temp_table_name: {'resource-name': 'member_english_names'}},
            db.get_db_engine(),
            batch_size=100000,
        ),
    ).process
    with db.get_db_engine().connect() as conn:
        with conn.begin():
            conn.execute(dedent(f'''
                    drop table if exists {table_name};
                    alter table {temp_table_name} rename to {table_name};
                '''))
    
