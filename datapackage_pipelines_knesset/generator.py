from datapackage_pipelines.generators import GeneratorBase, steps
from copy import deepcopy
import logging


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
            pipeline_id, pipeline = cls.get_knesset_dataservice_pipeline(pipeline_id, pipeline)
        yield pipeline_id, pipeline

    @classmethod
    def get_knesset_dataservice_pipeline(cls, pipeline_id, pipeline):
        return pipeline_id, {'description': '<p>'
                                                'runs daily, loads data from the latest version of the '
                                                '<a href="https://github.com/hasadna/knesset-data/blob/master/docs/dataservice/README.md">'
                                                    'Knesset dataservice odata interface'
                                                '</a>'
                                           '</p> ',
                            'schedule': {'crontab': '10 0 * * *'},
                            'pipeline': steps(('..datapackage_pipelines_knesset.dataservice.processors.add_dataservice_collection_resource',
                                               pipeline["dataservice-parameters"]),
                                              ('..datapackage_pipelines_knesset.common.processors.throttle',
                                               {'rows-per-page': 50}),
                                              ('dump.to_path',
                                               {'out-path': '../data/{}/{}'.format(pipeline['schemas-bucket'],
                                                                                   pipeline_id)}))}
