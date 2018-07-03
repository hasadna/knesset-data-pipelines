from datapackage_pipelines.wrapper import ingest, spew
from datapackage_pipelines.utilities.resources import PROP_STREAMING
import logging, yaml, json


parameters, datapackage, resources = ingest()
aggregations = {"stats": {}}
kns_mksitecode, kns_person = None, None
kns_person_descriptor = None
kns_persontoposition, kns_position = None, None
mk_individual_resource, mk_individual_descriptor = None, None


mk_altnames = {}
with open('oknesset_all_mk_names_May26_2018.json') as f:
    for mk, mk_name in zip(*json.load(f)):
        mk_altnames.setdefault(int(mk["id"]), set()).add(mk_name.strip())


for descriptor, resource in zip(datapackage["resources"], resources):
    if descriptor["name"] == "kns_mksitecode":
        kns_mksitecode = {int(row["SiteId"]): row for row in resource}
    elif descriptor["name"] == "kns_person":
        kns_person = {int(row["PersonID"]): row for row in resource}
        kns_person_descriptor = descriptor
    elif descriptor["name"] == "mk_individual":
        mk_individual_resource = resource
        mk_individual_descriptor = descriptor
    elif descriptor["name"] == "kns_position":
        kns_position = {int(row["PositionID"]): row for row in resource}
    elif descriptor["name"] == "kns_persontoposition":
        kns_persontopositions = {}
        for row in resource:
            kns_persontopositions.setdefault(int(row["PersonID"]), []).append(row)
    else:
        for row in resource:
            pass


KNOWN_MK_PERSON_IDS = {
    955: kns_person[30407]  # Yehuda Glick - has a mismatch in name between mk_individual and kns_person
}


# TODO: remove this mk_individual matching function once this bug is fixed: https://github.com/hasadna/knesset-data/issues/147
def find_matching_kns_person(mk):
    for person_id, person in kns_person.items():
        person_first, person_last, person_email = person["FirstName"].strip(), person["LastName"].strip(), person["Email"]
        mk_first, mk_last, mk_email = mk["mk_individual_first_name"].strip(), mk["mk_individual_name"].strip(), mk["mk_individual_email"]
        name_match = (len(person_first) > 1 and len(mk_first) > 1 and person_first == mk_first and person_last == mk_last)
        email_match = (person_email and mk_email
                       and len(person_email.strip()) > 5 and len(mk_email.strip()) > 5 and
                       person_email.strip().lower() == mk_email.strip().lower())
        if name_match or email_match:
            return person_id, person
    person = KNOWN_MK_PERSON_IDS.get(int(mk["mk_individual_id"]))
    if person:
        return person["PersonID"], person
    return None, None


def get_person_positions(person_id):
    for kns_persontoposition_row in kns_persontopositions[person_id]:
        mk_position = {field: kns_persontoposition_row[field] for field in ("KnessetNum",
                                                                            "GovMinistryID", "GovMinistryName",
                                                                            "DutyDesc",
                                                                            "FactionID", "FactionName",
                                                                            "GovernmentNum",
                                                                            "CommitteeID", "CommitteeName")}
        if not parameters.get("filter-knesset-num") or int(mk_position["KnessetNum"]) in parameters["filter-knesset-num"]:
            position_id = int(kns_persontoposition_row["PositionID"])
            position = kns_position[position_id]
            finish_date = kns_persontoposition_row["FinishDate"]
            mk_position.update(start_date=kns_persontoposition_row["StartDate"].strftime('%Y-%m-%d %H:%M:%S'),
                               finish_date=finish_date.strftime('%Y-%m-%d %H:%M:%S') if finish_date else None,
                               position=position["Description"],
                               position_id=position_id,
                               gender={250: "f", 251: "m", 252: "o"}[int(position["GenderID"])],)
        yield {k: v for k, v in mk_position.items() if v}


mk_individuals = []


def get_mk_individual_positions_resource(resource):
    with open('join_mks_extra_details.yaml') as f:
        mks_extra = yaml.load(f)
    for mk_individual_row in resource:
        mk_individual_id = int(mk_individual_row["mk_individual_id"])
        kns_person_id, kns_person_row = None, None
        mksitecode = kns_mksitecode.get(mk_individual_id)
        if mksitecode:
            kns_person_id = int(mksitecode["KnsID"])
            kns_person_row = kns_person.get(kns_person_id)
            if not kns_person_row:
                logging.warning("person mismatch in kns_mksitecode for mk_individual_id {}".format(mk_individual_id))
                kns_person_id = None
        if not kns_person_id:
            kns_person_id, kns_person_row = find_matching_kns_person(mk_individual_row)
            if not kns_person_id or not kns_person_row:
                raise Exception("Failed to find matching person for mk_invidual {}".format(mk_individual_id))
        if parameters.get("filter-is-current") is None or kns_person_row["IsCurrent"] == parameters["filter-is-current"]:
            mk_individual_row.update(**kns_person_row)
            mk_individual_row["positions"] = list(get_person_positions(kns_person_id))
            altnames = mk_altnames.setdefault(mk_individual_id, set())
            altnames.add("{} {}".format(mk_individual_row["mk_individual_first_name"].strip(),
                                        mk_individual_row["mk_individual_name"].strip()).strip())
            altnames.add("{} {}".format(kns_person_row["FirstName"].strip(),
                                        mk_individual_row["LastName"].strip()).strip())
            if mk_individual_id in mks_extra:
                mk_extra = mks_extra[mk_individual_id]
                if 'altnames' in mk_extra:
                    altnames.update(set(mk_extra['altnames']))
            mk_individual_row["altnames"] = list(altnames)
            yield mk_individual_row
            del mk_individual_row['positions']
            mk_individuals.append(mk_individual_row)


def get_mk_individual_resource():
    for row in mk_individuals:
        yield row


def get_mk_individual_resources(resource):
    yield get_mk_individual_positions_resource(resource)
    yield get_mk_individual_resource()


mk_individual_descriptor["schema"]["fields"] += kns_person_descriptor["schema"]["fields"]
mk_individual_descriptor["schema"]["fields"] += [{"name": "altnames", "type": "array"}]


mk_individual_positions_descriptor = {PROP_STREAMING: True,
                                      'name': 'mk_individual_positions',
                                      'path': 'mk_individual_positions.csv',
                                      'schema': {'fields': mk_individual_descriptor['schema']['fields'] + [
                                          {"name": "positions", "type": "array"}
                                      ]}}

spew(dict(datapackage, resources=[mk_individual_positions_descriptor, mk_individual_descriptor]),
     get_mk_individual_resources(mk_individual_resource),
     aggregations["stats"])
