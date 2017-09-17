from datapackage_pipelines_knesset.common.base_processors.base_resource import BaseResourceProcessor


class AddResourceBaseProcessor(BaseResourceProcessor):

    def _get_new_resource_descriptor(self):
        # you can use this to add attributes (other then schema / path / name - which are added automatically)
        return {}

    def _get_new_resource(self):
        # should yield the new resource rows
        # the rows will be processed further via the standard filter_resources / filter_resource / filter_ros methods
        yield from []

    def _is_matching_resource_number(self, resource_number, resource_descriptor=None):
        # no matching needed, we append the resource
        return False

    def _filter_resource_descriptors(self, resource_descriptors):
        descriptors = super(AddResourceBaseProcessor, self)._filter_resource_descriptors(resource_descriptors)
        # append the new resource descriptor
        self._resource_number = len(descriptors)
        descriptors.append(self._filter_resource_descriptor(self._resource_number, self._get_new_resource_descriptor()))
        return descriptors

    def _filter_resources(self, resources):
        yield from super(AddResourceBaseProcessor, self)._filter_resources(resources)
        yield self._filter_resource(self._resource_number, self._get_new_resource())
