from datapackage_pipelines.generators import GeneratorBase, steps
from copy import deepcopy
import logging, os, requests, codecs, uuid, datetime
from datapackage_pipelines_metrics import append_metrics


__escape_decoder = codecs.getdecoder('unicode_escape')


def decode_escaped(escaped):
    return __escape_decoder(escaped)[0]


def remove_pipeline_dependencies(pipeline):
    dependencies = []
    for dependency in pipeline.get('dependencies', []):
        if dependency.get('pipeline'):
            continue
        dependencies.append(dependency)
    pipeline['dependencies'] = dependencies


def parse_dotenv(dotenv):
    for line in dotenv.splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        k, v = line.split('=', 1)
        k, v = k.strip(), v.strip().encode('unicode-escape').decode('ascii')
        if len(v) > 0:
            quoted = v[0] == v[-1] in ['"', "'"]
            if quoted:
                v = decode_escaped(v[1:-1])
        yield k, v


class Generator(GeneratorBase):
    latest_sync_url = None

    @classmethod
    def get_schema(cls):
        return {"$schema": "http://json-schema.org/draft-04/schema#",
                "type": "object",
                "properties": {}}

    @classmethod
    def generate_pipeline(cls, source, base):
        for pipeline_id, pipeline in source.items():
            if pipeline_id and pipeline:
                for output_pipeline_id, output_pipeline in cls.filter_pipeline(pipeline_id, deepcopy(pipeline), base):
                    if os.environ.get('DPP_INFLUXDB_URL'):
                        yield output_pipeline_id, append_metrics(output_pipeline)
                    else:
                        yield output_pipeline_id, output_pipeline


    @classmethod
    def filter_pipeline(cls, pipeline_id, pipeline, base):
        remove_pipeline_dependencies(pipeline)  # pipeline dependencies are handled in Airflow
        if pipeline.get('dpp_disabled'):
            yield from cls.get_dpp_disabled_pipeline(pipeline_id, pipeline, base)
        elif pipeline.get("pipeline-type") == "knesset dataservice":
            yield from cls.get_knesset_dataservice_pipeline(pipeline_id, pipeline, base)
        elif pipeline.get("pipeline-type") == "all package":
            yield from cls.get_all_package_pipeline(pipeline_id, pipeline, base)
        elif pipeline.get("pipeline-type") == "db dump":
            yield from cls.get_db_dump_pipeline(pipeline_id, pipeline, base)
        else:
            if os.environ.get('KNESSET_LOAD_FROM_URL') == '1':
                if 'dependencies' in pipeline:
                    del pipeline['dependencies']
                url = None
                out_path = None
                for step in pipeline['pipeline']:
                    if step.get('run') == 'knesset.dump_to_path':
                        parameters = step.get('parameters', {})
                        if parameters.get('storage-url') and parameters.get('out-path'):
                            url, out_path = parameters['storage-url'], parameters['out-path']
                if not url or not out_path:
                    for step in pipeline['pipeline']:
                        if step.get('run') == 'dump.to_path':
                            parameters = step.get('parameters', {})
                            if parameters.get('out-path') and parameters.get('out-path').startswith('../../data/committees/dist/'):
                                out_path = parameters['out-path']
                                rel_path = parameters['out-path'].replace('../../data/committees/dist/', '')
                                url = 'https://production.oknesset.org/pipelines/data/committees/dist/{}'.format(rel_path)
                if url and out_path:
                    pipeline['pipeline'] = [{'run': 'load_resource',
                                             'parameters': {'url': url + '/datapackage.json',
                                                            'resource': '.*',
                                                            'log-progress-rows': 10000}},
                                            {'run': 'dump.to_path',
                                             'parameters': {'out-path': out_path}}]
            elif os.environ.get('KNESSET_DATA_SAMPLES'):
                if 'dependencies' in pipeline:
                    del pipeline['dependencies']
            yield os.path.join(base, pipeline_id), pipeline

    @classmethod
    def get_dpp_disabled_pipeline(cls, pipeline_id, pipeline, base):
        pipeline_steps = [('knesset.dummy', {'msg': 'running dummy pipeline because dpp is disabled, the package is created elsewhere'})]
        output_pipeline = {
            'pipeline': steps(*pipeline_steps)
        }
        if pipeline.get('dependencies'):
            output_pipeline['dependencies'] = pipeline['dependencies']
        else:
            output_pipeline['schedule'] = {'crontab': '26 6 * * *'}
        yield os.path.join(base, pipeline_id), output_pipeline

    @classmethod
    def get_knesset_dataservice_pipeline(cls, pipeline_id, pipeline, base):
        storage_path = "data/{}/{}".format(pipeline['schemas-bucket'], pipeline_id)
        storage_url = "http://storage.googleapis.com/knesset-data-pipelines/{}".format(storage_path)
        if os.environ.get('KNESSET_PIPELINES_DATA_PATH'):
            storage_abspath = os.path.join(os.environ['KNESSET_PIPELINES_DATA_PATH'],
                                           pipeline['schemas-bucket'], pipeline_id)
        else:
            storage_abspath = None
        resource_name = pipeline_id
        pipeline_steps = []
        if os.environ.get('KNESSET_LOAD_FROM_URL'):
            if 'dependencies' in pipeline:
                del pipeline['dependencies']
            pipeline_steps += [('load_resource', {"url": "{}/datapackage.json".format(storage_url),
                                                  "resource": '.*',
                                                  'log-progress-rows': 10000},
                                True), ]
        else:
            for pre_step in pipeline.get('pre-steps', []):
                pipeline_steps.append((pre_step['run'],
                                       pre_step.get('parameters', {}),
                                       pre_step.get('cache', False)))
            if os.environ.get("DATASERVICE_LOAD_FROM_URL"):
                pipeline_steps += [('load_resource', {"url": "{}/datapackage.json".format(storage_url),
                                                      "resource": resource_name,
                                                      'log-progress-rows': 10000,
                                                      'limit-rows': pipeline['dataservice-parameters'].get('limit-rows')},
                                    True),]
            else:
                if (
                        'incremental-field' in pipeline['dataservice-parameters']
                        and os.environ.get('KNESSET_DATASERVICE_INCREMENTAL')
                ):
                    if not storage_abspath:
                        logging.error('please set KNESSET_PIPELINES_DATA_PATH env var to absolute path for the data directory to use incremental updates')
                        exit(1)
                    pipeline_steps += [('load_resource',
                                        {"url": "{}/datapackage.json".format(storage_abspath),
                                         'required': False,
                                         "resources": {resource_name: {'name': 'last_' + resource_name,
                                                                       'path': 'last_' + resource_name + '.csv'}}})]
                pipeline_steps += [('..datapackage_pipelines_knesset.dataservice.processors.add_dataservice_collection_resource',
                                    pipeline["dataservice-parameters"]),
                                   ('..datapackage_pipelines_knesset.common.processors.throttle',
                                    {'rows-per-page': 50, 'resource': resource_name}),]
                if (
                        'incremental-field' in pipeline['dataservice-parameters']
                        and os.environ.get('KNESSET_DATASERVICE_INCREMENTAL')
                ):
                    pipeline_steps += [('sort', {'resources': resource_name,
                                                 'sort-by': '{' + pipeline['dataservice-parameters']['incremental-field'] + '}'})]
            for additional_step in pipeline.get('additional-steps', []):
                pipeline_steps.append((additional_step['run'],
                                       additional_step.get('parameters', {}),
                                       additional_step.get('cache', False)))
        pipeline_steps += [('knesset.dump_to_path', {'storage-url': storage_url,
                                                     'out-path': '../{}'.format(storage_path)},)]
        dump_to_sql = 'knesset.dump_to_sql'
        table_name = '{}_{}'.format(pipeline['schemas-bucket'], pipeline_id.replace('-', '_'))
        tables = {table_name: pipeline_id}
        tables.update(pipeline.get('additional-sql-tables', {}))
        tables = {table_name: {'resource-name': resource_name, 'mode': 'rewrite'}
                  for table_name, resource_name in tables.items()}
        pipeline_steps += [(dump_to_sql, {'engine': 'env://DPP_DB_ENGINE',
                                          'tables': tables},)]
        output_pipeline = {'pipeline': steps(*pipeline_steps),
                           'dependencies': pipeline.get('dependencies', [])}
        if pipeline.get('dependencies'):
            output_pipeline['dependencies'] = pipeline['dependencies']
        else:
            output_pipeline['schedule'] = {'crontab': '10 1 * * *'}
        yield os.path.join(base, pipeline_id), output_pipeline

    @classmethod
    def get_all_package_pipeline(cls, pipeline_id, pipeline, base):
        assert pipeline['base-url'].startswith('https://storage.googleapis.com/knesset-data-pipelines/')
        base_path = pipeline['base-url'].replace('https://storage.googleapis.com/knesset-data-pipelines/', '')
        pipeline_steps = []
        dependencies = []
        for resource in pipeline["resources"]:
            pipeline_steps += [("load_resource", {"url": '../' + base_path + resource["name"] + "/datapackage.json",
                                                  "resource": resource.get("resource", resource["name"])})]
            dependencies.append({'datapackage': base_path + resource["name"] + "/datapackage.json"})
            if resource.get("resource"):
                pipeline_steps += [("..rename_resource",
                                    {"src": resource["resource"], "dst": resource["name"]})]
            if resource.get('set_types'):
                pipeline_steps += [("set_types",
                                    {"resources": resource["name"], "types": resource['set_types']})]
        # pipeline_steps += [('dump.to_path',
        #                     {'out-path': pipeline["out-path"]})]
        pipeline_steps += [('dump.to_zip',
                            {'out-file': pipeline["out-path"] + "/datapackage.zip",
                             'pretty-descriptor': True})]
        storage_path = '{}all'.format(pipeline['base-url'].replace('https://storage.googleapis.com/knesset-data-pipelines/', ''))
        storage_url = "http://storage.googleapis.com/knesset-data-pipelines/{}".format(storage_path)
        pipeline_steps += [('knesset.dump_to_path', {'storage-url': storage_url,
                                                     'out-path': '../{}'.format(storage_path)},)]
        yield os.path.join(base, pipeline_id), {'pipeline': steps(*pipeline_steps),
                                                'schedule': {'crontab': '10 1 * * *'},
                                                'dependencies': dependencies}

    @classmethod
    def get_db_dump_pipeline(cls, pipeline_id, pipeline, base):
        pipeline_steps = [
            ("load_resource", {
                "url": "https://storage.googleapis.com/knesset-data-pipelines/data/members/presence/datapackage.json",
                "resource": "presence"
            }),
            ("load_resource", {
                "url": "https://storage.googleapis.com/knesset-data-pipelines/data/knesset/kns_knessetdates/datapackage.json",
                "resource": "kns_knessetdates"
            }),
            ("load_resource", {
                "url": "https://storage.googleapis.com/knesset-data-pipelines/data/votes/view_vote_mk_individual/datapackage.json",
                "resource": "view_vote_mk_individual"
            }),
            ("load_resource", {
                "url": "https://storage.googleapis.com/knesset-data-pipelines/data/votes/view_vote_rslts_hdr_approved/datapackage.json",
                "resource": "view_vote_rslts_hdr_approved"
            }),
            ("load_resource", {
                "url": "https://storage.googleapis.com/knesset-data-pipelines/data/votes/vote_result_type/datapackage.json",
                "resource": "vote_result_type"
            }),
            ("load_resource", {
                "url": "https://storage.googleapis.com/knesset-data-pipelines/data/votes/vote_rslts_kmmbr_shadow/datapackage.json",
                "resource": "vote_rslts_kmmbr_shadow"
            }),
            ("load_resource", {
                "url": "https://storage.googleapis.com/knesset-data-pipelines/data/committees/kns_committee/datapackage.json",
                "resource": "kns_committee"
            }),
            ("load_resource", {
                "url": "https://storage.googleapis.com/knesset-data-pipelines/data/people/members/joined-mks/datapackage.json",
                "resource": "mk_individual"
            }),
            ("load_resource", {
                "url": "https://storage.googleapis.com/knesset-data-pipelines/data/people/committees/committee-meeting-attendees-mks-stats/datapackage.json",
                "resource": "mk_attendance"
            }),
            # remove positions and altnames because oknesset DB doesn't support jsonb
            # TODO: normalize altnames and positions to mk_individual or other tables
            ("set_types", {"resources": "mk_individual", "types": {"positions": None, "altnames": None}}),
            ("dump.to_sql", {"engine": "env://DPP_DB_ENGINE", "tables": {
                "next_members_presence": {"resource-name": "presence", "mode": "rewrite"},
                "next_kns_knessetdates": {"resource-name": "kns_knessetdates", "mode": "rewrite"},
                "next_view_vote_mk_individual": {"resource-name": "view_vote_mk_individual", "mode": "rewrite"},
                "next_view_vote_rslts_hdr_approved": {"resource-name": "view_vote_rslts_hdr_approved", "mode": "rewrite"},
                "next_vote_result_type": {"resource-name": "vote_result_type", "mode": "rewrite"},
                "next_vote_rslts_kmmbr_shadow": {"resource-name": "vote_rslts_kmmbr_shadow", "mode": "rewrite"},
                "next_kns_committee": {"resource-name": "kns_committee", "mode": "rewrite"},
                "next_mk_individual": {"resource-name": "mk_individual", "mode": "rewrite"},
                "next_mk_attendance": {"resource-name": "mk_attendance", "mode": "rewrite"},
            }})
        ]
        yield os.path.join(base, pipeline_id), {'pipeline': steps(*pipeline_steps), 'schedule': {'crontab': '10 1 * * *'}}
