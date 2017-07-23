from datapackage_pipelines_knesset.dataservice.processors.base_processor import BaseDataserviceProcessor
from knesset_data.dataservice.base import BaseKnessetDataServiceCollectionObject


class AddDataserviceCollectionResourceProcessor(BaseDataserviceProcessor):

    def _get_base_dataservice_class(self):
        return BaseKnessetDataServiceCollectionObject

    def _extend_dataservice_class(self, dataservice_class):
        class ExtendedDataserviceClass(dataservice_class):
            SERVICE_NAME = self._parameters["service-name"]
            METHOD_NAME = self._parameters["method-name"]
            DEFAULT_ORDER_BY_FIELD = self._parameters.get("order_by", "id")
        return ExtendedDataserviceClass

    def _get_dataservice_objects(self):
        for dataservice_object in self.dataservice_class.get_all():
            yield self._filter_dataservice_object(dataservice_object)

    def _process(self, datapackage, resources):
        return self._process_append(datapackage, resources)


if __name__ == '__main__':
    AddDataserviceCollectionResourceProcessor.main()
