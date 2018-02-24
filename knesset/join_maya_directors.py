from datapackage_pipelines.wrapper import ingest, spew


parameters, datapackage, resources = ingest()


resources_names = [(resource, descriptor["name"]) for resource, descriptor in zip(resources, datapackage["resources"])]


def get_resource():
    for resource, name in resources_names:
        for row in resource:
            row["id"] = row[""]
            del row[""]
            row["year"] = name
            for k,v in row.items():
              if not v:
                  row[k] = ""
              else:
                  row[k] = str(v)
            yield row


datapackage["resources"] = [datapackage["resources"][0]]
for field in datapackage["resources"][0]["schema"]["fields"]:
    field["type"] = "string"
datapackage["resources"][0]["schema"]["fields"].append({"name": "year", "type": "string"})
datapackage["resources"][0].update(name="maya_directors", path="maya_directors.csv")
datapackage["resources"][0]["schema"]["fields"][0]["name"] = "id"


spew(datapackage, [get_resource()])
