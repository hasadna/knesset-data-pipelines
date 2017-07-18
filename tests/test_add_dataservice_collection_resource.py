from processors.add_dataservice_collection_resource import Processor, DynamicKnessetDataserviceCollection
import requests
import os
import json


class MockDynamicKnessetDataserviceCollection(DynamicKnessetDataserviceCollection):

    @classmethod
    def _get_url_base(cls):
        return "http://" + cls._get_service_name() + '/' + cls._get_method_name()

    @classmethod
    def _get_response_content(cls, url, params, timeout, proxies):
        filename = os.path.join(os.path.dirname(__file__),
                                "mocks", "Odata_old_CommitteeScheduleData_View_committee")
        if not os.path.exists(filename):
            response = requests.get("http://knesset.gov.il/Odata_old/CommitteeScheduleData.svc/View_committee",
                                    params=params,
                                    timeout=timeout,
                                    proxies=proxies)
            status_code, content = response.status_code, response.content
            with open(filename, "w") as f:
                json.dump([status_code, content.decode()], f)
        with open(filename) as f:
            status_code, content = json.load(f)
        if status_code != 200:
            raise Exception("invalid response status code: {}".format(status_code))
        else:
            return content


class MockProcessor(Processor):

    def _get_collection_class(self):
        return MockDynamicKnessetDataserviceCollection


def test():
    datapackage = {"name": "dummy", "resources": []}
    parameters = {"resource-name": "dummy",
                  "service-name": "dummy_service",
                  "method-name": "DummyMethod",
                  "fields": {"id": {"source": "committee_id", "type": "integer"},
                             "name": {"source": "committee_name", "type": "string"}}}
    processor = MockProcessor(datapackage=datapackage, parameters=parameters)
    datapackage, resources = processor.spew()
    assert datapackage == {'name': 'dummy',
                           'resources': [{'name': 'dummy',
                                          'path': 'dummy.csv',
                                          'schema': {'fields': [{'name': 'id', 'type': 'integer'},
                                                                {"name": "name", "type": "string"}]}}]}
    resources = list(resources)
    assert len(resources) == 1
    resource = resources[0]
    row = next(resource)
    assert row == {"id": 1, "name": "ועדת הכנסת"}



