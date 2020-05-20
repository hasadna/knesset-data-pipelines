import logging
from datapackage_pipelines_knesset.committees.dist.constants import COMMITTEE_DETAIL_URL, COMMITTEE_LIST_KNESSET_URL, MEMBER_URL
from datapackage_pipelines_knesset.committees.dist.template_functions import get_context
from datapackage_pipelines_knesset.committees.dist.speech_parts import (get_speech_part_body,
                                                                        get_speech_parts)
from datapackage import Package


# meetings which should be hidden for various reasons
# data is still available, just the meeting html is not displayed
HIDE_MEETING_IDS = [2072396, 568058, 543222]


def get_meeting_context_data():
    package = Package('data/committees/dist/build_meetings/datapackage.json')
    return dict(
        mk_individuals={int(mk['mk_individual_id']): mk for mk
                        in package.get_resource('mk_individual').iter(keyed=True)},
        kns_committees = {int(cmt['CommitteeID']): cmt for cmt
                        in package.get_resource('kns_committee').iter(keyed=True)},
        meetings_descriptor = package.get_resource('kns_committeesession').descriptor,
        kns_committee_descriptor = package.get_resource('kns_committee').descriptor,
        meeting_stats = {}
    )


def get_meeting_context(meeting, context_data, use_data=True):
    context = get_context({"topics": meeting["topics"],
                           "note": meeting.get("Note"),
                           "meeting_datestring": meeting["StartDate"].strftime("%d/%m/%Y"),
                           "member_url": MEMBER_URL,
                           "meeting_id": meeting["CommitteeSessionID"],
                           "source_meeting_schema": context_data['meetings_descriptor']["schema"],
                           "source_meeting_row": meeting,
                           "source_committee_schema": context_data['kns_committee_descriptor']["schema"],})
    if meeting['CommitteeSessionID'] in HIDE_MEETING_IDS:
        context['hidden_meeting'] = True
        speech_parts_list = []
    else:
        try:
            speech_parts_list = list(get_speech_parts(meeting, use_data=use_data))
        except Exception as e:
            logging.exception("failed to get speech parts for meeting {}".format(meeting["CommitteeSessionID"]))
            speech_parts_list = []
        context.update(speech_parts=speech_parts_list,
                       speech_part_body=get_speech_part_body)

    attended_mks = [context_data['mk_individuals'][mk_id] for mk_id in meeting["attended_mk_individual_ids"]]
    context.update(attended_mks=attended_mks)

    committee = context_data['kns_committees'][meeting["CommitteeID"]]
    context.update(title="ישיבה של {} בתאריך {}".format(committee["Name"],
                                                        meeting["StartDate"].strftime("%d/%m/%Y")),
                   committee_name=committee["Name"],
                   committee_url=COMMITTEE_DETAIL_URL.format(committee_id=committee["CommitteeID"]),
                   knesset_num=committee["KnessetNum"],
                   committeelist_knesset_url=COMMITTEE_LIST_KNESSET_URL.format(num=committee["KnessetNum"]),
                   source_committee_row=committee)

    context_data['meeting_stats'][meeting["CommitteeSessionID"]] = {"num_speech_parts": len(speech_parts_list)}
    return context
