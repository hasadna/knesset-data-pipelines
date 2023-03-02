# common committee functions - imported from other files
from datapackage_pipelines_knesset.committees.dist.constants import MEETING_URL
import datetime


def get_meeting_topics(meeting):
    return ", ".join(meeting["topics"]) if meeting["topics"] else meeting.get("Note", "")


def get_meeting_path(meeting):
    return MEETING_URL.format(str(meeting["CommitteeSessionID"])[0],
                              str(meeting["CommitteeSessionID"])[1],
                              str(meeting["CommitteeSessionID"]))


def get_committee_name(committee):
    return committee["CategoryDesc"] if committee["CategoryDesc"] else committee["Name"]


def is_future_meeting(meeting):
    return meeting["StartDate"] > datetime.datetime.now()


def has_protocol(meeting):
    return meeting["num_speech_parts"] > 1 or (meeting.get('parts_filesize') and meeting['parts_filesize'] > 20)
