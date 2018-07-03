from datapackage_pipelines.wrapper import ingest, spew
from datapackage_pipelines_knesset.committees.dist.template_functions import get_jinja_env
import logging, os, subprocess
from datetime import datetime
from datapackage_pipelines_knesset.committees.dist.template_functions import build_template, get_context
from datapackage_pipelines_knesset.committees.dist.constants import MEMBER_URL, POSITION_URL, MINISTRY_URL, FACTION_URL

def main():
    parameters, datapackage, resources = ingest()

    jinja_env = get_jinja_env()
    jinja_env.filters['datetime'] = dateTimeFormat

    members = {}
    committees = {}

    for descriptor, resource in zip(datapackage["resources"], resources):

        if descriptor["name"] == "mk_individual":
            for member in resource:

                mkId = member["mk_individual_id"]

                members[mkId] = {
                    "mk_individual_id": mkId,
                    "first_name": member["mk_individual_first_name"],
                    "last_name": member["mk_individual_name"],
                    "photo": member["mk_individual_photo"],
                    "icon": getIcon(member["mk_individual_photo"]),
                    "position_url": POSITION_URL,
                    "ministry_url": MINISTRY_URL,
                    "faction_url": FACTION_URL,
                    "source_member_schema": descriptor["schema"],
                    "url": MEMBER_URL.format(member_id=mkId),
                    "source_member_row": member}

                member_factions = []
                member_committees = []
                member_ministries = []

                for position in sorted(member["positions"], key=dateKey, reverse=True):
                    if "KnessetNum" not in position:
                        continue

                    item = {
                        "knesset_num": position["KnessetNum"],
                        "position_id": position["position_id"],
                        "position_name": position["position"],
                        "start_date": position["start_date"]
                    }

                    if "finish_date" in position:
                        item["finish_date"] = position["finish_date"]

                    if "FactionID" in position:
                        item["faction_id"] = position["FactionID"]
                        item["faction_name"] = position["FactionName"]
                        member_factions.append(item)

                    if "CommitteeID" in position:
                        item["committee_id"] = position["CommitteeID"]
                        item["committee_name"] = position["CommitteeName"]
                        member_committees.append(item)

                    if "GovMinistryID" in position:
                        item["ministry_id"] = position["GovMinistryID"]
                        item["ministry_name"] = position["GovMinistryName"]
                        member_ministries.append(item)

                members[mkId]["factions"] = member_factions
                members[mkId]["committees"] = member_committees
                members[mkId]["ministries"] = member_ministries

        elif descriptor["name"] == "kns_committeesession":
            for committeesession in resource:
                # aggregate statistics only if there is a protocol and mks
                if committeesession["text_parsed_filename"]:
                    knessetNum = committeesession["KnessetNum"]

                    if knessetNum not in committees:
                        committees[knessetNum] = 0
                    committees[knessetNum] += 1

                    for mkId in committeesession["attended_mk_individual_ids"]:
                        if mkId not in members:
                            continue

                        positions = members[mkId]["factions"] + members[mkId]["committees"] + members[mkId][
                            "ministries"]
                        if isMember(positions, committeesession["StartDate"]):
                            if "counts" not in members[mkId]:
                                members[mkId]["counts"] = {}
                            if knessetNum not in members[mkId]["counts"]:
                                members[mkId]["counts"][knessetNum] = 0

                            members[mkId]["counts"][knessetNum] += 1

    for member in members.values():
        if not os.environ.get('DISABLE_MEMBER_PERCENTS') and "counts" in member:
            for knesset, count in member["counts"].items():
                percent = count / committees[knesset] * 100

                if "percents" not in member:
                    member["percents"] = {}
                member["percents"][knesset] = int(percent)

        build_template(jinja_env, "member_detail.html",
                       get_context(member),
                       MEMBER_URL.format(member_id=member["mk_individual_id"]))

    if os.environ.get("SKIP_STATIC") != "1":
        subprocess.check_call(["mkdir", "-p", "../../data/committees/dist/dist"])
        subprocess.check_call(["cp", "-rf", "static", "../../data/committees/dist/dist/"])

    spew(dict(datapackage, resources=[]), [], {})

def getIcon(photo):
    return photo[:-4] + "-s" + photo[-4:] if photo else None

def isMember(positions, startDate):

    if not startDate:
        return False

    for position in positions:
        if position["position_id"] == 54 and "start_date" in position:
            positionStartDate = datetime.strptime(position["start_date"], "%Y-%m-%d %H:%M:%S")

            if "finish_date" in position:
                positionEndDate = datetime.strptime(position["finish_date"], "%Y-%m-%d %H:%M:%S")
            else:
                positionEndDate = datetime.now()

            if positionStartDate <= startDate and positionEndDate >= startDate:
                return True

    return False

def dateKey(position):
    key = "1970-01-01 00:00:00"

    if "finish_date" in position:
        key = position["finish_date"]
    elif "start_date" in position:
        key = position["start_date"]

    return datetime.strptime(key, "%Y-%m-%d %H:%M:%S")


def dateTimeFormat(value, format="%Y-%m-%d %H:%M:%S"):
    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S").strftime(format)

if __name__ == "__main__":
    main()
