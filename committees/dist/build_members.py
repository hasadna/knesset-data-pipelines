from datapackage_pipelines.wrapper import ingest, spew
from datapackage_pipelines_knesset.committees.dist.template_functions import get_jinja_env
import logging, os, subprocess
from datetime import datetime
from datetime import time
from datapackage_pipelines_knesset.committees.dist.template_functions import build_template, get_context
from datapackage_pipelines_knesset.committees.dist.constants import MEMBER_URL, POSITION_URL, MINISTRY_URL, FACTION_URL


def main():
    parameters, datapackage, resources = ingest()

    jinja_env = get_jinja_env()

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
        elif descriptor['name'] == 'mk_individual_committees':
            for position in resource:
                committees_positions = members[position['mk_individual_id']].setdefault('committees', [])
                committee_chairperson_positions = members[position['mk_individual_id']].setdefault('committee_chairperson', [])
                if position['position_id'] == 41:
                    committee_chairperson_positions.append({'knesset_num': position['knesset'],
                                                            'committee_id': position['committee_id'],
                                                            'committee_name': position['committee_name'],
                                                            'start_date': position['start_date'],
                                                            'finish_date': position['finish_date']})
                else:
                    committees_positions.append({'knesset_num': position['knesset'],
                                                 'committee_id': position['committee_id'],
                                                 'committee_name': position['committee_name'],
                                                 'position_id': position['position_id'],
                                                 'position_name': position['position_name'],
                                                 'start_date': position['start_date'],
                                                 'finish_date': position['finish_date']})
        elif descriptor['name'] == 'mk_individual_faction_chairpersons':
            for position in resource:
                faction_chairpersons_positions = members[position['mk_individual_id']].setdefault('faction_chairperson', [])
                faction_chairpersons_positions.append({'knesset_num': position['knesset'],
                                                       'faction_id': position['faction_id'],
                                                       'faction_name': position['faction_name'],
                                                       'start_date': position['start_date'],
                                                       'finish_date': position['finish_date']})
        elif descriptor['name'] == 'mk_individual_factions':
            for position in resource:
                faction_positions = members[position['mk_individual_id']].setdefault('factions', [])
                faction_positions.append({'knesset_num': position['knesset'],
                                          'faction_id': position['faction_id'],
                                          'faction_name': position['faction_name'],
                                          'start_date': position['start_date'],
                                          'finish_date': position['finish_date']})
        elif descriptor['name'] == 'mk_individual_govministries':
            for position in resource:
                ministry_positions = members[position['mk_individual_id']].setdefault('govministries', [])
                ministry_positions.append({'knesset_num': position['knesset'],
                                           'govministry_id': position['govministry_id'],
                                           'govministry_name': position['govministry_name'],
                                           'position_id': position['position_id'],
                                           'position_name': position['position_name'],
                                           'start_date': position['start_date'],
                                           'finish_date': position['finish_date']})
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
                        if isMember(members[mkId], committeesession["StartDate"]):
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
                       get_member_context(member),
                       MEMBER_URL.format(member_id=member["mk_individual_id"]))

    if os.environ.get("SKIP_STATIC") != "1":
        subprocess.check_call(["mkdir", "-p", "../../data/committees/dist/dist"])
        subprocess.check_call(["cp", "-rf", "static", "../../data/committees/dist/dist/"])

    spew(dict(datapackage, resources=[]), [], {})

def getIcon(photo):
    return photo[:-4] + "-s" + photo[-4:] if photo else None


def isMember(member, startDate):
    if not startDate:
        return False
    for position in member['factions']:
        positionStartDate = datetime.combine(position["start_date"], time())
        if position.get("finish_date"):
            positionEndDate = datetime.combine(position["finish_date"], time())
        else:
            positionEndDate = datetime.now()
        if positionStartDate <= startDate <= positionEndDate:
            return True
    return False


def get_member_context(member):
    for position_attr in ('committees', 'committee_chairperson',
                          'faction_chairperson', 'factions', 'govministries'):
        for position in member.setdefault(position_attr, []):
            position['start_date'] = position['start_date'].strftime('%d/%m/%Y')
            if position['finish_date']:
                position['finish_date'] = position['finish_date'].strftime('%d/%m/%Y')
    return get_context(member)


if __name__ == "__main__":
    main()
