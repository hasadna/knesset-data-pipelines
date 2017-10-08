from datapackage_pipelines_knesset.common.base_processors.base import BaseProcessor
from datapackage_pipelines.utilities.resources import PROP_STREAMING


class BaseResourceProcessor(BaseProcessor):
    """Base class for processing a single resource"""

    def __init__(self, *args, **kwargs):
        super(BaseResourceProcessor, self).__init__(*args, **kwargs)
        # the descriptor of the selected resource (only 1 resource is processed by this processor)
        self._resource_descriptor = None
        # the selected resource number
        self._resource_number = None

    def _get_schema(self, resource_descriptor):
        # can be extended to provide a hard-coded schema
        # or to modify the schema from the input resource descriptor
        return resource_descriptor.get("schema", {"fields": []})

    def _get_output_resource_name(self):
        return self._parameters.get("resource")

    def _get_output_resource_path(self):
        return "data/{}.csv".format(self._get_output_resource_name())

    def _is_matching_resource_descriptor(self, resource_number, resource_descriptor):
        # see the comment on _is_matching_resource_number
        return resource_descriptor["name"] == self._get_output_resource_name()

    def _is_matching_resource_number(self, resource_number, resource_descriptor=None):
        # this is called from both _filter_resource_descriptors and filter_resources
        # the first one that matches will store the resource number
        # for example, if resource_descriptor matched an input resource -
        # it will use the same nubmer for matching the output resource
        if self._resource_number is None:
            if not resource_descriptor:
                resource_descriptor = self._get_resource_descriptor(resource_number)
            if self._is_matching_resource_descriptor(resource_number, resource_descriptor):
                self._resource_number = resource_number
                return True
            else:
                return False
        else:
            return self._resource_number == resource_number

    def _filter_resource_descriptors(self, resource_descriptors):
        filtered_descriptors = []
        for resource_number, resource_descriptor in enumerate(resource_descriptors):
            if self._is_matching_resource_number(resource_number, resource_descriptor):
                resource_descriptor = self._filter_resource_descriptor(resource_number, resource_descriptor)
            filtered_descriptors.append(resource_descriptor)
        return filtered_descriptors

    def _filter_resource_descriptor(self, resource_number, resource_descriptor):
        # allows to modify the resource descriptor
        # if you just need to modify the schema - you should extend _get_schema instead
        self._schema = self._get_schema(resource_descriptor)
        resource_descriptor =  dict(resource_descriptor, **{"name": self._get_output_resource_name(),
                                                            "path": self._get_output_resource_path(),
                                                            "schema": self._schema,
                                                            PROP_STREAMING: True})
        self._resource_descriptor = resource_descriptor
        return resource_descriptor

    def _filter_resources(self, resources):
        # modified to only call filter methods for the matching resource
        # other resources are yielded as-is without any processing
        for resource_number, resource_data in enumerate(resources):
            if self._is_matching_resource_number(resource_number):
                yield self._filter_resource(resource_number, resource_data)
            else:
                yield resource_data

    def _filter_resource(self, resource_number, resource_data):
        # this method is called only for the matching resource
        # it should be extended to provide code to run before or after iterating over the data
        self._delay_limit_initialize()
        yield from super(BaseResourceProcessor, self)._filter_resource(resource_number, resource_data)

    def _filter_row(self, resource_number, row):
        # this method is called only the matching resource's rows
        for row in super(BaseResourceProcessor, self)._filter_row(resource_number, row):
            if self._delay_limit_check():
                self._incr_stat("delay limit skipped rows")
            else:
                yield row
