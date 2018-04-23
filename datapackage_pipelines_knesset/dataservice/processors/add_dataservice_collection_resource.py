from datapackage_pipelines_knesset.dataservice.processors.base_processor import BaseDataserviceProcessor
from knesset_data.dataservice.base import BaseKnessetDataServiceCollectionObject
import os, logging
from datapackage_pipelines_knesset.common import utils
from datapackage_pipelines_knesset.common.utils import process_metrics


class AddDataserviceCollectionResourceProcessor(BaseDataserviceProcessor):

    def _get_base_dataservice_class(self):
        return BaseKnessetDataServiceCollectionObject

    def _extend_dataservice_class(self, dataservice_class):
        BaseDataserviceClass = super(AddDataserviceCollectionResourceProcessor, self)._extend_dataservice_class(dataservice_class)
        class ExtendedDataserviceClass(BaseDataserviceClass):
            SERVICE_NAME = self._parameters["service-name"]
            METHOD_NAME = self._parameters["method-name"]
            DEFAULT_ORDER_BY_FIELD = self._parameters.get("order_by", self._primary_key_field_name)
        return ExtendedDataserviceClass

    def _get_resource(self):
        resources_yielded = 0
        with utils.temp_loglevel():
            logging.info("Loading dataservice resource from service {} method {}".format(self._parameters["service-name"],
                                                                                         self._parameters["method-name"]))
            with process_metrics('dataservice_collection_row',
                                 {'service_name': self._parameters['service-name'],
                                  'method_name': self._parameters['method-name']}) as send_process_metrics:
                for dataservice_object in self.dataservice_class.get_all():
                    resources_yielded += 1
                    if os.environ.get("OVERRIDE_DATASERVICE_COLLECTION_LIMIT_ITEMS",""):
                        if int(os.environ.get("OVERRIDE_DATASERVICE_COLLECTION_LIMIT_ITEMS","")) < resources_yielded:
                            return
                    row = self._filter_dataservice_object(dataservice_object)
                    for k in row:
                        for field in self._schema["fields"]:
                            if field["name"] == k:
                                if field["type"] == "integer" and row[k] is not None:
                                    row[k] = int(row[k])
                    yield row
                    send_process_metrics()
                    if resources_yielded%10000 == 0:
                        logging.info("Loaded {} dataservice objects".format(resources_yielded))

    def _process(self, datapackage, resources):
        return self._process_append(datapackage, resources)


if __name__ == '__main__':
    AddDataserviceCollectionResourceProcessor.main()
