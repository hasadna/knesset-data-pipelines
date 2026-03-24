import json
import os
from textwrap import dedent
import xml.etree.ElementTree as ET

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
        'Edm.DateTimeOffset': 'datetime',  # "2016-02-28T10:22:10.843+02:00",
        'Edm.DateTime': 'datetime',
        None: 'string',  # "string",
        'Edm.Boolean': 'boolean',
        'Edm.String': 'string',
        'Edm.Decimal': 'string',
    }
    assert field.get("$Type") in field_types, f"unknown field type {field.get('$Type')}"
    return {
        'type': field_types[field.get("$Type")]
    }


def get_parliamentinfo_tables():
    res = {}
    data = requests.get('https://knesset.gov.il/OdataV4/ParliamentInfo/$metadata?$format=json').json()
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
    for service_name in (
            'Lobbyists',
            'Votes',
    ):
        xmlstr = requests.get(f'https://knesset.gov.il/Odata/{service_name}.svc/$metadata').text
        root = ET.fromstring(xmlstr)
        ns = {
            "edmx": "http://schemas.microsoft.com/ado/2007/06/edmx",
            "edm": "http://schemas.microsoft.com/ado/2009/11/edm",
        }
        for schema in root.findall(".//edm:Schema", ns):
            for entity_type in schema.findall("edm:EntityType", ns):
                table_name = f'{service_name.lower()}_{entity_type.get("Name")}'
                fields = {}
                for prop in entity_type.findall("edm:Property", ns):
                    field_name = prop.get("Name")
                    fields[field_name] = get_table_res_field({
                        "$Type": prop.get("Type"),
                    })
                edm_keys = entity_type.findall("edm:Key", ns)
                assert len(edm_keys) == 1
                edm_key = edm_keys[0]
                keys = [k.get("Name") for k in edm_key.findall("edm:PropertyRef", ns)]
                res[table_name] = {
                    'primary_key': keys[0] if len(keys) == 1 else keys,
                    'fields': fields,
                }
    return res


def get_pipelines_res_field(field, pipeline_id=None, field_name=None):
    assert field['source'] == '{name}', f'unexpected source {field["source"]} in field {field_name} of pipeline {pipeline_id}'
    return {
        'type': field['type'],
        'primary_key': bool(field.get('primaryKey')),
    }


def get_parliamentinfo_pipelines():
    res = {}
    for pipeline in list_pipelines(full=True):
        pipeline_id = pipeline['pipeline_id']
        if pipeline.get('dataservice_params'):
            dataservice_params = pipeline['dataservice_params']
            odata_v4 = dataservice_params.get('odata-v4', True)
            if odata_v4:
                assert dataservice_params.get('service-name') == 'api', f'{pipeline_id}: api service should have service-name set to api'
                method_name = dataservice_params['method-name']
            else:
                method_name = f'{dataservice_params["service-name"]}_{dataservice_params["method-name"]}'
            res[method_name] = {}
            res[method_name]['fields'] = {
                name: get_pipelines_res_field(field, pipeline_id=pipeline_id, field_name=name)
                for name, field in dataservice_params['fields'].items()
            }
            primary_keys = [name for name, field in res[method_name]['fields'].items() if field.get('primary_key')]
            if len(primary_keys) == 1:
                res[method_name]['primary_key'] = primary_keys[0]
            elif len(primary_keys) > 1:
                res[method_name]['primary_key'] = primary_keys
            else:
                raise Exception(f'no primary key found in pipeline {pipeline_id} for method {method_name}')
    return res


class MissingObject:

    def __init__(self, dst_obj_type, table_name, table=None):
        self.dst_obj_type = dst_obj_type
        self.table_name = table_name
        self.table = table

    def __str__(self):
        if self.dst_obj_type == 'pipelines':
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
            return f'{self.table_name} is missing from {self.dst_obj_type}, wrote to filename {filename}\n'
        else:
            return f'{self.table_name} exists in pipelines but missing in tables'


class InvalidPipeline:

    def __init__(self, dst_obj_type, table_name, table):
        self.dst_obj_type = dst_obj_type
        self.table_name = table_name
        self.table = table
        self.missing_fields = []
        self.wrong_type_fields = []
        self.extra_fields = []
        self.primary_key_mismatch = False

    def __str__(self):
        res = f'mismatch in pipeline for table {self.table_name}:\n' if self.dst_obj_type == 'pipelines' else f'mismatch in table for pipeline {self.table_name}:\n'
        if len(self.missing_fields) > 0:
            res += ' - missing fields in pipeline:\n' if self.dst_obj_type == 'pipelines' else ' - extra fields in pipeline do not appear in table:\n'
            for field_name in self.missing_fields:
                res += f'{field_name}: {{source: "{{name}}", type: "{self.table["fields"].get(field_name, {}).get("type")}"}}\n'
        if len(self.wrong_type_fields) > 0:
            res += ' - wrong type fields:\n' if self.dst_obj_type == 'pipelines' else ' - wrong type fields (type in table shown below does not match type in pipeline):\n'
            for field_name in self.wrong_type_fields:
                res += f'{field_name}: {{source: "{{name}}", type: "{self.table["fields"][field_name]["type"]}"}}\n'
        if len(self.extra_fields) > 0:
            res += ' - extra fields in pipeline which are not in table:\n' if self.dst_obj_type == 'pipelines' else ' - missing  fields in pipeline which appear in table:\n'
            for field_name in self.extra_fields:
                res += f'{field_name}\n'
        if self.primary_key_mismatch:
            res += ' - primary key mismatch:\n'
            res += f'table primary key: {self.table["primary_key"]}\n'
        return res

    def has_errors(self):
        return sum((
            len(self.missing_fields),
            len(self.wrong_type_fields),
            len(self.extra_fields),
        )) > 0 or self.primary_key_mismatch


def compare_parliamentinfo_tables_pipelines():
    fix_objects = []
    tables = get_parliamentinfo_tables()
    pipelines = get_parliamentinfo_pipelines()
    for dst_obj_type, src, dst in (('pipelines', tables, pipelines), ('tables', pipelines, tables)):
        for src_name, src_obj in src.items():
            if src_name not in dst:
                fix_objects.append(MissingObject(dst_obj_type, src_name, src_obj if dst_obj_type == 'pipelines' else None))
            else:
                dst_obj = dst[src_name]
                invalid_pipeline = InvalidPipeline(dst_obj_type, src_name, tables[src_name])
                for field_name, field in src_obj['fields'].items():
                    if field_name not in dst_obj['fields']:
                        if dst_obj_type == 'pipelines' and src_obj['primary_key'] == field_name and dst_obj['primary_key']:
                            # handle the special case of primary key for v4 being renamed to Id
                            field_name = dst_obj['primary_key']
                        elif dst_obj_type == 'tables' and src_obj['primary_key'] == field_name and dst_obj['primary_key'] == 'Id':
                            # handle the special case of primary key for v4 being renamed to Id
                            field_name = 'Id'
                        else:
                            invalid_pipeline.missing_fields.append(field_name)
                            continue
                    if field['type'] != dst_obj['fields'][field_name]['type'] and field_name not in IGNORE_FIELD_TYPE_ERRORS.get(src_name, []):
                        invalid_pipeline.wrong_type_fields.append(field_name)
                if set(src_obj['primary_key']) != set(dst_obj['primary_key']) and tables[src_name]['primary_key'] != 'Id':
                    invalid_pipeline.primary_key_mismatch = True
                if invalid_pipeline.has_errors():
                    fix_objects.append(invalid_pipeline)
    if len(fix_objects) > 0:
        for fix_object in fix_objects:
            print(fix_object)
        raise Exception('need to fix the pipelines')
    else:
        print('all pipelines are complete and correct')


if __name__ == '__main__':
    compare_parliamentinfo_tables_pipelines()
    # print(json.dumps(list(get_parliamentinfo_pipelines().keys()), indent=2))
    # print(json.dumps(get_parliamentinfo_pipelines()["lobbyists_V_Lobbyists"], indent=2))
    # print(json.dumps(list(get_parliamentinfo_tables().keys()), indent=2))
    # print(json.dumps(get_parliamentinfo_tables()["lobbyists_V_Lobbyists"], indent=2))
