from datapackage_pipelines_knesset.common.base_processors.base_resource import BaseResourceProcessor


class FilterResourceBaseProcessor(BaseResourceProcessor):

    def _is_matching_resource_descriptor(self, resource_number, resource_descriptor):
        # match the name of the input resource
        return resource_descriptor["name"] == self._get_input_resource_name()

    def _get_input_resource_name(self):
        # by default - uses the same name for input and output resources
        return self._get_output_resource_name()
