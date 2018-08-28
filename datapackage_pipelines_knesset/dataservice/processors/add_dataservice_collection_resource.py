from datapackage_pipelines_knesset.dataservice.processors.base_processor import BaseDataserviceProcessor
from knesset_data.dataservice.base import BaseKnessetDataServiceCollectionObject
import os, logging
from datapackage_pipelines_knesset.common import utils
from datapackage_pipelines_knesset.common.utils import process_metrics
from datapackage_pipelines.utilities.resources import PROP_STREAMING
from itertools import chain
import datetime
from kvfile import KVFile


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

    def _get_resource(self, last_update_resource=None):
        last_kvfile, last_update, key_fields, incremental_field = None, None, None, None
        if last_update_resource is not None:
            last_kvfile = KVFile()
            key_fields = self._parameters.get('incremental-field-key', [self._primary_key_field_name])
            incremental_field = self._parameters['incremental-field']
            for row in last_update_resource:
                key = '-'.join([str(row[k]) for k in key_fields])
                try:
                    last_row = last_kvfile.get(key)
                except KeyError:
                    last_row = None
                if not last_row or last_row[incremental_field] < row[incremental_field]:
                    last_kvfile.set(key, dict(row))
                    if not last_update or last_update < row[incremental_field]:
                        last_update = row[incremental_field]
            if last_update:
                logging.info('last_update={}'.format(last_update))
        resources_yielded = 0
        with utils.temp_loglevel():
            logging.info("Loading dataservice resource from service {} method {}".format(self._parameters["service-name"],
                                                                                         self._parameters["method-name"]))
            # with process_metrics('dataservice_collection_row',
            #                      {'service_name': self._parameters['service-name'],
            #                       'method_name': self._parameters['method-name']}) as send_process_metrics:
            if last_update:
                if self._parameters.get('incremental-field-type') == 'integer':
                    last_update_str = last_update
                else:
                    last_update_str = (last_update - datetime.timedelta(days=1)).strftime('%Y-%m-%d')
                since_last_update = (self._parameters['incremental-field'],
                                     last_update_str,
                                     self._parameters.get('incremental-field-type', 'datetime'))
            else:
                since_last_update = None
            for dataservice_object in self.dataservice_class.get_all(since_last_update=since_last_update):
                row = self._filter_dataservice_object(dataservice_object)
                if os.environ.get("OVERRIDE_DATASERVICE_COLLECTION_LIMIT_ITEMS",""):
                    if int(os.environ.get("OVERRIDE_DATASERVICE_COLLECTION_LIMIT_ITEMS","")) < resources_yielded:
                        return
                for k in row:
                    for field in self._schema["fields"]:
                        if field["name"] == k:
                            if field["type"] == "integer" and row[k] is not None:
                                row[k] = int(row[k])
                if last_update:
                    key = '-'.join([str(row[k]) for k in key_fields])
                    last_kvfile.set(key, dict(row))
                else:
                    resources_yielded += 1
                    yield row
                # send_process_metrics()
                if resources_yielded > 0 and resources_yielded%10000 == 0:
                    logging.info("Loaded {} dataservice objects".format(resources_yielded))
            if last_update:
                for key, row in last_kvfile.items():
                    resources_yielded += 1
                    yield row
                    if resources_yielded%10000 == 0:
                        logging.info("Loaded {} dataservice objects".format(resources_yielded))

    def _get_resources_incremental(self, last_resource_index, resources):
        last_update_resource = None
        for i, resource in enumerate(resources):
            if i == last_resource_index:
                last_update_resource = resource
            else:
                yield resource
        yield self._get_resource(last_update_resource)

    def _process(self, datapackage, resources):
        last_resource_index = None
        if self._parameters.get('incremental-field') and os.environ.get('KNESSET_DATASERVICE_INCREMENTAL'):
            for i, descriptor in enumerate(datapackage['resources']):
                if descriptor['name'] == 'last_' + self._parameters['resource-name']:
                    last_resource_index = i
            if last_resource_index is not None:
                del datapackage['resources'][last_resource_index]
        datapackage["resources"].append({"name": self._parameters["resource-name"],
                                         "schema": self._schema,
                                         "path": "{}.csv".format(self._parameters["resource-name"]),
                                         PROP_STREAMING: True})
        if self._parameters.get('incremental-field') and os.environ.get('KNESSET_DATASERVICE_INCREMENTAL'):
            return datapackage, self._get_resources_incremental(last_resource_index, resources)
        else:
            resources = chain(resources, [self._get_resource()])
            return datapackage, resources



if __name__ == '__main__':
    AddDataserviceCollectionResourceProcessor.main()
