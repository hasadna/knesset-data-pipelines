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
        elif pipeline.get("pipeline-type") == "all package":
            yield from cls.get_all_package_pipeline(pipeline_id, pipeline)
        elif pipeline.get("pipeline-type") == "db dump":
            yield from cls.get_db_dump_pipeline(pipeline_id, pipeline)
        else:
            pipeline["pipeline"] = steps(*[(step["run"], step.get("parameters", {})) for step in pipeline["pipeline"]])
            yield pipeline_id, pipeline

    @classmethod
    def get_knesset_dataservice_pipeline(cls, pipeline_id, pipeline):
        if os.environ.get("DATASERVICE_LOAD_FROM_URL"):
            pipeline_steps = [('load_resource',
                               {"url": "http://storage.googleapis.com/knesset-data-pipelines/data/{}/{}/datapackage.json".format(pipeline['schemas-bucket'], pipeline_id),
                                "resource": pipeline_id}),]
        else:
            pipeline_steps = [('..datapackage_pipelines_knesset.dataservice.processors.add_dataservice_collection_resource',
                               pipeline["dataservice-parameters"]),
                              ('..datapackage_pipelines_knesset.common.processors.throttle',
                               {'rows-per-page': 50}),]
        pipeline_steps += [('dump.to_path',
                            {'out-path': '../data/{}/{}'.format(pipeline['schemas-bucket'], pipeline_id)})]
        yield pipeline_id, {'pipeline': steps(*pipeline_steps)}

    @classmethod
    def get_all_package_pipeline(cls, pipeline_id, pipeline):
        pipeline_steps = []
        for resource in pipeline["resources"]:
            pipeline_steps += [("load_resource", {"url": pipeline["base-url"] + resource["name"] + "/datapackage.json",
                                                  "resource": resource.get("resource", resource["name"])})]
            if resource.get("resource"):
                pipeline_steps += [("..rename_resource",
                                    {"src": resource["resource"], "dst": resource["name"]})]
        pipeline_steps += [('dump.to_path',
                            {'out-path': pipeline["out-path"]})]
        pipeline_steps += [('dump.to_zip',
                            {'out-file': pipeline["out-path"] + "/datapackage.zip"})]
        yield pipeline_id, {'pipeline': steps(*pipeline_steps)}

    @classmethod
    def get_db_dump_pipeline(cls, pipeline_id, pipeline):
        pipeline_steps = [
            ("load_resource", {
                "url": "https://storage.googleapis.com/knesset-data-pipelines/data/votes/votes/datapackage.json",
                "resource": "votes"
            }),
            ("load_resource", {
                "url": "https://storage.googleapis.com/knesset-data-pipelines/data/committees/kns_committee/datapackage.json",
                "resource": "kns_committee"
            }),
            ("load_resource", {
                "url": "https://storage.googleapis.com/knesset-data-pipelines/data/people/members/joined-mks/datapackage.json",
                "resource": "mk_individual"
            }),
            ("load_resource", {
                "url": "https://storage.googleapis.com/knesset-data-pipelines/data/people/committees/committee-meeting-attendees-mks-stats/datapackage.json",
                "resource": "mk_attendance"
            }),
            # remove positions and altnames because oknesset DB doesn't support jsonb
            # TODO: normalize altnames and positions to mk_individual or other tables
            ("set_types", {"resources": "mk_individual", "types": {"positions": None, "altnames": None}}),
            ("dump.to_sql", {"engine": "env://DPP_DB_ENGINE", "tables": {
                "next_votes": {"resource-name": "votes", "mode": "rewrite"},
                "next_kns_committee": {"resource-name": "kns_committee", "mode": "rewrite"},
                "next_mk_individual": {"resource-name": "mk_individual", "mode": "rewrite"},
                "next_mk_attendance": {"resource-name": "mk_attendance", "mode": "rewrite"},
            }})
        ]
        yield pipeline_id, {'pipeline': steps(*pipeline_steps)}
