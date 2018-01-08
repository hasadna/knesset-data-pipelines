from datapackage_pipelines.wrapper import ingest, spew


parameters, datapackage, resources = ingest()


def get_resource(resource):
    for row in resource:
        yield row


def get_resources():
    for resource in resources:
        yield get_resource(resource)


spew(datapackage, get_resources())
