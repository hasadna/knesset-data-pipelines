from datapackage_pipelines_knesset.dataservice.processors.base_processor import BaseDataserviceProcessor
from knesset_data.dataservice.base import BaseKnessetDataServiceCollectionObject
import os
from datapackage_pipelines_knesset.common.influxdb import send_metric_parameters


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
        for dataservice_object in self.dataservice_class.get_all():
            resources_yielded += 1
            if os.environ.get("OVERRIDE_DATASERVICE_COLLECTION_LIMIT_ITEMS",""):
                if int(os.environ.get("OVERRIDE_DATASERVICE_COLLECTION_LIMIT_ITEMS","")) < resources_yielded:
                    return
            row = self._filter_dataservice_object(dataservice_object)
            self._send_metric("filter_row", {}, {"fields": len(row)})
            yield row
        self._send_metric("filter_resource", {}, {"filtered_rows": resources_yielded})

    def _process(self, datapackage, resources):
        return self._process_append(datapackage, resources)

    def _send_metric(self, measurement, tags, values):
        parameters = {"metric-tags": {"pipeline": self._parameters["resource-name"],
                                      "processor": "add_dataservice_collection_resource"}}
        send_metric_parameters(measurement, tags, values, parameters)


if __name__ == '__main__':
    AddDataserviceCollectionResourceProcessor.main()
