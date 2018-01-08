from datapackage_pipelines.generators import GeneratorBase, steps
from copy import deepcopy
import logging, os, requests, codecs


__escape_decoder = codecs.getdecoder('unicode_escape')


def decode_escaped(escaped):
    return __escape_decoder(escaped)[0]


def parse_dotenv(dotenv):
    for line in dotenv.splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        k, v = line.split('=', 1)
        k, v = k.strip(), v.strip().encode('unicode-escape').decode('ascii')
        if len(v) > 0:
            quoted = v[0] == v[-1] in ['"', "'"]
            if quoted:
                v = decode_escaped(v[1:-1])
        yield k, v


class Generator(GeneratorBase):
    latest_sync_url = None

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
            pipeline["pipeline"] = steps(*[(step["run"], step.get("parameters", {})) for step in pipeline["pipeline"]])
            yield pipeline_id, pipeline

    @classmethod
    def get_knesset_dataservice_pipeline(cls, pipeline_id, pipeline):
        if os.environ.get("DATASERVICE_LOAD_FROM_URL"):
            pipeline_steps = [('load_resource',
                               {"url": "http://storage.googleapis.com/knesset-data-pipelines/{}/{}/datapackage.json".format(pipeline['schemas-bucket'], pipeline_id),
                                "resource": pipeline_id}),]
        else:
            pipeline_steps = [('..datapackage_pipelines_knesset.dataservice.processors.add_dataservice_collection_resource',
                               pipeline["dataservice-parameters"]),
                              ('..datapackage_pipelines_knesset.common.processors.throttle',
                               {'rows-per-page': 50}),]
        pipeline_steps += [('dump.to_path',
                            {'out-path': '../data/{}/{}'.format(pipeline['schemas-bucket'], pipeline_id)})]
        yield pipeline_id, {'pipeline': steps(*pipeline_steps)}
