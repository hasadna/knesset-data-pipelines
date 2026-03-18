import os
from textwrap import dedent

import requests

from .run_pipeline import list_pipelines


IGNORE_FIELD_TYPE_ERRORS = {
    'KNS_BillHistoryInitiator': [
        'StartDate',  # field type is string instead of datetime
    ]
}


def get_table_res_field(field):
    field_types = {
        'Edm.Int64': 'integer',  # 123
        'Edm.Int32': 'integer',  # 123
        'Edm.Int16': 'integer',  # 123
        'Edm.Byte': 'integer',  # 123
        'Edm.DateTimeOffset': 'datetime',  # "2016-02-28T10:22:10.843+02:00"
        None: 'string',  # "string",
        'Edm.Boolean': 'boolean',
    }
    assert field.get("$Type") in field_types, f"unknown field type {field.get('$Type')}"
    return {
        'type': field_types[field.get("$Type")]
    }


def get_parliamentinfo_tables():
    data = requests.get('https://knesset.gov.il/OdataV4/ParliamentInfo/$metadata?$format=json').json()
    res = {}
    for table_name, fields in data['OdataService.DAL.ParliamentInfo'].items():
        assert fields.pop("$Kind") == 'EntityType'
        keys = fields.pop("$Key") or []
        assert len(keys) == 1, f"unexpected number of keys in table {table_name}: {keys}"
        res[table_name] = {
            'primary_key': keys[0],
            'fields': {
                field_name: get_table_res_field(field) for field_name, field in fields.items() if field.get('$Kind') is None
            }
        }
    return res


def get_pipelines_res_field(field):
    assert field['source'] == '{name}', f'unexpected source {field["source"]}'
    return {
        'type': field['type'],
        'primary_key': bool(field.get('primaryKey')),
    }


def get_parliamentinfo_pipelines():
    res = {}
    for pipeline in list_pipelines(full=True):
        if pipeline.get('dataservice_params') and pipeline['dataservice_params'].get('service-name') == 'api':
            res[pipeline['dataservice_params']['method-name']] = {}
            res[pipeline['dataservice_params']['method-name']]['fields'] = {
                name: get_pipelines_res_field(field) for name, field in pipeline['dataservice_params']['fields'].items()
            }
            primary_keys = [name for name, field in res[pipeline['dataservice_params']['method-name']]['fields'].items() if field.get('primary_key')]
            assert len(primary_keys) <= 1, f"unexpected number of primary keys in pipeline {pipeline['pipeline_id']}: {primary_keys}"
            res[pipeline['dataservice_params']['method-name']]['primary_key'] = primary_keys[0] if primary_keys else None
    return res


class MissingPipeline:

    def __init__(self, table_name, table):
        self.table_name = table_name
        self.table = table

    def __str__(self):
        res = f'table {self.table_name} is missing from pipelines\n'
        filename = f'knesset/{self.table_name.lower()}.yaml'
        filecontent = dedent(f'''
        pipeline-type: knesset dataservice
        dataservice-parameters:
          service-name: api
          method-name: "{self.table_name}"
          fields:
        ''')
        for field_name, field in self.table['fields'].items():
            filecontent += f'    {field_name}:\n'
            filecontent += f'      source: "{{name}}"\n'
            filecontent += f'      type: "{field["type"]}"\n'
            if field_name == self.table['primary_key']:
                filecontent += f'      primaryKey: true\n'
        with open(os.path.join(os.path.dirname(__file__), '..', 'pipelines', filename), 'w') as f:
            f.write(filecontent)
        return res


class IncompletePipeline:

    def __init__(self, table_name, table, pipeline):
        self.table_name = table_name
        self.table = table
        self.pipeline = pipeline
        self.missing_fields = []
        self.wrong_type_fields = []

    def __str__(self):
        res = f'pipeline for table {self.table_name} is incomplete:\n'
        if len(self.missing_fields) > 0:
            res += ' - missing fields:\n'
            for field_name in self.missing_fields:
                res += f'{field_name}: {{source: "{{name}}", type: "{self.table["fields"][field_name]["type"]}"}}\n'
        if len(self.wrong_type_fields) > 0:
            res += ' - wrong type fields:\n'
            for field_name in self.wrong_type_fields:
                res += f'{field_name}: {{source: "{{name}}", type: "{self.table["fields"][field_name]["type"]}"}}\n'
        return res


def compare_parliamentinfo_tables_pipelines():
    fix_objects = []
    tables = get_parliamentinfo_tables()
    pipelines = get_parliamentinfo_pipelines()
    for table_name, table in tables.items():
        if table_name not in pipelines:
            fix_objects.append(MissingPipeline(table_name, table))
            continue
        pipeline = pipelines[table_name]
        incomplete_pipeline = IncompletePipeline(table_name, table, pipeline)
        for field_name, field in table['fields'].items():
            if field_name not in pipeline['fields']:
                if table['primary_key'] == field_name and pipeline['primary_key']:
                    field_name = pipeline['primary_key']
                else:
                    incomplete_pipeline.missing_fields.append(field_name)
                    continue
            pipeline_field = pipeline['fields'][field_name]
            if field['type'] != pipeline_field['type'] and field_name not in IGNORE_FIELD_TYPE_ERRORS.get(table_name, []):
                incomplete_pipeline.wrong_type_fields.append(field_name)
        if len(incomplete_pipeline.missing_fields) > 0 or len(incomplete_pipeline.wrong_type_fields) > 0:
            fix_objects.append(incomplete_pipeline)
    if len(fix_objects) > 0:
        for fix_object in fix_objects:
            print(fix_object)
        raise Exception('need to fix the pipelines')
    else:
        print('all pipelines are complete and correct')


if __name__ == '__main__':
    compare_parliamentinfo_tables_pipelines()
