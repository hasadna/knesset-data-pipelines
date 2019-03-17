from datapackage_pipelines.wrapper import ingest, spew
import logging
from datapackage_pipelines.utilities.resources import PROP_STREAMING
from datetime import datetime


def get_source_data(resource, source_data):
    for row in resource:
        yield row
        source_data.append(row)


def get_parsed_data(source_data):
    for row in source_data:
        office = row['office']
        for ceo_num in ['1', '2', '3']:
            ceo_name = row.get('ceo_{}_name'.format(ceo_num))
            ceo_start = row.get('ceo_{}_start'.format(ceo_num))
            ceo_end = row.get('ceo_{}_end'.format(ceo_num))
            if ceo_name and ceo_start:
                ceo_end = ceo_end or datetime.now().strftime('%-m/%y')
                yield {
                    'office': office,
                    'ceo_name': ceo_name,
                    'start_datestring': ceo_start,
                    'end_datestring': ceo_end,
                }


def get_resources(datapackage, resources):
    source_data = []
    for descriptor, resource in zip(datapackage['resources'], resources):
        if descriptor['name'] == 'govministries-managers':
            yield get_source_data(resource, source_data)
        else:
            yield resource
    yield get_parsed_data(source_data)


def get_datapackage(datapackage):
    datapackage['resources'].append({PROP_STREAMING: True,
                                     'name': 'parsed_govministries_managers',
                                     'path': 'parsed_govministries_managers.csv',
                                     'schema': {'fields': [
                                         {'name': 'office', 'type': 'string'},
                                         {'name': 'ceo_name', 'type': 'string'},
                                         {'name': 'start_datestring', 'type': 'string'},
                                         {'name': 'end_datestring', 'type': 'string'},
                                     ]}})
    return datapackage


def main():
    parameters, datapackage, resources, stats = ingest() + ({},)
    spew(get_datapackage(datapackage),
         get_resources(datapackage, resources),
         stats)


if __name__ == '__main__':
    main()
