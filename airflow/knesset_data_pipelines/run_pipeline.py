import os
import datetime
import warnings
import traceback
from glob import glob
from pprint import pprint
from textwrap import dedent
from collections import defaultdict

import requests
import dataflows as DF
from ruamel import yaml
import google.cloud.storage
from bs4 import BeautifulSoup
from bs4.builder import XMLParsedAsHTMLWarning
from sqlalchemy.engine.create import create_engine

from . import config


warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)


def get_pipeline_spec(pipeline_id):
    *pipeline_path, pipeline_name = pipeline_id.split("/")
    pipeline_path = '/'.join(pipeline_path)
    source_spec_yaml = os.path.join(config.KNESSET_DATA_PIPELINES_ROOT_DIR, pipeline_path, 'knesset.source-spec.yaml')
    assert os.path.exists(source_spec_yaml)
    with open(source_spec_yaml) as f:
        source_spec = yaml.safe_load(f)
    pipeline = source_spec[pipeline_name]
    return pipeline_name, pipeline


def get_pipeline_params(pipeline_name, pipeline):
    assert pipeline.get('pipeline-type') == 'knesset dataservice', f'unknown pipeline-type: {pipeline.get("pipeline-type")}'
    pipeline_id = pipeline_name
    storage_path = "data/{}/{}".format(pipeline['schemas-bucket'], pipeline_id)
    storage_url = "http://storage.googleapis.com/knesset-data-pipelines/{}".format(storage_path)
    storage_abspath = os.path.join(config.KNESSET_PIPELINES_DATA_PATH, pipeline['schemas-bucket'], pipeline_id)
    assert 'dependencies' not in pipeline, 'pipeline dependencies are not supported'
    assert 'pre-steps' not in pipeline, 'pipeline pre-steps are not supported'
    assert not config.KNESSET_LOAD_FROM_URL, 'KNESSET_LOAD_FROM_URL is not supported'
    assert not config.DATASERVICE_LOAD_FROM_URL, 'DATASERVICE_LOAD_FROM_URL is not supported'
    assert not config.KNESSET_DATASERVICE_INCREMENTAL, 'KNESSET_DATASERVICE_INCREMENTAL is not supported'
    assert 'additional-steps' not in pipeline, 'additional-steps is not supported'
    assert 'additional-sql-tables' not in pipeline, 'additional-sql-tables is not supported'
    table_name = '{}_{}'.format(pipeline['schemas-bucket'], pipeline_id.replace('-', '_'))
    return pipeline["dataservice-parameters"], storage_url, storage_abspath, table_name
    # resource_name = pipeline_id
    # tables = {table_name: pipeline_id}
    # tables = {table_name: {'resource-name': resource_name, 'mode': 'rewrite'} for table_name, resource_name in tables.items()}
    # return [
    #     ('..datapackage_pipelines_knesset.dataservice.processors.add_dataservice_collection_resource', pipeline["dataservice-parameters"]),
    #     ('..datapackage_pipelines_knesset.common.processors.throttle', {'rows-per-page': 50, 'resource': resource_name}),
    #     ('knesset.dump_to_path', {'storage-url': storage_url, 'out-path': '../{}'.format(storage_path)}),
    #     ('knesset.dump_to_sql', {'engine': 'env://DPP_DB_ENGINE', 'tables': tables}),
    # ]


def compose_url_get(url, params=None):
    p = requests.PreparedRequest()
    p.prepare(method='GET', url=url, params=params)
    return p.url


def get_response_content(url, params, timeout, proxies):
    proxies = proxies if proxies else {}
    response = requests.get(url, params=params, timeout=timeout, proxies=proxies)
    assert response.status_code == 200, f"invalid response status code: {response.status_code}"
    return response.content


def get_soup(url, params=None, proxies=None):
    params = {} if params is None else params
    timeout = params.pop('__timeout__', config.DEFAULT_REQUEST_TIMEOUT_SECONDS)
    return BeautifulSoup(get_response_content(url, params, timeout, proxies), 'html.parser')


def get_source_field_value(type_, text, isnull):
    if isnull:
        return None
    elif type_ == '':
        return text
    elif type_ in ('edm.int32', 'edm.int16', 'edm.byte', 'edm.int64'):
        return int(text)
    elif type_ == 'edm.decimal':
        return float(text)
    elif type_ == 'edm.datetime':
        return datetime.datetime.strptime(text.split('.')[0], "%Y-%m-%dT%H:%M:%S")
    elif type_ == 'edm.boolean':
        return text == 'true'
    else:
        raise Exception(f'unknown prop type: {type_}')


def get_field_from_entry(fieldname, field, data):
    assert field['source'] == '{name}', f'invalid field source: {field["source"]}'
    source_field = data.get(fieldname.lower(), {})
    output_field_type = field['type']
    source_field_type = source_field.get('type')
    source_field_text = source_field.get('text')
    source_field_null = source_field.get('null')
    source_field_value = get_source_field_value(source_field_type, source_field_text, source_field_null)
    if output_field_type == 'integer':
        return str(int(source_field_value)) if source_field_value is not None else ''
    elif output_field_type == 'string':
        return str(source_field_value) if source_field_value is not None else ''
    elif output_field_type == 'datetime':
        if not source_field_value:
            return ''
        else:
            assert isinstance(source_field_value, datetime.datetime), f'invalid datetime value: {source_field_value}'
            return source_field_value.strftime('%Y-%m-%d %H:%M:%S')
    elif output_field_type == 'boolean':
        return 'True' if source_field_value is True else 'False'
    else:
        raise Exception(f'unknown output field type: {output_field_type}')


def get_row_from_entry(params, entry):
    data = {tag.name.split(':')[1].lower(): {
        'type': tag.attrs.get('m:type', '').lower(),
        'text': tag.text,
        'null': tag.attrs.get('m:null', '') == 'true',
    } for tag in entry.content.find('m:properties').children}
    return {fieldname: get_field_from_entry(fieldname, field, data) for fieldname, field in params['fields'].items()}


def add_dataservice_collection_resource(params, proxies=None, stats=None, limit_rows=None):
    if stats is None:
        stats = defaultdict(int)
    url_base = os.path.join(config.SERVICE_URLS[params['service-name']], params['method-name'])
    next_url = compose_url_get(url_base)
    while next_url and (not limit_rows or stats['rows'] < limit_rows):
        if stats['rows'] == 0:
            print(next_url)
        elif stats['rows'] % 1000 == 0:
            print(next_url)
            pprint(dict(stats))
        stats['urls'] += 1
        soup = get_soup(next_url, proxies=proxies)
        try:
            entries = soup.feed.find_all('entry')
        except:
            traceback.print_exc()
            entries = []
        for entry in entries:
            stats['rows'] += 1
            yield get_row_from_entry(params, entry)
        try:
            next_link = soup.find('link', rel="next")
            next_url = next_link and next_link.attrs.get('href', None)
        except Exception:
            next_url = None


def get_db_engine():
    return create_engine(
        f'postgresql+psycopg2://{config.PGSQL_USER}:{config.PGSQL_PASSWORD}@{config.PGSQL_HOST}:{config.PGSQL_PORT}/{config.PGSQL_DB}',
        echo=False
    )


def upload_to_storage(source_path, target_url, pipeline_name):
    print(f'uploading {source_path} to {target_url}')
    assert target_url.startswith('http://storage.googleapis.com/knesset-data-pipelines/')
    target_path = target_url.replace('http://storage.googleapis.com/knesset-data-pipelines/', '')
    bucket_name = 'knesset-data-pipelines'
    storage_client = google.cloud.storage.Client()
    bucket = storage_client.bucket(bucket_name)
    for filename in ('datapackage.json', f'{pipeline_name}.csv'):
        filepath = os.path.join(source_path, filename)
        assert os.path.exists(filepath), f'file not found: {filepath}'
        blob = bucket.blob(os.path.join(target_path, filename))
        blob.upload_from_filename(filepath)


def main(pipeline_id, limit_rows=None):
    limit_rows = int(limit_rows) if limit_rows else None
    pipeline_name, pipeline = get_pipeline_spec(pipeline_id)
    dataservice_params, storage_url, storage_path, table_name = get_pipeline_params(pipeline_name, pipeline)
    table_name = f'{table_name}{config.KNESSET_DATA_OUTPUT_SUFFIX}'
    storage_url = f'{storage_url}{config.KNESSET_DATA_OUTPUT_SUFFIX}'
    print(f'pipeline_id: {pipeline_id}\nstorage_url: {storage_url}\nstorage_path: {storage_path}\ntable_name: {table_name}')
    stats = defaultdict(int)
    temp_table_name = f'__temp__{table_name}'
    DF.Flow(
        add_dataservice_collection_resource(dataservice_params, stats=stats, limit_rows=limit_rows),
        DF.update_resource('res_1', name=pipeline_name, path=f'{pipeline_name}.csv'),
        DF.dump_to_path(os.path.join(config.KNESSET_PIPELINES_DATA_PATH, f'{pipeline_id}{config.KNESSET_DATA_OUTPUT_SUFFIX}')),
        DF.dump_to_sql(
            {temp_table_name: {'resource-name': pipeline_name}},
            get_db_engine(),
            batch_size=100000,
        ),
    ).process()
    with get_db_engine().connect() as conn:
        with conn.begin():
            conn.execute(dedent(f'''
                drop table if exists {table_name};
                alter table {temp_table_name} rename to {table_name};
            '''))
    upload_to_storage(os.path.join(config.KNESSET_PIPELINES_DATA_PATH, f'{pipeline_id}{config.KNESSET_DATA_OUTPUT_SUFFIX}'), storage_url, pipeline_name)
    pprint(dict(stats))


def list_pipelines():
    for source_spec_yaml in glob(os.path.join(config.KNESSET_DATA_PIPELINES_ROOT_DIR, '**/knesset.source-spec.yaml'), recursive=True):
        pipeline_path = os.path.dirname(source_spec_yaml.replace(config.KNESSET_DATA_PIPELINES_ROOT_DIR, '').lstrip('/'))
        with open(source_spec_yaml) as f:
            source_spec = yaml.safe_load(f)
        for pipeline_name, pipeline in source_spec.items():
            pipeline_id = os.path.join(pipeline_path, pipeline_name)
            pipeline_name, pipeline = get_pipeline_spec(pipeline_id)
            error = False
            try:
                get_pipeline_params(pipeline_name, pipeline)
            except Exception as e:
                if str(e) not in ['pipeline dependencies are not supported', 'unknown pipeline-type: None', 'additional-steps is not supported']:
                    raise
                error = True
            if not error:
                yield pipeline_id
