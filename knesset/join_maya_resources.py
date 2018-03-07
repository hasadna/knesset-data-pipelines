from datapackage_pipelines.wrapper import ingest, spew
import logging


parameters, datapackage, resources, stats = ingest() + ({},)


resource_names = [descriptor["name"] for descriptor in datapackage["resources"]]


def get_row(resource_name, row):
    stats["num rows"] += 1
    row["_"] = row[""]
    del row[""]
    row["year"] = resource_name
    row["rownum"] = stats["num rows"]
    return row


def get_resource():
    stats["num rows"] = 0
    for resource_name, resource in zip(resource_names, resources):
        for row in resource:
            yield get_row(resource_name, row)


datapackage = dict(datapackage, resources=[datapackage["resources"][0]])
datapackage["resources"][0].update(name='maya', path='maya.csv')
for field in datapackage["resources"][0]["schema"]["fields"]:
    if field["name"] == "":
        field["name"] = "_"
datapackage["resources"][0]["schema"]["fields"] += [{"name": "year", "type": "string"},
                                                    {"name": "rownum", "type": "integer"}]
datapackage["resources"][0]["schema"]["primaryKey"] = ["rownum"]


spew(datapackage, [get_resource()], stats)
