from datapackage_pipelines.wrapper import ingest, spew
import openpyxl
import json
import datetime
import os


parameters, datapackage, resources = ingest()


def get_headers(fields, param_fields):
    headers = []
    for field in fields:
        headers.append(param_fields.get(field['name'], {}).get('title', field['name']))
    return headers


def get_excel_cell(row, field):
    value = row[field['name']]
    if isinstance(value, datetime.datetime):
        return value.strftime('%Y-%m-%d %H:%M:%S')
    elif isinstance(value, list):
        return ', '.join(map(str, value))
    else:
        return value


def get_excel_row(row, fields):
    return [get_excel_cell(row, field) for field in fields]


def get_resource(workbook, fields, resource):
    for row in resource:
        workbook.active.append(get_excel_row(row, fields))
        yield row


def get_resources():
    workbook = openpyxl.Workbook()
    workbook.remove(workbook.active)
    for idx, resource in enumerate(resources):
        descriptor = datapackage['resources'][idx]
        workbook.create_sheet(parameters.get('sheet-names', {}).get(descriptor['name'],
                                                                    descriptor['name']), idx)
        workbook.active = idx
        fields = descriptor['schema']['fields']
        param_fields = None
        for name_prefix, param_fields in parameters['fields'].items():
            if descriptor['name'].startswith(name_prefix):
                break
            else:
                param_fields = None
        assert param_fields
        headers = get_headers(fields, param_fields)
        workbook.active.append(headers)
        yield get_resource(workbook, fields, resource)
    os.makedirs(os.path.dirname(parameters['out-file']), exist_ok=True)
    workbook.save(parameters['out-file'])


spew(datapackage, get_resources())
