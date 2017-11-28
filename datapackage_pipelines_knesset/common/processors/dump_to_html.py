from datapackage_pipelines.wrapper import ingest, spew
from datapackage_pipelines_knesset.common import object_storage
import logging, json

DEFAULT_SAVE_SCHEMA = "aggregations/{table_name}.{ext}"

parameters, datapackage, resources = ingest()

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


def filter_resource(descriptor, data, stats):
    for row in data:
        stats[descriptor["name"]] += 1
        yield row

def filter_resources(datapackage, resources, parameters, stats):
    tables = []
    for resource_descriptor, resource_data in zip(datapackage["resources"], resources):
        schema = resource_descriptor["schema"]
        stats[resource_descriptor["name"]] = 0
        tables.append(_get_schema_table(resource_descriptor["name"], schema["fields"], schema.get("primaryKey", [])))

        yield filter_resource(resource_descriptor, resource_data, stats)

    html = """<html><head><meta charset="UTF-8"></head><body>{tables}</body></html>""".format(tables="".join(tables))

    save_schema = parameters.get("save-schema", DEFAULT_SAVE_SCHEMA)
    if save_schema:
        save_schema_html = DEFAULT_SAVE_SCHEMA.format(table_name=datapackage["name"], ext="html")
        save_schema_json = DEFAULT_SAVE_SCHEMA.format(table_name=datapackage["name"], ext="json")

        s3 = object_storage.get_s3()
        object_storage.write(s3, parameters["bucket"], save_schema_html, html, public_bucket=True)
        object_storage.write(s3, parameters["bucket"], save_schema_json, json.dumps(datapackage["resources"], indent=2, ensure_ascii=False), public_bucket=True)

stats = {}
spew(datapackage, filter_resources(datapackage, resources, parameters, stats), stats)
