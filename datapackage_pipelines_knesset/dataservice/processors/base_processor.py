from datapackage_pipelines_knesset.common.processors.base_processor import BaseProcessor
from knesset_data.dataservice.base import KnessetDataServiceSimpleField
from datapackage_pipelines_knesset.retry_get_response_content import get_retry_response_content




class BaseDataserviceProcessor(BaseProcessor):

    def __init__(self, *args, **kwargs):
        super(BaseDataserviceProcessor, self).__init__(*args, **kwargs)
        fields = []
        self._primary_key_field_name = "id"
        class DataServiceClass(self._get_base_dataservice_class()):
            ORDERED_FIELDS = []
            for name, field in self._parameters["fields"].items():
                field_source = field.pop("source", None)
                if field.pop("primaryKey", False):
                    self._primary_key_field_name = name
                field["name"] = name
                # dump.to_path forces these formats for dates
                if field["type"] == "datetime":
                    field["format"] = "fmt:%Y-%m-%d %H:%M:%S.%f"
                elif field["type"] == "date":
                    field["format"] = "fmt:%Y-%m-%d"
                fields.append(field)
                if field_source:
                    field_source = field_source.format(name=name)
                    ORDERED_FIELDS.append((name, KnessetDataServiceSimpleField(field_source, field["type"])))
        self._schema = {"fields": fields,}
                       # better not to define primary key in the schema as knesset has a bug which might duplicate primary keys...
                       # see https://github.com/hasadna/knesset-data/issues/148
                       # "primaryKey": [self._primary_key_field_name]}
        self.dataservice_class = self._extend_dataservice_class(DataServiceClass)

    def _get_base_dataservice_class(self):
        raise NotImplementedError()

    def _extend_dataservice_class(self, dataservice_class):
        num_retries = self._parameters.get("num-retries", 10)
        seconds_between_retries = self._parameters.get("seconds-between-retries", 60)
        class BaseExtendedDataserviceClass(dataservice_class):
            @classmethod
            def _get_response_content(cls, url, params, timeout, proxies, retry_num=1):
                return get_retry_response_content(url, params, timeout, proxies, retry_num, num_retries, seconds_between_retries)
        return BaseExtendedDataserviceClass

    def _filter_output_row(self, row):
        for field in self._schema["fields"]:
            value = row.get(field["name"], None)
            row[field["name"]] = value
        return row

    def _get_dataservice_objects(self, *args, **kwargs):
        raise NotImplementedError()

    def _filter_dataservice_object(self, dataservice_object):
        return self._filter_output_row(dataservice_object.all_field_values())
