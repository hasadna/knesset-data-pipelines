import os, yaml
from copy import deepcopy
from tableschema.field import Field
from .mocks.dataservice import MockAddDataserviceCollectionResourceProcessor
from itertools import chain


def get_pipeline_processor_parameters(pipeline_spec, pipeline_name, processor_matcher):
    with open(os.path.join(os.path.dirname(__file__), '..', pipeline_spec, 'pipeline-spec.yaml')) as f:
        pipeline_spec = yaml.load(f)
        for step in pipeline_spec[pipeline_name]["pipeline"]:
            if processor_matcher(step):
                return step["parameters"]

def get_pipeline_processor_parameters_schema(pipeline_spec, pipeline_name, processor_matcher):
    parameters = get_pipeline_processor_parameters(pipeline_spec, pipeline_name, processor_matcher)
    schema_fields = []
    for field_name, field in parameters["fields"].items():
        field = deepcopy(field)
        field.pop("source", None)
        field["name"] = field_name
        if field["type"] == "datetime":
            field["format"] = "fmt:%Y-%m-%d %H:%M:%S.%f"
        elif field["type"] == "date":
            field["format"] = "fmt:%Y-%m-%d"
        schema_fields.append(field)
    return parameters, {"fields": schema_fields,
                       "primaryKey": ["id"]}

def assert_conforms_to_schema(schema, doc):
    assert isinstance(doc, dict), "invalid doc: {}".format(doc)
    for field in schema["fields"]:
        value = doc[field["name"]]
        assert Field(field).test_value(value), "value {} does not conform to schema {}".format(value, field)

def get_dataservice_processor_data(pipeline_spec_name, pipeline_name, expected_schema=None):
    datapackage = {"name": "_", "resources": []}
    processor_matcher = lambda step: step["run"] == "..datapackage_pipelines_knesset.dataservice.processors.add_dataservice_collection_resource"
    parameters, schema = get_pipeline_processor_parameters_schema(pipeline_spec_name, pipeline_name,
                                                                  processor_matcher)
    processor = MockAddDataserviceCollectionResourceProcessor(datapackage=datapackage,
                                                              parameters=parameters)
    datapackage, resources = processor.spew()
    assert datapackage["name"] == "_"
    assert len(datapackage["resources"]) == 1
    resource = datapackage["resources"][0]
    assert resource["name"] == pipeline_name
    assert resource["path"] == '{}.csv'.format(pipeline_name)
    if expected_schema is not None:
        assert resource["schema"] == expected_schema, dict(resource["schema"])
    resources = list(resources)
    assert len(resources) == 1
    resource = resources[0]
    first_row = next(resource)
    # peeks at the first row - to validate the schema
    assert_conforms_to_schema(schema, first_row)
    return chain([first_row], resource)

def assert_dataservice_processor_data(pipeline_spec_name, pipeline_name, expected_data, expected_schema=None):
    data = get_dataservice_processor_data(pipeline_spec_name, pipeline_name, expected_schema=expected_schema)
    if len(expected_data) < 1:
        try:
            row = next(data)
        except StopIteration:
            assert True
        else:
            assert False, "no data was expected, got this row: {}".format(dict(row))
    else:
        for expected_row in expected_data:
            actual_row = next(data)
            if len(expected_row) == 0:
                assert len(actual_row) == 0, dict(actual_row)
            else:
                actual_row = {k: actual_row[k] for k in expected_row}
                assert actual_row == expected_row, "actual_row = {}".format(actual_row)
