from datapackage_pipelines_knesset.dataservice.exceptions import InvalidStatusCodeException
from datapackage_pipelines_knesset.dataservice.processors.add_dataservice_collection_resource import AddDataserviceCollectionResourceProcessor
from datapackage_pipelines_knesset.dataservice.processors.dataservice_function_resource import DataserviceFunctionResourceProcessor
from datapackage_pipelines_knesset.retry_get_response_content import get_retry_response_content

import os
import json
from urllib.parse import urlparse, parse_qs


def get_mock_response_content(filename, url, params, timeout, proxies, retry_num,
                              num_retries=0, seconds_between_retries=0):
    if not filename:
        raise Exception("unknown url / params: {} / {}".format(url, params))
    if retry_num > 1:
        filename += "_retry_{}".format(retry_num)
    filename = os.path.join(os.path.dirname(__file__), filename)
    if not os.path.exists(filename):
        try:
            response_content = get_retry_response_content(url, params, timeout, proxies, retry_num,
                                                                         num_retries, seconds_between_retries)
            status_code = 200
        except InvalidStatusCodeException as e:
            status_code, response_content = e.status_code, e.response_content
        with open(filename, "w") as f:
            json.dump([status_code, response_content.decode()], f)
    with open(filename) as f:
        status_code, response_content = json.load(f)
    if status_code != 200:
        raise InvalidStatusCodeException(status_code, response_content)
    else:
        return response_content


class MockAddDataserviceCollectionResourceProcessor(AddDataserviceCollectionResourceProcessor):

    def _extend_dataservice_class(self, dataservice_class):
        BaseDataserviceClass = super(MockAddDataserviceCollectionResourceProcessor, self)._extend_dataservice_class(dataservice_class)

        class ExtendedDataserviceClass(BaseDataserviceClass):

            @classmethod
            def _get_filename(cls, url, params):
                if url == "http://knesset.gov.il/Odata_old/CommitteeScheduleData.svc/View_committee":
                    return "Odata_old_CommitteeScheduleData_View_committee.json"
                elif url.startswith("http://knesset.gov.il/Odata/ParliamentInfo.svc//KNS_"):
                    if len(params) > 0:
                        raise Exception("unexpected params")
                    return "odata_parliamentinfo_kns_{}.json".format(url.replace("http://knesset.gov.il/Odata/ParliamentInfo.svc//KNS_", ""))

            @classmethod
            def _get_response_content(cls, url, params, timeout, proxies, retry_num=1):
                filename = cls._get_filename(url, params)
                return get_mock_response_content(filename, url, params, timeout, proxies, retry_num)

        return ExtendedDataserviceClass


class MockDataserviceFunctionResourceProcessor(DataserviceFunctionResourceProcessor):

    def _extend_dataservice_class(self, dataservice_class):
        BaseDataserviceClass = super(MockDataserviceFunctionResourceProcessor, self)._extend_dataservice_class(dataservice_class)
        class ExtendedDataserviceClass(BaseDataserviceClass):

            @classmethod
            def _get_filename(cls, url, params):
                if url.startswith(
                        "http://online.knesset.gov.il/WsinternetSps/KnessetDataService/CommitteeScheduleData.svc/CommitteeAgendaSearch?"):
                    qs = parse_qs(urlparse(url).query)
                    return "CommitteeScheduleDava.svc_CommitteeAgendaSearch_CommitteeId_{}_{}_{}".format(
                        ",".join(qs["CommitteeId"]),
                        ",".join(qs["FromDate"]),
                        ",".join(qs["ToDate"]))

            @classmethod
            def _get_response_content(cls, url, params, timeout, proxies, retry_num=1):
                filename = cls._get_filename(url, params)
                return get_mock_response_content(filename, url, params, timeout, proxies, retry_num)

        return ExtendedDataserviceClass
