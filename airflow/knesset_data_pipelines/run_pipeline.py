import os
import time
import json
import shutil
import random
import datetime
import tempfile
import warnings
import traceback
import subprocess
import itertools
from glob import glob
from pprint import pprint
from textwrap import dedent
from collections import defaultdict
import pickle
import functools

import requests
import dataflows as DF
from ruamel import yaml
import google.cloud.storage
from bs4 import BeautifulSoup
from bs4.builder import XMLParsedAsHTMLWarning

from . import config, db


RECOVERABLE_SERVER_ERRORS = [500, 504]
RECOVERABLE_THROTTLE_ERRORS = [500, 503, 403, 504]

# these errors indicate that the pipeline cannot run using the standard dataservice flow but have to run via Docker
UNSUPPORTED_PIPELINE_PARAMS_ERRORS = ['pipeline dependencies are not supported', 'unknown pipeline-type: None', 'additional-steps is not supported']

PIPELINES_DEV_DOCKER_IMAGE = 'orihoch/knesset-data-pipelines@sha256:329c7619fbdb4603d485df327c17cec556bc1ece1db2f11bc64854e94a5ce88a'

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)


class RequestThrottledException(Exception):
    pass


def post_process_airflow_pipeline(pipeline_path, pipeline_name, pipeline):
    if 'schemas-bucket' not in pipeline:
        pipeline['schemas-bucket'] = pipeline_path
    return pipeline


def get_pipeline_spec(pipeline_id):
    *pipeline_path, pipeline_name = pipeline_id.split("/")
    pipeline_path = '/'.join(pipeline_path)
    source_spec_yaml = os.path.join(config.KNESSET_DATA_PIPELINES_ROOT_DIR, pipeline_path, 'knesset.source-spec.yaml')
    if os.path.exists(source_spec_yaml):
        with open(source_spec_yaml) as f:
            source_spec = yaml.safe_load(f)
        if pipeline_name in source_spec:
            return pipeline_name, source_spec[pipeline_name]
    source_spec_yaml = os.path.join(config.KNESSET_DATA_PIPELINES_ROOT_DIR, 'airflow/pipelines', pipeline_path, f'{pipeline_name}.yaml')
    if os.path.exists(source_spec_yaml):
        with open(source_spec_yaml) as f:
            return pipeline_name, post_process_airflow_pipeline(pipeline_path, pipeline_name, yaml.safe_load(f))
    raise Exception(f'pipeline {pipeline_id} not found')


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


def try_get_pipeline_params(pipeline_name, pipeline):
    error = False
    dataservice_params, storage_url, storage_path, table_name = None, None, None, None
    try:
        dataservice_params, storage_url, storage_path, table_name = get_pipeline_params(pipeline_name, pipeline)
    except Exception as e:
        if str(e) not in UNSUPPORTED_PIPELINE_PARAMS_ERRORS:
            raise
        error = True
    return error, dataservice_params, storage_url, storage_path, table_name


def compose_url_get(url, params=None):
    p = requests.PreparedRequest()
    p.prepare(method='GET', url=url, params=params)
    return p.url


def get_response_content(url, params, timeout, proxies, retry_num=0):
    proxies = proxies if proxies else {}
    recoverable_error = None
    try:
        response = requests.get(url.replace("'", "%27"), params=params, timeout=timeout, proxies=proxies)
    except requests.exceptions.ReadTimeout:
        recoverable_error = 'ReadTimeout'
    if recoverable_error is None and int(response.status_code) in RECOVERABLE_THROTTLE_ERRORS:
        recoverable_error = response.status_code
    if recoverable_error:
        if retry_num < 5:
            retry_num += 1
            sleep_seconds = (random.randint(5, 30) + (retry_num * retry_num / 2)) * 60
            print(f'got {recoverable_error}, sleeping {sleep_seconds} seconds and retrying ({retry_num}/5)')
            time.sleep(sleep_seconds)
            return get_response_content(url, params, timeout, proxies, retry_num)
        else:
            raise RequestThrottledException()
    return int(response.status_code), response.content


def get_soup(url, params=None, proxies=None):
    params = {} if params is None else params
    timeout = params.pop('__timeout__', config.DEFAULT_REQUEST_TIMEOUT_SECONDS)
    status_code, content = get_response_content(url, params, timeout, proxies)
    soup = BeautifulSoup(content, 'html.parser') if status_code == 200 else None
    return status_code, soup


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


def get_field_from_entry(fieldname, field, data, v4=False):
    try:
        if field['source'] == '{name}':
            if v4 and field.get('primaryKey'):
                field_source = 'ID'
            else:
                field_source = fieldname
        else:
            field_source = field['source']
        output_field_type = field['type']
        if v4:
            source_field_value = data.get(field_source.lower())
        else:
            source_field = data.get(field_source.lower(), {})
            source_field_type = source_field.get('type')
            source_field_text = source_field.get('text')
            source_field_null = source_field.get('null')
            source_field_value = get_source_field_value(source_field_type, source_field_text, source_field_null)
        if output_field_type == 'integer':
            return int(source_field_value) if source_field_value is not None else None
        elif output_field_type == 'number':
            return float(source_field_value) if source_field_value is not None else None
        elif output_field_type == 'string':
            return str(source_field_value) if source_field_value is not None else ''
        elif output_field_type == 'datetime':
            if not source_field_value:
                return None
            elif v4:
                split_on = '.' if '.' in source_field_value else '+'
                return datetime.datetime.strptime(source_field_value.split(split_on)[0], "%Y-%m-%dT%H:%M:%S")
            else:
                assert isinstance(source_field_value, datetime.datetime), f'invalid datetime value: {source_field_value}'
                return source_field_value
        elif output_field_type == 'boolean':
            if source_field_value is None:
                return None
            else:
                return True if source_field_value else False
        elif output_field_type == 'date':
            if not source_field_value:
                return None
            elif v4:
                return datetime.datetime.strptime(source_field_value.split('.')[0], "%Y-%m-%dT%H:%M:%S").date()
            else:
                assert isinstance(source_field_value, datetime.date), f'invalid date value: {source_field_value}'
                return source_field_value
        else:
            raise Exception(f'unknown output field type: {output_field_type}')
    except Exception as e:
        raise Exception(f'fieldname: {fieldname}\nfield: {field}\ndata: {data}\nv4: {v4}') from e


def get_row_from_entry(params, entry, v4=False):
    if v4:
        data = {k.lower(): v for k, v in entry.items()}
    else:
        data = {tag.name.split(':')[1].lower(): {
            'type': tag.attrs.get('m:type', '').lower(),
            'text': tag.text,
            'null': tag.attrs.get('m:null', '') == 'true',
        } for tag in entry.content.find('m:properties').children}
    return {fieldname: get_field_from_entry(fieldname, field, data, v4=v4) for fieldname, field in params['fields'].items()}


def get_key_row_from_entry(params, entry, v4=False):
    row = get_row_from_entry(params, entry, v4)
    primary_keys = set()
    for field_name, field in params['fields'].items():
        if field.get('primaryKey'):
            primary_keys.add(field_name)
    key = ';'.join([str(row[k]) for k in sorted(list(primary_keys))])
    assert len(key) > 0, f'unexpected key ({key}): {params} {entry}'
    return {
        'key': key,
        'row': row,
    }


def get_next_skiptoken(first_skiptoken, i, processed_entry_ids):
    if len(processed_entry_ids) > i:
        skiptoken = processed_entry_ids[-(i+1)]
    else:
        skiptoken = processed_entry_ids[0] - i - len(processed_entry_ids)
    assert skiptoken > 0, f'failed to find next skiptoken starting from {first_skiptoken} after {i} tries'
    return skiptoken


def get_soup_handle_server_error(first_url, processed_entry_ids=None, **kwargs):
    try:
        first_skiptoken = int(first_url.split('$skiptoken=')[1].split('L')[0])
    except Exception as e:
        raise Exception(f'failed to parse integer skiptoken for url {first_url}') from e
    for i in range(1, 1001):
        skiptoken = get_next_skiptoken(first_skiptoken, i, processed_entry_ids)
        url = first_url.replace(f'$skiptoken={first_skiptoken}', f'$skiptoken={skiptoken}')
        print(f'trying to bypass server error with url {url}')
        status_code, soup = get_soup(url, **kwargs)
        if status_code == 200:
            print('success')
            return soup
        else:
            assert int(status_code) in RECOVERABLE_SERVER_ERRORS, f'got unexpected status code {status_code} for url {url} (starting from skiptoken {first_skiptoken})'
    raise Exception(f'failed to find successful response starting from url {first_url}')


def add_dataservice_collection_resource_odata_v4(params, proxies, stats, limit_rows=None):
    url_base = os.path.join(config.SERVICE_URLS_V4[params['service-name']], params['method-name'])
    timeout = params.pop('__timeout__', config.DEFAULT_REQUEST_TIMEOUT_SECONDS_V4)
    odata_count = None
    skip = None
    while True:
        if skip is None:
            url = f'{url_base}?$count=true'
        else:
            url = f'{url_base}?$skip={skip}'
        print(url)
        status_code, content = get_response_content(url, params, timeout, proxies)
        assert status_code == 200, f'unexpected status code: {status_code} for url {url}\n{content}'
        try:
            res = json.loads(content)
        except Exception as e:
            raise Exception(f'failed to parse json response for url {url}\n{content}') from e
        num_entries = 0
        for entry in (res if isinstance(res, list) else res['value']):
            stats['rows'] += 1
            yield get_key_row_from_entry(params, entry, v4=True)
            num_entries += 1
        skip = num_entries if skip is None else skip + num_entries
        if odata_count is None and isinstance(res, dict) and '@odata.count' in res:
            odata_count = res['@odata.count']
            assert odata_count >= 0, f'invalid count: {odata_count} for url {url}\n{content}'
        if num_entries == 0:
            break
        if limit_rows and stats['rows'] >= limit_rows:
            break
    assert limit_rows or odata_count is None or stats['rows'] == odata_count, f'invalid rows count: {stats["rows"]} != {odata_count} for url {url}'


def add_dataservice_collection_resource(params, proxies=None, stats=None, limit_rows=None, stop_on_throttled_error=False, start_url=None, load_from=None):
    if stats is None:
        stats = defaultdict(int)
    if params.get('odata-v4', True):
        assert not start_url and not load_from and not stop_on_throttled_error, 'odata-v4 does not support start_url, load_from, stop_on_throttled_error'
        yield from add_dataservice_collection_resource_odata_v4(params, proxies, stats, limit_rows)
        return
    if load_from:
        print(f'loading from {load_from}')
        for res in DF.Flow(DF.load(os.path.join(load_from, 'datapackage.json'))).datastream().res_iter.get_iterator():
            for row in res:
                stats['rows'] += 1
                yield row
        pprint(dict(stats))
    if start_url:
        next_url = start_url
    else:
        url_base = os.path.join(config.SERVICE_URLS[params['service-name']], params['method-name'])
        next_url = compose_url_get(url_base)
    has_valid_entry_ids = True
    processed_entry_ids = []
    while next_url and (not limit_rows or stats['rows'] < limit_rows):
        if stats['rows'] == 0:
            print(next_url)
        elif stats['rows'] % 1000 == 0:
            print(next_url)
            pprint(dict(stats))
        stats['urls'] += 1
        try:
            try:
                status_code, soup = get_soup(next_url, proxies=proxies)
            except RequestThrottledException:
                if has_valid_entry_ids:
                    traceback.print_exc()
                    print(f'got throttled error for url {next_url}, will try to handle it as server error {RECOVERABLE_SERVER_ERRORS[0]}')
                    status_code = RECOVERABLE_SERVER_ERRORS[0]
                else:
                    print(f'got throttled error for url {next_url}, but has_valid_entry_ids is False, will raise the exception')
                    raise
            if int(status_code) in RECOVERABLE_SERVER_ERRORS and has_valid_entry_ids:
                soup = get_soup_handle_server_error(next_url, proxies=proxies, processed_entry_ids=processed_entry_ids)
            else:
                assert status_code == 200, f'invalid status code: {status_code}, (has_valid_entry_ids is False)'
        except RequestThrottledException:
            if stop_on_throttled_error:
                traceback.print_exc()
                stats[f'stopped_on_throttled_error_next_url__{next_url}'] += 1
                break
            else:
                raise
        assert str(soup).startswith('<?xml version="1.0" encoding="utf-8"?><feed'), f'invalid response: {str(soup)[:100]}'
        try:
            entries = soup.feed.find_all('entry')
        except:
            traceback.print_exc()
            entries = []
        for entry in entries:
            if has_valid_entry_ids:
                try:
                    entry_id = int(entry.id.text.split('(')[1].split(')')[0].split('L')[0])
                except:
                    entry_id = None
                if entry_id is None:
                    has_valid_entry_ids = False
            if not has_valid_entry_ids or entry_id not in processed_entry_ids:
                stats['rows'] += 1
                yield get_key_row_from_entry(params, entry)
                if has_valid_entry_ids:
                    processed_entry_ids.append(entry_id)
        try:
            next_link = soup.find('link', rel="next")
            next_url = next_link and next_link.attrs.get('href', None)
        except Exception:
            next_url = None


def upload_to_storage(source_path, target_url, pipeline_name, delete=False):
    if delete:
        assert source_path is None
        print(f'deleting {target_url} from storage')
    else:
        print(f'uploading {source_path} to {target_url}')
    assert target_url.startswith('http://storage.googleapis.com/knesset-data-pipelines/')
    target_path = target_url.replace('http://storage.googleapis.com/knesset-data-pipelines/', '')
    bucket_name = 'knesset-data-pipelines'
    storage_client = google.cloud.storage.Client()
    bucket = storage_client.bucket(bucket_name)
    for filename in ('datapackage.json', f'{pipeline_name}.csv'):
        if delete:
            blob = bucket.blob(os.path.join(target_path, filename))
            if blob.exists():
                blob.delete()
        else:
            filepath = os.path.join(source_path, filename)
            assert os.path.exists(filepath), f'file not found: {filepath}'
            blob = bucket.blob(os.path.join(target_path, filename))
            blob.upload_from_filename(filepath)


def get_schema_set_type_kwargs(dataservice_params):
    res = []
    for fieldname, field in dataservice_params['fields'].items():
        res.append({
            'name': fieldname,
            'regex': False,
            'type': field['type'],
        })
    return res


def validate_items_iterator(iterator_func, stats, num_validations=2, max_iterations=5):
    print(f'Starting validate_items_iterator (num_validations={num_validations}, max_iterations={max_iterations})')
    ok, last_keys = False, None
    with tempfile.TemporaryDirectory() as tmpdir:
        filename = os.path.join(tmpdir, 'pickle')
        for i in range(max_iterations):
            stats.clear()
            print(f'validate_items_iterator iteration #{i+1}')
            if i > 0:
                os.unlink(filename)
            with open(filename, 'wb') as f:
                pickler = pickle.Pickler(f)
                cur_keys = set()
                for data in iterator_func():
                    pickler.dump(data['row'])
                    key = data['key']
                    assert key not in cur_keys, f'duplicate key {key}'
                    cur_keys.add(key)
            if last_keys is not None and cur_keys == last_keys:
                num_validations -= 1
                print(f'Validated, remaining validations: {num_validations}')
            if num_validations <= 0:
                ok = True
                break
            last_keys = cur_keys
        assert ok, f'Failed to validate items iterator after {max_iterations} iterations'
        print('Validated all required validations')
        with open(filename, 'rb') as f:
            unpickler = pickle.Unpickler(f)
            while True:
                try:
                    yield unpickler.load()
                except EOFError:
                    break


def _run_pipeline(table_name, storage_url, pipeline_id, storage_path, dataservice_params, limit_rows, pipeline_name, dump_to_path, dump_to_db, dump_to_storage,
                  stop_on_throttled_error=False, start_url=None, load_from=None):
    if stop_on_throttled_error:
        assert not dump_to_db, 'stop_on_throttled_error is not supported with dump_to_db'
        assert not dump_to_storage, 'stop_on_throttled_error is not supported with dump_to_storage'
    table_name = f'{table_name}{config.KNESSET_DATA_OUTPUT_SUFFIX}'
    storage_url = f'{storage_url}{config.KNESSET_DATA_OUTPUT_SUFFIX}'
    print(f'pipeline_id: {pipeline_id}\nstorage_url: {storage_url}\nstorage_path: {storage_path}\ntable_name: {table_name}')
    stats = defaultdict(int)
    temp_table_name = f'__temp__{table_name}'
    rows_iterator = validate_items_iterator(
        functools.partial(
            add_dataservice_collection_resource,
            dataservice_params,
            stats=stats, limit_rows=limit_rows, stop_on_throttled_error=stop_on_throttled_error, start_url=start_url, load_from=load_from
        ),
        stats,
    )
    first_row = next(rows_iterator, None)
    if first_row is not None:
        DF.Flow(
            itertools.chain([first_row], rows_iterator),
            DF.update_resource('res_1', name=pipeline_name, path=f'{pipeline_name}.csv'),
            *[DF.set_type(resources=pipeline_name, **kwargs) for kwargs in get_schema_set_type_kwargs(dataservice_params)],
            *([
                  DF.dump_to_path(storage_path),
              ] if dump_to_path else []),
            *([
                  DF.dump_to_sql(
                      {temp_table_name: {'resource-name': pipeline_name}},
                      db.get_db_engine(),
                      batch_size=100000,
                  ),
              ] if dump_to_db else []),
        ).process()
        if dump_to_db:
            alias_table_name = dataservice_params['method-name'] if dataservice_params.get("service-name") == "api" else None
            with db.get_db_engine().connect() as conn:
                with conn.begin():
                    sql = []
                    if alias_table_name:
                        sql.append(f'drop view if exists "{alias_table_name}";')
                    sql.append(f'drop table if exists {table_name};')
                    sql.append(f'alter table {temp_table_name} rename to {table_name};')
                    if alias_table_name:
                        alias_table_name = dataservice_params['method-name']
                        sql.append(f'create view "{alias_table_name}" as select')
                        for i, field_name in enumerate(dataservice_params['fields']):
                            alias_field_name = field_name
                            if dataservice_params['fields'][field_name].get('primaryKey'):
                                alias_field_name = 'Id'
                            if i != 0:
                                sql.append(',')
                            sql.append(f'"{field_name}" as "{alias_field_name}"')
                        sql.append(f'from {table_name};')
                    conn.execute("\n".join(sql))
        if dump_to_storage:
            upload_to_storage(storage_path, storage_url, pipeline_name)
    else:
        print('no data found for the pipeline, removing old data if exists')
        shutil.rmtree(storage_path, ignore_errors=True)
        if dump_to_db:
            with db.get_db_engine().connect() as conn:
                conn.execute(f'drop table if exists {table_name};')
        if dump_to_storage:
            upload_to_storage(None, storage_url, pipeline_name, delete=True)
    pprint(dict(stats))
    if stop_on_throttled_error:
        for key in stats.keys():
            if key.startswith('stopped_on_throttled_error_next_url__'):
                return key.replace('stopped_on_throttled_error_next_url__', '')
    return None


def main(pipeline_id, limit_rows=None, dump_to_db=None, dump_to_path=None, dump_to_storage=None):
    if not dump_to_db and not dump_to_path and not dump_to_storage:
        dump_to_db, dump_to_path, dump_to_storage = True, True, True
    if dump_to_storage:
        dump_to_path = True
    limit_rows = int(limit_rows) if limit_rows else None
    pipeline_name, pipeline = get_pipeline_spec(pipeline_id)
    error, dataservice_params, storage_url, storage_path, table_name = try_get_pipeline_params(pipeline_name, pipeline)
    if error:
        _run_pipeline_docker(pipeline_id)
    else:
        _run_pipeline(table_name, storage_url, pipeline_id, storage_path, dataservice_params, limit_rows, pipeline_name, dump_to_path, dump_to_db, dump_to_storage)


def _run_pipeline_docker(pipeline_id):
    print(f'Running pipeline via Docker: {pipeline_id}')
    print('WARNING! pipeline dependencies will be ignored, they are only handled when running via Airflow')
    exit(subprocess.call([
        'docker', 'run', '-it', '--entrypoint', '/usr/local/bin/dpp', '-v', f'{config.KNESSET_DATA_PIPELINES_ROOT_DIR}:/pipelines',
        PIPELINES_DEV_DOCKER_IMAGE, 'run', '--verbose', '--no-use-cache', f'./{pipeline_id}'
    ]))


def run_dpp_shell():
    exit(subprocess.call([
        'docker', 'run', '-it', '--entrypoint', '/bin/bash', '-v',
        f'{config.KNESSET_DATA_PIPELINES_ROOT_DIR}:/pipelines',
        PIPELINES_DEV_DOCKER_IMAGE
    ]))


def get_pipeline_schedule(pipeline_id, pipeline):
    if pipeline.get('schedule'):
        return True
    for dependency in pipeline.get('dependencies', []):
        if dependency.get('pipeline'):
            return True
    if pipeline.get('pipeline-type') == 'knesset dataservice':
        return True
    for dep_pipeline_id, dep_pipeline_name, dep_pipeline in _iterate_pipelines():
        for dependency in dep_pipeline.get('dependencies', []):
            if dependency.get('pipeline') == f'./{pipeline_id}':
                return True
    return False


def _iterate_pipelines(filter_pipeline_ids=None):
    for source_spec_yaml in glob(os.path.join(config.KNESSET_DATA_PIPELINES_ROOT_DIR, '**/knesset.source-spec.yaml'), recursive=True):
        pipeline_path = os.path.dirname(source_spec_yaml.replace(config.KNESSET_DATA_PIPELINES_ROOT_DIR, '').lstrip('/'))
        with open(source_spec_yaml) as f:
            source_spec = yaml.safe_load(f)
        for pipeline_name, pipeline in source_spec.items():
            pipeline_id = os.path.join(pipeline_path, pipeline_name)
            if filter_pipeline_ids and pipeline_id not in filter_pipeline_ids:
                continue
            pipeline_name, pipeline = get_pipeline_spec(pipeline_id)
            yield pipeline_id, pipeline_name, pipeline
    for pipeline_yaml in glob(os.path.join(config.KNESSET_DATA_PIPELINES_ROOT_DIR, 'airflow/pipelines/**/*.yaml'), recursive=True):
        pipeline_path, pipeline_name = pipeline_yaml.split('/')[-2:]
        pipeline_name = pipeline_name.replace('.yaml', '')
        pipeline_id = f'{pipeline_path}/{pipeline_name}'
        with open(pipeline_yaml) as f:
            pipeline = post_process_airflow_pipeline(pipeline_path, pipeline_name, yaml.safe_load(f))
        yield pipeline_id, pipeline_name, pipeline


def list_pipelines(full=False, filter_pipeline_ids=None, all_=False, with_dependencies=False):
    if all_:
        assert not full, 'full and all_ are mutually exclusive'
    if with_dependencies:
        assert all_, 'with_dependencies is only supported with all_'
    filter_pipeline_ids = filter_pipeline_ids.split(',') if filter_pipeline_ids else None
    for pipeline_id, pipeline_name, pipeline in _iterate_pipelines(filter_pipeline_ids):
        error, dataservice_params, storage_url, storage_path, table_name = try_get_pipeline_params(pipeline_name, pipeline)
        if all_:
            if with_dependencies:
                yield error, pipeline_id, get_pipeline_dependencies(pipeline), get_pipeline_schedule(pipeline_id, pipeline)
            else:
                yield error, pipeline_id
        elif not error:
            if full:
                yield {
                    'pipeline_id': pipeline_id,
                    'pipeline_name': pipeline_name,
                    'dataservice_params': dataservice_params,
                    'storage_url': storage_url,
                    'storage_path': storage_path,
                    'table_name': table_name,
                }
            else:
                yield pipeline_id


def get_pipeline_dependencies(pipeline):
    res = []
    for dependency in pipeline.get('dependencies', []):
        if dependency.get('pipeline'):
            res.append(dependency['pipeline'].replace('./', ''))
    return res


def run_all(filter_pipeline_ids=None):
    if filter_pipeline_ids:
        filter_pipeline_ids = [p.strip() for p in filter_pipeline_ids.split(',') if p.strip()]
    all_pipelines = list(list_pipelines(full=True, filter_pipeline_ids=filter_pipeline_ids))
    bucket_name = 'knesset-data-pipelines'
    storage_client = google.cloud.storage.Client()
    bucket = storage_client.bucket(bucket_name)
    for pipeline in all_pipelines:
        datapackage_json_url = os.path.join(pipeline['storage_url'].replace('http://', 'https://'), 'datapackage.json')
        datapackage = requests.get(datapackage_json_url).json()
        pipeline['old_package_hash'] = datapackage['hash']
        pipeline['old_package_created'] = bucket.get_blob(datapackage_json_url.replace('https://storage.googleapis.com/knesset-data-pipelines/', '')).time_created
        pipeline['hours_since_last_update'] = (datetime.datetime.now(datetime.timezone.utc) - pipeline['old_package_created']).total_seconds() / 60 / 60
    temp_pipeline_path = os.path.join(config.KNESSET_PIPELINES_DATA_PATH, '__airflow_temp_pipeline')
    temp_pipeline_status_json_filename = os.path.join(temp_pipeline_path, 'status.json')
    if os.path.exists(temp_pipeline_status_json_filename):
        with open(temp_pipeline_status_json_filename) as f:
            old_temp_pipeline_status = json.load(f)
    else:
        old_temp_pipeline_status = None
    if old_temp_pipeline_status is not None:
        print(f'old_temp_pipeline_status: {old_temp_pipeline_status}')
    for pipeline in all_pipelines:
        if old_temp_pipeline_status and old_temp_pipeline_status['pipeline_id'] != pipeline['pipeline_id']:
            print(f'skipping pipeline {pipeline["pipeline_id"]} because we are waiting to continue previously started pipeline {old_temp_pipeline_status["pipeline_id"]}')
            continue
        if pipeline['hours_since_last_update'] <= 24:
            print(f'skipping pipeline {pipeline["pipeline_id"]} because it was updated {pipeline["hours_since_last_update"]} hours ago')
            continue
        if old_temp_pipeline_status:
            print(f'continuing pipeline {pipeline["pipeline_id"]} from previous run')
            start_datetime = datetime.datetime.fromisoformat(old_temp_pipeline_status['start_datetime'])
            start_url = old_temp_pipeline_status.get('stopped_next_url')
            old_temp_pipeline_status = None
        else:
            print(f'running pipeline {pipeline["pipeline_id"]}')
            start_datetime = datetime.datetime.now(datetime.timezone.utc)
            start_url = None
            shutil.rmtree(temp_pipeline_path, ignore_errors=True)
            os.makedirs(temp_pipeline_path, exist_ok=True)
        with open(temp_pipeline_status_json_filename, 'w') as f:
            json.dump({
                'pipeline_id': pipeline['pipeline_id'],
                'start_datetime': start_datetime.isoformat(),
                'start_url': start_url,
            }, f)
        with tempfile.TemporaryDirectory() as tmpdir:
            stopped_next_url = _run_pipeline(
                table_name=None, storage_url=None, pipeline_id=pipeline['pipeline_id'],
                storage_path=tmpdir, dataservice_params=pipeline['dataservice_params'],
                limit_rows=None, pipeline_name=pipeline['pipeline_name'],
                dump_to_path=True, dump_to_db=False, dump_to_storage=False,
                stop_on_throttled_error=True, start_url=start_url if os.path.exists(os.path.join(temp_pipeline_path, 'datapackage.json')) else None,
                load_from=temp_pipeline_path if start_url and os.path.exists(os.path.join(temp_pipeline_path, 'datapackage.json')) else None
            )
            for filename in os.listdir(tmpdir):
                os.unlink(os.path.join(temp_pipeline_path, filename))
                shutil.move(os.path.join(tmpdir, filename), os.path.join(temp_pipeline_path, filename))
        if stopped_next_url:
            print(f'pipeline stopped on url {stopped_next_url}, can continue on next run')
            with open(temp_pipeline_status_json_filename, 'w') as f:
                json.dump({
                    'pipeline_id': pipeline['pipeline_id'],
                    'start_datetime': start_datetime.isoformat(),
                    'stopped_datetime': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    'stopped_next_url': stopped_next_url,
                }, f)
                break
        else:
            shutil.rmtree(temp_pipeline_path, ignore_errors=True)
