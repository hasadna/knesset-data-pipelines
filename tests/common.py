import os, yaml
from copy import deepcopy
from jsontableschema.field import Field


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
        field.pop("source")
        field["name"] = field_name
        if field["type"] == "datetime":
            field["format"] = "fmt:%Y-%m-%d %H:%M:%S.%f"
        elif field["type"] == "date":
            field["format"] = "fmt:%Y-%m-%d"
        schema_fields.append(field)
    return parameters, {"fields": schema_fields,
                       "primaryKey": "id"}

def assert_conforms_to_schema(schema, doc):
    assert isinstance(doc, dict), "invalid doc: {}".format(doc)
    for field in schema["fields"]:
        value = doc[field["name"]]
        assert Field(field).test_value(value), "value {} does not conform to schema {}".format(value, field)
