from datapackage_pipelines.wrapper import ingest, spew
from datapackage_pipelines.utilities.resources import PROP_STREAMING
from copy import deepcopy
import logging, datetime, csv


parameters, datapackage, resources = ingest()


errors = []
mk_attendance = []


# full mks data, with positions
mk_individuals = {}
for mk_individual in next(resources):
    mk_individuals[mk_individual["mk_individual_id"]] = mk_individual


# document committee session with reated attended mk ids
for meeting in next(resources):
    committee_name = meeting['committee_name']
    meeting_aggs = {"knesset_num": meeting["KnessetNum"],
                    "committee_id": meeting["CommitteeID"],
                    "committee_name": committee_name,
                    "meeting_start_date": meeting["StartDate"],
                    "meeting_topics": ", ".join(meeting["topics"]) if meeting["topics"] else None, }
    for mk_individual_id in meeting["attended_mk_individual_ids"]:
        mk_individual = mk_individuals[mk_individual_id]
        mk_name = None
        # mk_individual_id,mk_status_id,mk_individual_name,mk_individual_name_eng,mk_individual_first_name,mk_individual_first_name_eng,mk_individual_email,mk_individual_photo
        for name_pair in ((mk_individual["mk_individual_first_name"], mk_individual["mk_individual_name"]),
                          (mk_individual["FirstName"], mk_individual["LastName"]),):
            if all(name_pair):
                mk_name = "{} {}".format(*name_pair)
                break
        if mk_name:
            try:
                mk_id = mk_individual["mk_individual_id"]
                mk_aggs = deepcopy(meeting_aggs)
                mk_aggs.update(mk_name=mk_name, mk_id=mk_id)
                mk_faction_id = None
                mk_faction_name = None
                mk_membership_committee_names = set()
                for position in mk_individual["positions"]:
                    mk_position_start_date = datetime.datetime.strptime(position["start_date"], "%Y-%m-%d %H:%M:%S")
                    if position.get("finish_date"):
                        mk_position_finish_date = datetime.datetime.strptime(position["finish_date"], "%Y-%m-%d %H:%M:%S")
                    else:
                        mk_position_finish_date = datetime.datetime.now()
                    assert meeting["StartDate"], "meeting must have a start date"
                    if not meeting["FinishDate"]:
                        meeting["FinishDate"] = datetime.datetime.now()
                    if meeting["StartDate"] >= mk_position_start_date and meeting["FinishDate"] <= mk_position_finish_date:
                        if position.get("FactionID") and position.get("FactionName"):
                            if mk_faction_id is None or mk_faction_id == position["FactionID"]:
                                mk_faction_id = position["FactionID"]
                                mk_faction_name = position["FactionName"]
                            else:
                                logging.warning("Invalid faction for knesset num {} mk_individual id {} faction name {}"
                                                .format(meeting["KnessetNum"], mk_id, position.get("FactionName")))
                        elif position.get("CommitteeID") and position.get("CommitteeName"):
                            mk_membership_committee_names.add(position["CommitteeName"])
                mk_aggs.update(mk_membership_committee_names=", ".join(mk_membership_committee_names),
                               mk_faction_id=mk_faction_id, mk_faction_name=mk_faction_name)
                mk_attendance.append(mk_aggs)
            except Exception:
                logging.exception("Failed to process mk_individual name {}".format(mk_name))
                raise
        else:
            raise Exception("Failed to find mk_individual name for mk_individual id {}".format(mk_individual["mk_individual_id"]))

meeting_aggs_fields = [{"name": "knesset_num", "type": "integer"},
                       {"name": "committee_id", "type": "integer"},
                       {"name": "committee_name", "type": "string"},
                       {"name": "meeting_start_date", "type": "datetime"},
                       {"name": "meeting_topics", "type": "string"}, ]

datapackage["resources"] = []

datapackage["resources"] += [{"name": "errors", "path": "errors.csv", PROP_STREAMING: True,
                              "schema": {"fields": [{"name": "error", "type": "string"}, ]}}]

datapackage["resources"] += [{PROP_STREAMING: True,
                              "name": "mk_attendance",
                              "path": "mk_attendance.csv",
                              "schema": {"fields": meeting_aggs_fields + [{"name": "mk_id", "type": "integer"},
                                                                          {"name": "mk_name", "type": "string"},
                                                                          {"name": "mk_membership_committee_names",
                                                                           "type": "string"},
                                                                          {"name": "mk_faction_id", "type": "integer"},
                                                                          {"name": "mk_faction_name", "type": "string"},
                                                                          ]}}]

spew(datapackage, [errors, mk_attendance])
