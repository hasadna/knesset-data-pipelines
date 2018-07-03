from datapackage_pipelines.wrapper import ingest, spew


parameters, datapackage, resources = ingest()


for resource in datapackage["resources"]:
    if resource["name"] == parameters["src"]:
        resource.update(name=parameters["dst"],
                        path=parameters["dst"] + ".csv")


spew(datapackage, resources)
