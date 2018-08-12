from datapackage_pipelines.wrapper import ingest, spew
from datapackage_pipelines.utilities.resources import PROP_STREAMING
import logging, yaml, json, datetime


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


kns_knessetdates, kns_knessetdates_descriptor = [], {}


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
    elif descriptor['name'] == 'kns_knessetdates':
        for row in resource:
            kns_knessetdates.append(row)
        kns_knessetdates_descriptor[PROP_STREAMING] = True
        kns_knessetdates_descriptor.update(name='kns_knessetdates',
                                           path='kns_knessetdates.csv',
                                           schema=descriptor['schema'])
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


mk_individual_committees = []
mk_individual_factions = []
factions = {}
faction_memberships = {}


def faction_dates_days_iterator(start_date, finish_date):
    finish_date = datetime.date.today() if not finish_date else datetime.datetime.strptime(finish_date,
                                                                                           '%Y-%m-%d %H:%M:%S').date()
    start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d %H:%M:%S').date()
    cur_date = start_date
    while cur_date <= finish_date:
        yield cur_date
        cur_date += datetime.timedelta(days=1)


def update_faction(faction_id, faction_name, start_date, finish_date, mk_id):
    if faction_id:
        faction_membership_days = faction_memberships.setdefault(faction_id, {})
        for day_date in faction_dates_days_iterator(start_date, finish_date):
            faction_membership_days.setdefault(day_date, set()).add(mk_id)
        faction = factions.get(faction_id)
        if faction:
            assert faction['name'] == faction_name, 'faction name mismatch ({}: {})'.format(faction_id, faction_name)
            if faction['start_date'] > start_date:
                faction['start_date'] = start_date
            if not finish_date or (faction['finish_date'] and faction['finish_date'] < finish_date):
                faction['finish_date'] = finish_date
        else:
            factions[faction_id] = {'id': faction_id, 'name': faction_name,
                                    'start_date': start_date, 'finish_date': finish_date}


def get_person_positions(person_id, mk_individual_row):
    positions = []
    for kns_persontoposition_row in kns_persontopositions[person_id]:
        start_date = kns_persontoposition_row["StartDate"].strftime('%Y-%m-%d %H:%M:%S')
        finish_date = kns_persontoposition_row["FinishDate"]
        if finish_date:
            finish_date = finish_date.strftime('%Y-%m-%d %H:%M:%S')
        update_faction(kns_persontoposition_row['FactionID'], kns_persontoposition_row['FactionName'],
                       start_date, finish_date, mk_individual_row['mk_individual_id'])
        mk_position = {field: kns_persontoposition_row[field] for field in ("KnessetNum",
                                                                            "GovMinistryID", "GovMinistryName",
                                                                            "DutyDesc",
                                                                            "FactionID", "FactionName",
                                                                            "GovernmentNum",
                                                                            "CommitteeID", "CommitteeName")}
        if not parameters.get("filter-knesset-num") or int(mk_position["KnessetNum"]) in parameters["filter-knesset-num"]:
            position_id = int(kns_persontoposition_row["PositionID"])
            position = kns_position[position_id]

            mk_position.update(start_date=start_date,
                               finish_date=finish_date,
                               position=position["Description"],
                               position_id=position_id,
                               gender={250: "f", 251: "m", 252: "o"}[int(position["GenderID"])],)
            if position_id == 54:
                mk_individual_factions.append({'mk_individual_id': mk_individual_row['mk_individual_id'],
                                               'faction_id': kns_persontoposition_row['FactionID'],
                                               'start_date': mk_position['start_date'],
                                               'finish_date': mk_position['finish_date']})
            elif position_id in (42, 66):
                mk_individual_committees.append({'mk_individual_id': mk_individual_row['mk_individual_id'],
                                                 'committee_id': kns_persontoposition_row['CommitteeID'],
                                                 'start_date': mk_position['start_date'],
                                                 'finish_date': mk_position['finish_date']})
        positions.append(mk_position)
    mk_individual_row.update(positions=positions)


mk_individuals = []
mk_individual_names = []


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
            get_person_positions(kns_person_id, mk_individual_row)
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
            mk_individual_names.append({'mk_individual_id': mk_individual_id,
                                        'names': mk_individual_row['altnames']})
            yield mk_individual_row
            del mk_individual_row['positions']
            mk_individuals.append(mk_individual_row)


def get_mk_individual_resource():
    for row in mk_individuals:
        yield row


def get_membership_row(row, faction_id):
    return {'faction_id': faction_id,
            'start_date': row['start_date'].strftime('%Y-%m-%d'),
            'finish_date': row['finish_date'].strftime('%Y-%m-%d'),
            'member_mk_ids': list(row['mk_ids'])}


def get_faction_memberships_resource():
    for faction_id in sorted(faction_memberships):
        membership_days = faction_memberships[faction_id]
        membership = None
        for day in sorted(membership_days):
            mk_ids = membership_days[day]
            if membership and membership['mk_ids'] == mk_ids:
                membership['finish_date'] += datetime.timedelta(days=1)
            else:
                if membership:
                    yield get_membership_row(membership, faction_id)
                membership = {'start_date': day, 'finish_date': day,
                              'mk_ids': mk_ids}
        if membership:
            yield get_membership_row(membership, faction_id)


def get_mk_individual_resources(resource):
    yield get_mk_individual_positions_resource(resource)
    yield get_mk_individual_resource()
    yield kns_knessetdates
    yield mk_individual_names
    yield mk_individual_factions
    yield mk_individual_committees
    yield factions.values()
    yield get_faction_memberships_resource()


mk_individual_descriptor["schema"]["fields"] += kns_person_descriptor["schema"]["fields"]
mk_individual_descriptor["schema"]["fields"] += [{"name": "altnames", "type": "array"}]


mk_individual_positions_descriptor = {PROP_STREAMING: True,
                                      'name': 'mk_individual_positions',
                                      'path': 'mk_individual_positions.csv',
                                      'schema': {'fields': mk_individual_descriptor['schema']['fields'] + [
                                          {"name": "positions", "type": "array"},
                                      ]}}

mk_individual_names_descriptor = {PROP_STREAMING: True,
                                  'name': 'mk_individual_names',
                                  'path': 'mk_individual_names.csv',
                                  'schema': {'fields': [{"name": "mk_individual_id", "type": "integer"},
                                                        {"name": "names", "type": "array"}]}}

mk_individual_factions_descriptor = {PROP_STREAMING: True,
                                     'name': 'mk_individual_factions',
                                     'path': 'mk_individual_factions.csv',
                                     'schema': {'fields': [{"name": "mk_individual_id", "type": "integer"},
                                                           {'name': 'faction_id', 'type': 'integer'},
                                                           {'name': 'start_date', 'type': 'string'},
                                                           {'name': 'finish_date', 'type': 'string'}]}}

mk_individual_committees_descriptor = {PROP_STREAMING: True,
                                       'name': 'mk_individual_committees',
                                       'path': 'mk_individual_committees.csv',
                                       'schema': {'fields': [{"name": "mk_individual_id", "type": "integer"},
                                                             {'name': 'committee_id', 'type': 'integer'},
                                                             {'name': 'start_date', 'type': 'string'},
                                                             {'name': 'finish_date', 'type': 'string'}]}}

factions_descriptor = {PROP_STREAMING: True,
                       'name': 'factions',
                       'path': 'factions.csv',
                       'schema': {'fields': [{'name': 'id', 'type': 'integer'},
                                             {'name': 'name', 'type': 'string'},
                                             {'name': 'start_date', 'type': 'string'},
                                             {'name': 'finish_date', 'type': 'string'}]}}

faction_memberships_descriptor = {PROP_STREAMING: True,
                                  'name': 'faction_memberships',
                                  'path': 'faction_memberships.csv',
                                  'schema': {'fields': [{'name': 'faction_id', 'type': 'integer'},
                                                        {'name': 'start_date', 'type': 'string'},
                                                        {'name': 'finish_date', 'type': 'string'},
                                                        {'name': 'member_mk_ids', 'type': 'array'}]}}

spew(dict(datapackage, resources=[mk_individual_positions_descriptor,
                                  mk_individual_descriptor,
                                  kns_knessetdates_descriptor,
                                  mk_individual_names_descriptor,
                                  mk_individual_factions_descriptor,
                                  mk_individual_committees_descriptor,
                                  factions_descriptor,
                                  faction_memberships_descriptor]),
     get_mk_individual_resources(mk_individual_resource),
     aggregations["stats"])
