from datapackage_pipelines.wrapper import ingest, spew
import logging
from datapackage_pipelines_knesset.committees.dist.template_functions import build_template, get_jinja_env, get_context
from datapackage_pipelines_knesset.committees.dist.speech_parts import (get_speech_part_body,
                                                                        get_speech_parts,
                                                                        update_speech_parts_hash)
from datapackage_pipelines_knesset.committees.dist.constants import COMMITTEE_DETAIL_URL, COMMITTEE_LIST_KNESSET_URL, MEMBER_URL
from datapackage_pipelines_knesset.committees.dist.committees_common import get_meeting_path
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


def get_meeting_context(meeting):
    try:
        speech_parts_list = list(get_speech_parts(meeting))
    except Exception as e:
        logging.exception("failed to get speech parts for meeting {}".format(meeting["CommitteeSessionID"]))
        speech_parts_list = []
    attended_mks = [mk_individuals[mk_id] for mk_id in meeting["attended_mk_individual_ids"]]
    committee = kns_committees[meeting["CommitteeID"]]
    context = get_context({"topics": meeting["topics"],
                           "title": "ישיבה של {} בתאריך {}".format(committee["Name"],
                                                                  meeting["StartDate"].strftime("%d/%m/%Y")),
                           "committee_name": committee["Name"],
                           "meeting_datestring": meeting["StartDate"].strftime("%d/%m/%Y"),
                           "committee_url": COMMITTEE_DETAIL_URL.format(committee_id=committee["CommitteeID"]),
                           "member_url": MEMBER_URL,
                           "knesset_num": committee["KnessetNum"],
                           "committeelist_knesset_url": COMMITTEE_LIST_KNESSET_URL.format(num=committee["KnessetNum"]),
                           "meeting_id": meeting["CommitteeSessionID"],
                           "speech_parts": speech_parts_list,
                           "speech_part_body": get_speech_part_body,
                           "source_meeting_schema": meetings_descriptor["schema"],
                           "source_meeting_row": meeting,
                           "source_committee_schema": kns_committee_descriptor["schema"],
                           "source_committee_row": committee,
                           "attended_mks": attended_mks,
                           })
    meeting_stats[meeting["CommitteeSessionID"]] = {"num_speech_parts": len(speech_parts_list)}
    return context


for meeting in next(resources):
    m = HASH_FILES_OBJECT.copy()
    update_meeting_hash(meeting, m.update)
    build_template(jinja_env,
                   "committeemeeting_detail.html",
                   lambda: get_meeting_context(meeting),
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
