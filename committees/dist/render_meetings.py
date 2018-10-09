from datapackage_pipelines.wrapper import ingest, spew
from datapackage_pipelines_knesset.committees.dist.template_functions import build_template, get_jinja_env
from datapackage_pipelines_knesset.committees.dist.speech_parts import (update_speech_parts_hash)
from datapackage_pipelines_knesset.committees.dist.committees_common import get_meeting_path
from datapackage_pipelines_knesset.committees.dist.meeting_context import get_meeting_context
from datapackage_pipelines.utilities.resources import PROP_STREAMING
import hashlib, fileinput


HASH_FILES=('../../datapackage_pipelines_knesset/committees/dist/template_functions.py',
            '../../datapackage_pipelines_knesset/committees/dist/speech_parts.py',
            '../../datapackage_pipelines_knesset/committees/dist/constants.py',
            '../../datapackage_pipelines_knesset/committees/dist/committees_common.py',
            'templates/committeemeeting_detail.html',
            'templates/site_base.html',
            'render_meetings.py',)


HASH_FILES_OBJECT = hashlib.md5()
with fileinput.input(HASH_FILES, mode='rb') as f:
    for line in f:
        HASH_FILES_OBJECT.update(line)


parameters, datapackage, resources = ingest()
stats = {
    "kns_committees": 0,
    "mk_individuals": 0,
    "meetings": 0,
    "failed meetings": 0
}
meeting_stats = {}


kns_committee_descriptor = datapackage["resources"][0]
kns_committees = {}
for kns_committee in next(resources):
    kns_committees[int(kns_committee["CommitteeID"])] = kns_committee
    stats["kns_committees"] += 1


mk_individual_descriptor = datapackage["resources"][1]
mk_individuals = {}
for mk_individual in next(resources):
    mk_individuals[int(mk_individual["mk_individual_id"])] = mk_individual
    stats["mk_individuals"] += 1


meetings_descriptor = datapackage["resources"][2]


jinja_env = get_jinja_env()


def update_meeting_hash(meeting, update_hash_callback):
    update_speech_parts_hash(meeting, update_hash_callback)
    update_hash_callback(''.join((str(mk_individuals[mk_id])
                                  for mk_id
                                  in meeting["attended_mk_individual_ids"])).encode())
    update_hash_callback(str(kns_committees[meeting["CommitteeID"]]).encode())
    update_hash_callback(str(meeting).encode())


for meeting in next(resources):
    m = HASH_FILES_OBJECT.copy()
    update_meeting_hash(meeting, m.update)
    build_template(jinja_env,
                   "committeemeeting_detail.html",
                   lambda: get_meeting_context(meeting, dict(mk_individuals=mk_individuals,
                                                             kns_committees=kns_committees,
                                                             meetings_descriptor=meetings_descriptor,
                                                             kns_committee_descriptor=kns_committee_descriptor,
                                                             meeting_stats=meeting_stats)),
                   get_meeting_path(meeting),
                   with_hash=m.hexdigest())
    stats["meetings"] += 1


def get_stats_resource():
    for meeting_id, stats in meeting_stats.items():
        stats["CommitteeSessionID"] = meeting_id
        yield stats


spew(dict(datapackage, resources=[{PROP_STREAMING: True,
                                   "name": "meetings_stats",
                                   "path": "meetings_stats.csv",
                                   "schema": {"fields": [{"name": "CommitteeSessionID", "type": "integer"},
                                                         {"name": "num_speech_parts", "type": "integer"},
                                                         {'name': 'hash', 'type': 'string'}]}}]),
     [get_stats_resource()], stats)
