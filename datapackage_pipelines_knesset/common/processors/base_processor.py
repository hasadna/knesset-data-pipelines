from itertools import chain


class BaseProcessor(object):

    def __init__(self, parameters=None, datapackage=None, resources=None):
        self._parameters = parameters if parameters else {}
        self._datapackage = datapackage if datapackage else {}
        self._resources = resources if resources else []
        self._schema = {"fields": []}

    @classmethod
    def main(cls):
        from datapackage_pipelines.wrapper import ingest, spew
        spew(*cls(*ingest()).spew())

    def spew(self):
        self._datapackage, self._resources = self._process(self._datapackage, self._resources)
        return self._datapackage, self._resources

    def _process(self, datapackage, resources):
        # extending classes should return either _process_filter or _process_append
        # _process_filter: filters an input resource and emits output resource
        #                  parameters: input-resource, output-resource
        # _process_append: adds a new resource
        #                  parameters: resource-name
        raise NotImplementedError()

    def _get_resource(self):
        # will be called in case of _process_append
        # should yield all the resource items
        raise NotImplementedError()

    def _filter_row(self, row, **kwargs):
        # will be called in case of _process_filter
        # gets the input row and can yield multiple output rows
        raise NotImplementedError()

    def _filter_resource(self, data):
        for row in data:
            yield from self._filter_row(row)

    def _filter_resources(self, datapackage, resources):
        for resource_descriptor, data in zip(datapackage["resources"], resources):
            if resource_descriptor["name"] == self._parameters["output-resource"]:
                yield self._filter_resource(data)
            else:
                yield data

    def _process_filter(self, datapackage, resources):
        for resource_descriptor in datapackage["resources"]:
            if resource_descriptor["name"] == self._parameters["input-resource"]:
                resource_descriptor.update(name=self._parameters["output-resource"],
                                           path="{}.csv".format(self._parameters["output-resource"]),
                                           schema=self._schema)
        return datapackage, self._filter_resources(datapackage, resources)

    def _process_append(self, datapackage, resources):
        datapackage["resources"].append({"name": self._parameters["resource-name"],
                                         "schema": self._schema,
                                         "path": "{}.csv".format(self._parameters["resource-name"])})
        resources = chain(resources, [self._get_resource()])
        return datapackage, resources
