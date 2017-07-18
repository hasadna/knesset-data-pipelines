from processors.base_processor import BaseProcessor
from itertools import chain
from knesset_data.dataservice.base import BaseKnessetDataServiceCollectionObject, KnessetDataServiceSimpleField
import logging


class DynamicKnessetDataserviceCollection(BaseKnessetDataServiceCollectionObject):

    def __init__(self, *args, **kwargs):
        super(DynamicKnessetDataserviceCollection, self).__init__(*args, **kwargs)


class Processor(BaseProcessor):

    def _get_collection_class(self):
        return DynamicKnessetDataserviceCollection

    def _get_schema_collection(self):
        fields = []
        class Collection(self._get_collection_class()):
            SERVICE_NAME = self._parameters["service-name"]
            METHOD_NAME = self._parameters["method-name"]
            DEFAULT_ORDER_BY_FIELD = self._parameters.get("order_by", "id")
            ORDERED_FIELDS = []
            for name, field in self._parameters["fields"].items():
                field_source = field.pop("source")
                field["name"] = name
                fields.append(field)
                ORDERED_FIELDS.append((name, KnessetDataServiceSimpleField(field_source, field["type"])))
        return {"fields": fields}, Collection

    def _get_collection_items(self, collection_class):
        for item in collection_class.get_all():
            item = item.all_field_values()
            yield item

    def _process(self, datapackage, resources):
        schema, collection_class = self._get_schema_collection()
        datapackage["resources"].append({"name": self._parameters["resource-name"],
                                         "schema": schema,
                                         "path": "{}.csv".format(self._parameters["resource-name"])})
        resources = chain(resources, [self._get_collection_items(collection_class)])
        return super(Processor, self)._process(datapackage, resources)


if __name__ == '__main__':
    Processor.main()
