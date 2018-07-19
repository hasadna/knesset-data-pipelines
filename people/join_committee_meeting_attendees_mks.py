from datapackage_pipelines.wrapper import ingest, spew
from datapackage_pipelines.utilities.resources import PROP_STREAMING
import logging


parameters, datapackage, resources = ingest()


mk_individuals = []
for mk_individual in next(resources):
    mk_names = set()
    for name_pair in ((mk_individual["mk_individual_first_name"], mk_individual["mk_individual_name"]),
                      (mk_individual["mk_individual_first_name_eng"], mk_individual["mk_individual_name_eng"]),
                      (mk_individual["FirstName"], mk_individual["LastName"]),):
        if all(name_pair):
            mk_names.add("{} {}".format(*name_pair))
    if mk_individual["altnames"] and len(mk_individual["altnames"]) > 0:
        mk_names.update(mk_individual["altnames"])
    mk_individual["mk_names"] = list(mk_names)
    mk_individuals.append(mk_individual)


def get_mk_individual(mk):
    if "LastUpdatedDate" in mk:
        del mk["LastUpdatedDate"]
    if "knesset_nums" not in mk:
        mk["knesset_nums"] = set()
        for position in mk["positions"]:
            if position.get("position") in ["חברת הכנסת", "חבר הכנסת"] or position.get("position_id") in [61, 43]:
                if position.get("KnessetNum"):
                    # start_date = datetime.datetime.strptime(position["start_date"], "%Y-%m-%d %H:%M:%S")
                    # finish_date = datetime.datetime.strptime(position["finish_date"], "%Y-%m-%d %H:%M:%S")
                    mk["knesset_nums"].add(position["KnessetNum"])
                # else:
                #     logging.warning("invalid position - missing KnessetNum: {}".format(position))
        mk["knesset_nums"] = list(mk["knesset_nums"])
    return mk


def get_resource():
    for meeting in next(resources):
        all_attendee_names = set()
        for attendee_names in (meeting["mks"], meeting["invitees"], meeting["legal_advisors"], meeting["manager"]):
            if attendee_names and len(attendee_names) > 0:
                for attendee_name in attendee_names:
                    if type(attendee_name) == str:
                        all_attendee_names.add(attendee_name)
                    else:
                        all_attendee_names.add(attendee_name["name"])
        attended_mk_individual_ids = set()
        for attendee_name in all_attendee_names:
            for mk_individual in filter(lambda mk: meeting["KnessetNum"] in mk["knesset_nums"],
                                        map(get_mk_individual, mk_individuals)):
                if meeting["KnessetNum"] in mk_individual["knesset_nums"]:
                    name_equals, name_in = False, False
                    for name in mk_individual["mk_names"]:
                        if name == attendee_name:
                            name_equals += 1
                        if name in attendee_name:
                            name_in += 1
                    if name_equals or name_in:
                        attended_mk_individual_ids.add(mk_individual["mk_individual_id"])
        meeting["attended_mk_individual_ids"] = list(attended_mk_individual_ids)
        yield meeting


datapackage["resources"] = [datapackage["resources"][1]]
datapackage["resources"][0]["schema"]["fields"] += [{"name": "attended_mk_individual_ids", "type": "array"}]


spew(datapackage, [get_resource()])
