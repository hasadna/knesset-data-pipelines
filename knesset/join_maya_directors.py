from datapackage_pipelines.wrapper import ingest, spew


parameters, datapackage, resources = ingest()


resources_names = [(resource, descriptor["name"]) for resource, descriptor in zip(resources, datapackage["resources"])]


def get_resource():
    for resource, name in resources_names:
        for row in resource:
            row["year"] = name
            yield row


datapackage["resources"] = [datapackage["resources"][0]]
datapackage["resources"][0]["schema"]["fields"].append({"name": "year", "type": "integer"})
datapackage["resources"][0].update(name="maya_directors", path="maya_directors.csv")


spew(datapackage, [get_resource()])
