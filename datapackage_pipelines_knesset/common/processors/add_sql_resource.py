# shamelessly copied from budgetkey-data-pipelines
import os
from datapackage_pipelines.wrapper import process
import datapackage


def modify_datapackage(dp, parameters, *_):
    datapackage_url = parameters['datapackage']
    source_datapackage = datapackage.DataPackage(datapackage_url)
    for resource in source_datapackage.resources:
        descriptor = resource.descriptor
        if descriptor['name'] == parameters['resource']:
            # override field attributes based on parameters and matching on field name
            override_fields = {field["name"]: field for field in parameters.get("fields", [])}
            for field in descriptor["schema"]["fields"]:
                field.update(override_fields.get(field["name"], {}))
            resource = {
                'name': descriptor['name'],
                'schema': descriptor['schema'],
                'url': os.environ['DPP_DB_ENGINE'],
                'table': parameters['table']
            }
            dp['resources'].append(resource)
            break
    return dp

process(modify_datapackage=modify_datapackage)
