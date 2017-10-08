from datapackage_pipelines_knesset.common.processors.dump_to_sql import Processor as DumpToSqlProcessor
from .common import get_pipeline_processor_parameters, get_pipeline_spec_pipeline_names
from .mocks.dataservice import MockAddDataserviceCollectionResourceProcessor
import os, json
from datapackage_pipelines_knesset.common import object_storage


class MockDumpToSqlProcessor(DumpToSqlProcessor):

    def save_schemas(self):
        self._tablename = self._parameters["table"]
        save_schema = os.path.join(os.path.dirname(__file__), "mocks", "table_schema_{table_name}.{ext}")
        self._save_schema_json(save_schema)
        self._save_schema_html(save_schema)


def assert_dump_to_sql_table_schema(pipeline_spec_name, pipeline_name):
    datapackage = {"name": "_", "resources": []}
    processor_matcher = lambda step: step["run"] == "..datapackage_pipelines_knesset.dataservice.processors.add_dataservice_collection_resource"
    parameters = get_pipeline_processor_parameters(pipeline_spec_name, pipeline_name, processor_matcher)
    processor = MockAddDataserviceCollectionResourceProcessor(parameters, datapackage, [])
    datapackage, resources = processor.spew()
    processor_matcher = lambda step: step["run"] == "..datapackage_pipelines_knesset.common.processors.dump_to_sql"
    parameters = get_pipeline_processor_parameters(pipeline_spec_name, pipeline_name, processor_matcher)
    processor = MockDumpToSqlProcessor(parameters, datapackage, [])
    datapackage, resources, stats = processor.spew()
    for resource in resources:
        pass
    filenames = {ext: os.path.join(os.path.dirname(__file__), "mocks",
                                  "table_schema_{}.{}".format(pipeline_name, ext))
                 for ext in ["html", "json"]}
    for filename in filenames.values():
        if os.path.exists(filename):
            os.unlink(filename)
    processor.save_schemas()
    for ext, filename in filenames.items():
        if ext == "json":
            assert "fields" in fs.json_load(filename)
        else:
            assert f.read(6) == "<html>"

def test_dump_to_sql_table_schemas():
    for pipeline_spec_name in ["bills", "committees", "laws"]:
        processor_matcher = lambda step: step["run"] == "..datapackage_pipelines_knesset.dataservice.processors.add_dataservice_collection_resource"
        for pipeline_name in get_pipeline_spec_pipeline_names(pipeline_spec_name, processor_matcher):
            assert_dump_to_sql_table_schema(pipeline_spec_name, pipeline_name)
