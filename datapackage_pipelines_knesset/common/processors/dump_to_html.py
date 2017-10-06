from datapackage_pipelines.wrapper import ingest, spew
import logging, os

DEFAULT_SAVE_SCHEMA = "../data/aggregation/{table_name}.html"

parameters, datapackage, resources = ingest()

def filter_resource(descriptor, data):
    for row in data:
        yield row

def _get_schema_table(tablename, fields, primaryKey):
    html = "<h1>{tablename}</h1>".format(tablename=tablename)

    html += "<table border=5 cellpadding=5 cellspacing=2><tr><th>name</th><th>type</th><th>description</th></tr>"
    for field in fields:
        html += "<tr><td>{name}</td><td>{type}</td><td dir=rtl align=right>{description}</td></tr>".format(
            name=("{}" if field["name"] not in primaryKey else "<strong>{}</strong> (primaryKey)").format(
                field["name"]),
            type=field["type"],
            description=field.get("description", ""))
    html += "</table>"

    return html

def filter_resources(datapackage, resources, parameters):
    save_schema = DEFAULT_SAVE_SCHEMA.format(table_name=datapackage["name"])
    if not os.path.exists(os.path.dirname(save_schema)):
        try:
            os.makedirs(os.path.dirname(save_schema))
        except OSError as e:
            logging.exception(e)
            raise

    tables = []
    for resource_descriptor, resource_data in zip(datapackage["resources"], resources):
        schema = resource_descriptor["schema"]
        tables.append(_get_schema_table(resource_descriptor["name"], schema["fields"], schema["primaryKey"]))

        yield filter_resource(resource_descriptor, resource_data)

    html = """<html><head></head><body>{tables}</body></html>""".format(tables="".join(tables))
    with open(save_schema, "w") as f:
        f.write(html)


spew(datapackage, filter_resources(datapackage, resources, parameters))
