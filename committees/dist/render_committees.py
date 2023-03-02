from datapackage_pipelines.wrapper import ingest, spew
from datapackage_pipelines_knesset.committees.dist.template_functions import build_template, get_jinja_env, get_context
from datapackage_pipelines_knesset.committees.dist.constants import COMMITTEE_DETAIL_URL, COMMITTEE_LIST_KNESSET_URL, MEMBER_URL, COMMITTEES_INDEX_URL
from datapackage_pipelines_knesset.committees.dist.committees_common import get_committee_name, get_meeting_path, get_meeting_topics, is_future_meeting, has_protocol


parameters, datapackage, resources, stats = ingest() + ({},)


kns_committee_descriptor = datapackage["resources"][0]
stats["all committees"] = 0
kns_committees = {}
for kns_committee in next(resources):
    kns_committees[int(kns_committee["CommitteeID"])] = kns_committee
    kns_committee['meetings'] = []
    stats["all committees"] += 1


mk_individual_descriptor = datapackage["resources"][1]
stats.update(**{"all mks": 0, "all chairpersons": 0, "all members": 0, "all replacements": 0, "all watchers": 0,
                "all others": 0,})
for mk in next(resources):
    mk_id = mk["mk_individual_id"]
    for position in mk["positions"]:
        if position.get("CommitteeID") and position["CommitteeID"] in kns_committees:
            kns_committee = kns_committees[position["CommitteeID"]]
            kns_committee_mks = kns_committee.setdefault("mks", {})
            if position["position_id"] == 41:
                # chairperson role overrides other roles
                kns_committee_mks[mk_id] = dict(mk, committee_position="chairperson")
                stats["all chairpersons"] += 1
            elif mk_id not in kns_committee_mks:
                if position["position_id"] in [42, 66]:
                    kns_committee_mks[mk_id] = dict(mk, committee_position="member")
                    stats["all members"] += 1
                elif position["position_id"] == 67:
                    kns_committee_mks[mk_id] = dict(mk, committee_position="replacement")
                    stats["all replacements"] += 1
                elif position["position_id"] == 663:
                    kns_committee_mks[mk_id] = dict(mk, committee_position="watcher")
                    stats["all watchers"] += 1
                else:
                    kns_committee_mks[mk_id] = dict(mk, committee_position="other")
                    stats["all others"] += 1
    stats["all mks"] += 1


meetings_descriptor = datapackage["resources"][2]
stats["all meetings"] = 0
all_meetings = {}
for meeting in next(resources):
    committee = kns_committees[meeting["CommitteeID"]]
    committee.setdefault("meetings", []).append(meeting)
    all_meetings[meeting["CommitteeSessionID"]] = meeting
    meeting["num_speech_parts"] = 0
    stats["all meetings"] += 1


meeting_stats_descriptor = datapackage["resources"][3]
stats["all meeting stats"] = 0
for meeting_stats in next(resources):
    if meeting_stats["CommitteeSessionID"] in all_meetings:
        all_meetings[meeting_stats["CommitteeSessionID"]]["num_speech_parts"] = meeting_stats["num_speech_parts"]
        stats["all meeting stats"] += 1


def get_committee_meeting_contexts(committee):
    for meeting in sorted(committee["meetings"], key=lambda m:m["StartDate"], reverse=True):
        yield {"date_string": meeting["StartDate"].strftime("%d/%m/%Y"),
               "url": get_meeting_path(meeting),
               "title": get_meeting_topics(meeting),
               "is_future_meeting": is_future_meeting(meeting),
               "has_protocol": has_protocol(meeting)}


def get_committee_context(committee):
    return get_context({"source_committee_row": committee,
                        "source_committee_schema": kns_committee_descriptor["schema"],
                        "name": get_committee_name(committee),
                        "meetings": get_committee_meeting_contexts(committee),
                        "knesset_num": committee["KnessetNum"],
                        "committeelist_knesset_url": COMMITTEE_LIST_KNESSET_URL.format(num=committee["KnessetNum"]),
                        "member_url": MEMBER_URL,
                        "mks": sorted(committee.get("mks", {}).values(), key=lambda mk: mk["mk_individual_name"]),
                        })


def get_committee_list_context(committees, knesset_num):
    def committees_generator():
        for committee in committees:
            yield {"id": committee["CommitteeID"],
                   "name": get_committee_name(committee),
                   "url": COMMITTEE_DETAIL_URL.format(committee_id=committee["CommitteeID"]),
                   "num_meetings": len(committee["meetings"]),
                   }
    return get_context({"committees": sorted(committees_generator(), key=lambda c: c["name"]),
                        "knesset_num": knesset_num})


def get_committee_index_context(knesset_num_committees):
    def knesset_nums():
        for knesset_num, kns_committees in knesset_num_committees.items():
            num_meetings = 0
            for kns_committee in kns_committees:
                num_meetings += len(kns_committee.get("meetings", []))
            yield {"num": knesset_num,
                   "url": COMMITTEE_LIST_KNESSET_URL.format(num=knesset_num),
                   "num_committees": len(kns_committees),
                   "num_meetings": num_meetings}
    return get_context({"knesset_nums": sorted(knesset_nums(), key=lambda k: k["num"], reverse=True)})


def get_homepage_context():
    return get_context({})


jinja_env = get_jinja_env()


stats["built_committees"] = 0
stats["failed_committees"] = 0
knesset_num_committees = {}
for kns_committee in kns_committees.values():
    knesset_num_committees.setdefault(kns_committee["KnessetNum"], []).append(kns_committee)
    build_template(jinja_env,
                   "committee_detail.html",
                   get_committee_context(kns_committee),
                   COMMITTEE_DETAIL_URL.format(committee_id=kns_committee["CommitteeID"]))
    stats["built_committees"] += 1


stats["built_knesset_nums"] = 0
stats["failed_knesset_nums"] = 0
for knesset_num, kns_committees in knesset_num_committees.items():
    build_template(jinja_env,
                   "committee_list.html",
                   get_committee_list_context(kns_committees, knesset_num),
                   COMMITTEE_LIST_KNESSET_URL.format(num=knesset_num))
    stats["built_knesset_nums"] += 1


build_template(jinja_env,
               "committees_index.html",
               get_committee_index_context(knesset_num_committees),
               COMMITTEES_INDEX_URL)
stats["built index"] = 1


spew(dict(datapackage, resources=[]), [], stats)
