from datapackage_pipelines.wrapper import ingest, spew
from datapackage_pipelines.utilities.resources import PROP_STREAMING
import logging, yaml, json, datetime
from functools import lru_cache


FACTION_MEMBER_POSITION = 54

FACTION_CHAIRPERSON_POSITION = 48

GOV_MINISTRY_POSITIONS = {
    31: 'משנה לראש הממשלה',
    39: 'שר',
    40: 'סגן שר',
    45: 'ראש הממשלה',
    49: 'מ"מ שר',
    50: 'סגן ראש הממשלה',
    51: 'מ"מ ראש הממשלה',
    57: 'שרה',
    59: 'סגנית שר'
}

COMMITTEE_POSITIONS = {
    41: 'יו"ר ועדה',
    42: 'חבר ועדה',
    66: 'חברת ועדה',
    67: 'מ"מ חבר ועדה'
}

# https://commons.wikimedia.org/wiki/File:Male_portrait_placeholder_cropped.jpg
MK_INDIVIDUAL_PHOTO_MALE = 'https://oknesset.org/static/img/Male_portrait_placeholder_cropped.jpg'

# https://commons.wikimedia.org/wiki/File:Female_portrait_placeholder_cropped.jpg
MK_INDIVIDUAL_PHOTO_FEMALE = 'https://oknesset.org/static/img/Female_portrait_placeholder_cropped.jpg'

MISSING_MK_INDIVIDUAL_IDS = [
    '984'
]


@lru_cache(maxsize=1)
def get_mks_extra():
    with open('join_mks_extra_details.yaml') as f:
        return yaml.load(f)


def update_mk_individual_photo(mk):
    # mk_individual_photo from Knesset API has copyright problems
    # we replace it with our own photo or a placeholder photo
    photo_url = get_mks_extra().get(mk['mk_individual_id'], {}).get('photo_url')
    if not photo_url:
        photo_url = {'זכר': MK_INDIVIDUAL_PHOTO_MALE,
                     'נקבה': MK_INDIVIDUAL_PHOTO_FEMALE}.get(mk['GenderDesc']) or MK_INDIVIDUAL_PHOTO_FEMALE
    mk['mk_individual_photo'] = photo_url
    return mk


parameters, datapackage, resources = ingest()
aggregations = {"stats": {}}
kns_mksitecode, kns_person = None, None
kns_person_descriptor = None
kns_persontoposition, kns_position = None, None
mk_individual_descriptor = {
  "schema": {
    "fields": [
      {
        "name": "mk_individual_id",
        "type": "integer"
      },
      {
        "name": "mk_status_id",
        "type": "integer"
      },
      {
        "name": "mk_individual_name",
        "type": "string"
      },
      {
        "name": "mk_individual_name_eng",
        "type": "string"
      },
      {
        "name": "mk_individual_first_name",
        "type": "string"
      },
      {
        "name": "mk_individual_first_name_eng",
        "type": "string"
      },
      {
        "name": "mk_individual_email",
        "type": "string"
      },
      {
        "name": "mk_individual_photo",
        "type": "string"
      }
    ]
  }
}


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
    # elif descriptor["name"] == "mk_individual":
    #     mk_individual_resource = resource
    #     mk_individual_descriptor = descriptor
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

mk_individual_committees = []
mk_individual_factions = []
mk_individual_govministries = []
mk_individual_faction_chairpersons = []
factions = {}
faction_memberships = {}


def faction_dates_days_iterator(start_date, finish_date):
    if not finish_date:
        finish_date = datetime.date.today()
    cur_date = start_date
    while cur_date <= finish_date:
        yield cur_date
        cur_date += datetime.timedelta(days=1)


def update_faction(faction_id, faction_name, start_date, finish_date, mk_id, knesset):
    start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d %H:%M:%S').date()
    if finish_date:
        finish_date = datetime.datetime.strptime(finish_date, '%Y-%m-%d %H:%M:%S').date()
    if faction_id:
        faction_membership_days = faction_memberships.setdefault(faction_id, {}).setdefault(knesset, {})
        for day_date in faction_dates_days_iterator(start_date, finish_date):
            faction_membership_days.setdefault(day_date, set()).add(mk_id)
        faction = factions.get(faction_id)
        if faction:
            if faction['name'] != faction_name:
                error_msg = 'faction name mismatch (knesset={} faction_id={} faction_name={} faction["name"]={})'.format(knesset, faction_id, faction_name, faction['name'])
                logging.warning(error_msg)
                # if not knesset or int(knesset) < 21:
                #     raise Exception(error_msg)
            faction['knessets'].add(knesset)
            if faction['start_date'] > start_date:
                faction['start_date'] = start_date
            if not finish_date or (faction['finish_date'] and faction['finish_date'] < finish_date):
                faction['finish_date'] = finish_date
        else:
            factions[faction_id] = {'id': faction_id, 'name': faction_name,
                                    'start_date': start_date, 'finish_date': finish_date,
                                    'knessets': {knesset}}


def get_person_positions(person_id, mk_individual_row):
    positions = []
    for kns_persontoposition_row in kns_persontopositions[person_id]:
        if kns_persontoposition_row['KnessetNum'] is None:
            logging.warning('invalid persontoposition row - missing KnessetNum: {}'.format(kns_persontoposition_row))
            continue
        start_date = kns_persontoposition_row["StartDate"].strftime('%Y-%m-%d %H:%M:%S')
        finish_date = kns_persontoposition_row["FinishDate"]
        if finish_date:
            finish_date = finish_date.strftime('%Y-%m-%d %H:%M:%S')
        update_faction(kns_persontoposition_row['FactionID'], kns_persontoposition_row['FactionName'],
                       start_date, finish_date, mk_individual_row['mk_individual_id'],
                       kns_persontoposition_row['KnessetNum'])
        mk_position = {field: kns_persontoposition_row[field] for field in ("KnessetNum",
                                                                            "GovMinistryID", "GovMinistryName",
                                                                            "DutyDesc",
                                                                            "FactionID", "FactionName",
                                                                            "GovernmentNum",
                                                                            "CommitteeID", "CommitteeName")}
        if not parameters.get("filter-knesset-num") or int(mk_position["KnessetNum"]) in parameters["filter-knesset-num"]:
            position_id = int(kns_persontoposition_row["PositionID"])
            position = kns_position.get(position_id, {'Description': str(position_id), 'GenderID': 252})

            mk_position.update(start_date=start_date,
                               finish_date=finish_date,
                               position=position["Description"],
                               position_id=position_id,
                               gender={250: "f", 251: "m", 252: "o"}[int(position["GenderID"])],)
            mk_position_start_date = datetime.datetime.strptime(mk_position['start_date'],
                                                                '%Y-%m-%d %H:%M:%S').date()
            mk_position_finish_date = mk_position['finish_date']
            if mk_position_finish_date:
                mk_position_finish_date = datetime.datetime.strptime(mk_position['finish_date'],
                                                                     '%Y-%m-%d %H:%M:%S').date()
            if position_id == FACTION_CHAIRPERSON_POSITION:
                mk_individual_faction_chairpersons.append({'mk_individual_id': mk_individual_row['mk_individual_id'],
                                                           'faction_id': kns_persontoposition_row['FactionID'],
                                                           'faction_name': kns_persontoposition_row['FactionName'],
                                                           'start_date': mk_position_start_date,
                                                           'finish_date': mk_position_finish_date,
                                                           'knesset': kns_persontoposition_row['KnessetNum']})
            elif position_id == FACTION_MEMBER_POSITION or kns_persontoposition_row['FactionID']:
                mk_individual_factions.append({'mk_individual_id': mk_individual_row['mk_individual_id'],
                                               'faction_id': kns_persontoposition_row['FactionID'],
                                               'faction_name': kns_persontoposition_row['FactionName'],
                                               'start_date': mk_position_start_date,
                                               'finish_date': mk_position_finish_date,
                                               'knesset': kns_persontoposition_row['KnessetNum']})
            elif position_id in COMMITTEE_POSITIONS or kns_persontoposition_row['CommitteeID']:
                mk_individual_committees.append({'mk_individual_id': mk_individual_row['mk_individual_id'],
                                                 'committee_id': kns_persontoposition_row['CommitteeID'],
                                                 'committee_name': kns_persontoposition_row['CommitteeName'],
                                                 'position_id': position_id,
                                                 'position_name': COMMITTEE_POSITIONS.get(position_id, ''),
                                                 'start_date': mk_position_start_date,
                                                 'finish_date': mk_position_finish_date,
                                                 'knesset': kns_persontoposition_row['KnessetNum']})
            elif position_id in GOV_MINISTRY_POSITIONS or kns_persontoposition_row['GovMinistryID']:
                mk_individual_govministries.append({'mk_individual_id': mk_individual_row['mk_individual_id'],
                                                    'govministry_id': kns_persontoposition_row['GovMinistryID'],
                                                    'govministry_name': kns_persontoposition_row['GovMinistryName'],
                                                    'position_id': position_id,
                                                    'position_name': GOV_MINISTRY_POSITIONS.get(position_id, ''),
                                                    'start_date': mk_position_start_date,
                                                    'finish_date': mk_position_finish_date,
                                                    'knesset': kns_persontoposition_row['KnessetNum']})
        positions.append(mk_position)
    mk_individual_row.update(positions=positions)


mk_individuals = []
mk_individual_names = []


def get_mk_individual_positions_resource():
    mks_extra = get_mks_extra()
    for kns_person_id, kns_person_row in kns_person.items():
        mk_individual_id = None
        for mkindid, mksitecode in kns_mksitecode.items():
            if int(mksitecode["KnsID"]) == int(kns_person_id):
                mk_individual_id = mkindid
                break
        if not mk_individual_id:
            if int(kns_person_id) not in map(int, kns_mksitecode.keys()):
                mk_individual_id = int(kns_person_id)
            else:
                mk_individual_id = max([k['SiteId'] for k in kns_mksitecode.values()]) + 1
        kns_mksitecode[int(kns_person_id)] = {
            'KnsID': kns_person_id,
            'MKSiteCode': max([k['MKSiteCode'] for k in kns_mksitecode.values()]) + 1,
            'SiteId': mk_individual_id
        }
        mk_individual_row = {
            'mk_individual_id': int(mk_individual_id),
            'mk_status_id': 0,
            'mk_individual_name': kns_person_row["LastName"] or "",
            'mk_individual_name_eng': '',
            'mk_individual_first_name': kns_person_row["FirstName"] or '',
            'mk_individual_first_name_eng': '',
            'mk_individual_email': kns_person_row['Email'] or '',
            'mk_individual_photo': '',
        }
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
            yield update_mk_individual_photo(mk_individual_row)
            del mk_individual_row['positions']
            mk_individuals.append(mk_individual_row)


def get_mk_individual_resource():
    for row in mk_individuals:
        yield update_mk_individual_photo(row)


def get_membership_row(row, faction_id, knesset):
    return {'faction_id': faction_id,
            'faction_name': factions[faction_id]['name'],
            'start_date': row['start_date'],
            'finish_date': row['finish_date'],
            'member_mk_ids': list(row['mk_ids']),
            'knesset': knesset}


def get_faction_memberships_resource():
    for faction_id in sorted(faction_memberships):
        for knesset in sorted(faction_memberships[faction_id]):
            membership_days = faction_memberships[faction_id][knesset]
            membership = None
            for day in sorted(membership_days):
                mk_ids = membership_days[day]
                if membership and membership['mk_ids'] == mk_ids:
                    membership['finish_date'] += datetime.timedelta(days=1)
                else:
                    if membership:
                        yield get_membership_row(membership, faction_id, knesset)
                    membership = {'start_date': day, 'finish_date': day,
                                  'mk_ids': mk_ids}
            if membership:
                yield get_membership_row(membership, faction_id, knesset)


new_fields = kns_person_descriptor["schema"]["fields"] + [{"name": "altnames", "type": "array"}]
mk_individual_descriptor["schema"]["fields"] = [f for f in mk_individual_descriptor["schema"]["fields"]
                                                if f['name'] not in [f['name'] for f in new_fields]]
mk_individual_descriptor["schema"]["fields"] += new_fields


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
                                                           {'name': 'faction_name', 'type': 'string'},
                                                           {'name': 'start_date', 'type': 'date'},
                                                           {'name': 'finish_date', 'type': 'date'},
                                                           {'name': 'knesset', 'type': 'integer'}]}}

mk_individual_faction_chairpersons_descriptor = {PROP_STREAMING: True,
                                                 'name': 'mk_individual_faction_chairpersons',
                                                 'path': 'mk_individual_faction_chairpersons.csv',
                                                 'schema': {'fields': [{"name": "mk_individual_id", "type": "integer"},
                                                                       {'name': 'faction_id', 'type': 'integer'},
                                                                       {'name': 'faction_name', 'type': 'string'},
                                                                       {'name': 'start_date', 'type': 'date'},
                                                                       {'name': 'finish_date', 'type': 'date'},
                                                                       {'name': 'knesset', 'type': 'integer'}]}}

mk_individual_committees_descriptor = {PROP_STREAMING: True,
                                       'name': 'mk_individual_committees',
                                       'path': 'mk_individual_committees.csv',
                                       'schema': {'fields': [{"name": "mk_individual_id", "type": "integer"},
                                                             {'name': 'committee_id', 'type': 'integer'},
                                                             {'name': 'committee_name', 'type': 'string'},
                                                             {'name': 'position_id', 'type': 'integer'},
                                                             {'name': 'position_name', 'type': 'string'},
                                                             {'name': 'start_date', 'type': 'date'},
                                                             {'name': 'finish_date', 'type': 'date'},
                                                             {'name': 'knesset', 'type': 'integer'}]}}

mk_individual_govministries_descriptor = {PROP_STREAMING: True,
                                          'name': 'mk_individual_govministries',
                                          'path': 'mk_individual_govministries.csv',
                                          'schema': {'fields': [{"name": "mk_individual_id", "type": "integer"},
                                                                {'name': 'govministry_id', 'type': 'integer'},
                                                                {'name': 'govministry_name', 'type': 'string'},
                                                                {'name': 'position_id', 'type': 'integer'},
                                                                {'name': 'position_name', 'type': 'string'},
                                                                {'name': 'start_date', 'type': 'date'},
                                                                {'name': 'finish_date', 'type': 'date'},
                                                                {'name': 'knesset', 'type': 'integer'}]}}

factions_descriptor = {PROP_STREAMING: True,
                       'name': 'factions',
                       'path': 'factions.csv',
                       'schema': {'fields': [{'name': 'id', 'type': 'integer'},
                                             {'name': 'name', 'type': 'string'},
                                             {'name': 'start_date', 'type': 'date'},
                                             {'name': 'finish_date', 'type': 'date'},
                                             {'name': 'knessets', 'type': 'array'}]}}

faction_memberships_descriptor = {PROP_STREAMING: True,
                                  'name': 'faction_memberships',
                                  'path': 'faction_memberships.csv',
                                  'schema': {'fields': [{'name': 'faction_id', 'type': 'integer'},
                                                        {'name': 'faction_name', 'type': 'string'},
                                                        {'name': 'start_date', 'type': 'date'},
                                                        {'name': 'finish_date', 'type': 'date'},
                                                        {'name': 'member_mk_ids', 'type': 'array'},
                                                        {'name': 'knesset', 'type': 'integer'}]}}


def counter(rows_iter, stat):
    i = 0
    for i, row in enumerate(rows_iter, start=1):
        yield row
    aggregations["stats"][stat] = i


def start_finish_date_order_key(row):
    start_date, finish_date = row['start_date'], row['finish_date']
    if not finish_date:
        finish_date = datetime.date.today()
    return start_date, finish_date


def start_finish_date_order(row_iter):
    return sorted(row_iter, key=start_finish_date_order_key, reverse=True)


def get_factions_resource():
    for faction in factions.values():
        faction['knessets'] = list(faction['knessets'])
        yield faction


def get_mk_individual_resources():
    yield counter(get_mk_individual_positions_resource(), 'mk_individual_positions')
    yield counter(get_mk_individual_resource(), 'mk_individual')
    yield counter(kns_knessetdates, 'kns_knessetdates')
    yield counter(mk_individual_names, 'mk_individual_names')
    yield start_finish_date_order(counter(mk_individual_factions, 'mk_individual_factions'))
    yield start_finish_date_order(counter(mk_individual_faction_chairpersons, 'mk_individual_faction_chairpersons'))
    yield start_finish_date_order(counter(mk_individual_committees, 'mk_individual_committees'))
    yield start_finish_date_order(counter(mk_individual_govministries, 'mk_individual_govministries'))
    yield start_finish_date_order(counter(get_factions_resource(), 'factions'))
    yield start_finish_date_order(counter(get_faction_memberships_resource(), 'faction_memberships'))


spew(dict(datapackage, resources=[mk_individual_positions_descriptor,
                                  {
                                    PROP_STREAMING: True,
                                    "encoding": "utf-8",
                                    "format": "csv",
                                    "name": "mk_individual",
                                    "path": "mk_individual.csv",
                                    **mk_individual_descriptor
                                  },
                                  kns_knessetdates_descriptor,
                                  mk_individual_names_descriptor,
                                  mk_individual_factions_descriptor,
                                  mk_individual_faction_chairpersons_descriptor,
                                  mk_individual_committees_descriptor,
                                  mk_individual_govministries_descriptor,
                                  factions_descriptor,
                                  faction_memberships_descriptor]),
     get_mk_individual_resources(),
     aggregations["stats"])
