from datapackage_pipelines.generators import GeneratorBase
from copy import deepcopy

class Generator(GeneratorBase):

    @classmethod
    def get_schema(cls):
        return {"$schema": "http://json-schema.org/draft-04/schema#",
                "type": "object",
                "properties": {}}

    @classmethod
    def generate_pipeline(cls, source):
        for pipeline_id, pipeline in source.items():
            if pipeline_id and pipeline:
                yield from cls.filter_pipeline(pipeline_id, deepcopy(pipeline))

    @classmethod
    def filter_pipeline(cls, pipeline_id, pipeline):
        if pipeline.get("pipeline-type") == "knesset dataservice":
            yield from cls.get_knesset_dataservice_pipeline(pipeline_id, pipeline)
        else:
            yield pipeline_id, pipeline

    @classmethod
    def get_knesset_dataservice_pipeline(cls, pipeline_id, pipeline):
        pipeline_schedule = {"crontab": "10 0 * * *"}
        pipeline_steps = [{"run": "load_dataservice_resource",
                           "parameters": pipeline["dataservice-parameters"]}]
        pipeline = {'pipeline': pipeline_steps}
        yield pipeline_id, {}
        pass