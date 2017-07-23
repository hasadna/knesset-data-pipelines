from datapackage_pipelines_knesset.common.processors.base_processor import BaseProcessor
from knesset_data.dataservice.base import KnessetDataServiceSimpleField
from datapackage_pipelines_knesset.dataservice.exceptions import InvalidStatusCodeException, ReachedMaxRetries
import datetime, requests, logging, time
from itertools import chain


def get_retry_response_content(url, params, timeout, proxies, retry_num, num_retries, seconds_between_retries):
    proxies = proxies if proxies else {}
    try:
        response = requests.get(url, params=params, timeout=timeout, proxies=proxies)
    except requests.exceptions.InvalidSchema:
        # missing dependencies for SOCKS support
        raise
    except requests.RequestException as e:
        # network / http problem - start the retry mechanism
        if (retry_num < num_retries):
            logging.exception(e)
            logging.info("retry {} / {}, waiting {} seconds before retrying...".format(retry_num,
                                                                                       num_retries,
                                                                                       seconds_between_retries))
            time.sleep(seconds_between_retries)
            return get_retry_response_content(url, params, timeout, proxies, retry_num + 1, num_retries, seconds_between_retries)
        else:
            raise ReachedMaxRetries(e)
    if response.status_code != 200:
        # http status_code is not 200 - retry won't help here
        raise InvalidStatusCodeException(response.status_code, response.content)
    else:
        return response.content


class BaseDataserviceProcessor(BaseProcessor):

    def __init__(self, *args, **kwargs):
        super(BaseDataserviceProcessor, self).__init__(*args, **kwargs)
        fields = []
        class DataServiceClass(self._get_base_dataservice_class()):
            ORDERED_FIELDS = []
            for name, field in self._parameters["fields"].items():
                field_source = field.pop("source")
                field["name"] = name
                # dump.to_path forces these formats for dates
                if field["type"] == "datetime":
                    field["format"] = "fmt:%Y-%m-%d %H:%M:%S.%f"
                elif field["type"] == "date":
                    field["format"] = "fmt:%Y-%m-%d"
                fields.append(field)
                ORDERED_FIELDS.append((name, KnessetDataServiceSimpleField(field_source, field["type"])))
        self.schema = {"fields": fields,
                       "primaryKey": "id"}
        self.dataservice_class = self._extend_dataservice_class(DataServiceClass)

    def _get_base_dataservice_class(self):
        raise NotImplementedError()

    def _extend_dataservice_class(self, dataservice_class):
        num_retries = self._parameters.get("NUM_RETRIES", 5)
        seconds_between_retries = self._parameters.get("SECONDS_BETWEEN_RETRIES", 60)
        class BaseExtendedDataserviceClass(dataservice_class):
            @classmethod
            def _get_response_content(cls, url, params, timeout, proxies, retry_num=1):
                return get_retry_response_content(url, params, timeout, proxies, retry_num, num_retries, seconds_between_retries)
        return BaseExtendedDataserviceClass

    def _filter_output_row(self, row):
        for field in self.schema["fields"]:
            value = row[field["name"]]
            if value is None:
                value = ""
            else:
                if isinstance(value, (datetime.datetime,datetime.date)):
                    if field["type"] == "datetime":
                        value = value.strftime("%Y-%m-%d %H:%M:%S.%f")
                    elif field["type"] == "date":
                        value = value.strftime("%Y-%m-%d")
                elif isinstance(value, bool):
                    value = "true" if value else "false"
                elif isinstance(value, int):
                    value = str(value)
            row[field["name"]] = value
        return row

    def _get_dataservice_objects(self, *args, **kwargs):
        raise NotImplementedError()

    def _filter_dataservice_object(self, dataservice_object):
        return self._filter_output_row(dataservice_object.all_field_values())

    def _filter_row(self, row, **kwargs):
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
                                           schema=self.schema)
        return super(BaseDataserviceProcessor, self)._process(datapackage, self._filter_resources(datapackage, resources))

    def _process_append(self, datapackage, resources):
        datapackage["resources"].append({"name": self._parameters["resource-name"],
                                         "schema": self.schema,
                                         "path": "{}.csv".format(self._parameters["resource-name"])})
        resources = chain(resources, [self._get_dataservice_objects()])
        return super(BaseDataserviceProcessor, self)._process(datapackage, resources)
