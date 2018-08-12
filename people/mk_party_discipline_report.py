import logging
from datapackage_pipelines.wrapper import ingest, spew
from datapackage_pipelines.utilities.resources import PROP_STREAMING


VOTE_URL_TEMPLATE = 'http://www.knesset.gov.il/vote/heb/Vote_Res_Map.asp?vote_id_t={vote_id}'


REPORT_FIELDS = [{'name': 'mk_id', 'type': 'integer'},
                 {'name': 'mk_name', 'type': 'string'},
                 {'name': 'faction_ids', 'type': 'array'},
                 {'name': 'faction_names', 'type': 'string'},
                 {'name': 'party_discipline_votes', 'type': 'integer'},
                 {'name': 'party_non_discipline_votes', 'type': 'integer'}]

DETAILS_FIELDS = [{'name': 'vote_id', 'type': 'integer'},
                  {'name': 'vote_url', 'type': 'string'},
                  {'name': 'vote_datetime', 'type': 'datetime'},
                  {'name': 'vote_knesset', 'type': 'integer'},
                  {'name': 'vote_plenum', 'type': 'integer'},
                  {'name': 'vote_assembly', 'type': 'integer'},
                  {'name': 'vote_pagra', 'type': 'boolean'},
                  {'name': 'mk_id', 'type': 'integer'},
                  {'name': 'mk_name', 'type': 'string'},
                  {'name': 'faction_id', 'type': 'integer'},
                  {'name': 'faction_name', 'type': 'string'},
                  {'name': 'vote_majority', 'type': 'string'}]


def is_pagra_included(vote_pagra, parameters_pagra):
    if parameters_pagra == 'include':
        return True
    elif vote_pagra and parameters_pagra == 'only':
        return True
    elif not vote_pagra and parameters_pagra == 'exclude':
        return True
    else:
        return False


def main():
    parameters, datapackage, resources = ingest()


    datapackage['resources'].append({PROP_STREAMING: True,
                                     'name': 'details_' + parameters['name'],
                                     'path': 'details_' + parameters['name'] + '.csv',
                                     'schema': {'fields': DETAILS_FIELDS}})

    datapackage['resources'].append({PROP_STREAMING: True,
                                     'name': 'report_' + parameters['name'],
                                     'path': 'report_' + parameters['name'] + '.csv',
                                     'schema': {'fields': REPORT_FIELDS}})

    mk_names = {}
    factions = {}
    mk_report = {}
    mk_faction_ids = {}
    report_details = []

    def get_mk_individual_names(resource):
        for row in resource:
            yield row
            mk_names[row['mk_individual_id']] = row['names'][0]

    def get_factions(resource):
        for row in resource:
            yield row
            factions[row['id']] = row['name']

    def get_mk_voted_against_majority(resource):
        for row in resource:
            yield row
            if not is_pagra_included(row['vote_pagra'], parameters.get('pagra', 'include')):
                continue
            if 'knesset' in parameters and row['vote_knesset'] != parameters['knesset']:
                continue
            if 'plenum' in parameters and row['vote_plenum'] != parameters['plenum']:
                continue
            if 'assembly' in parameters and row['vote_assembly'] != parameters['assembly']:
                continue
            mk_faction_ids.setdefault(row['mk_id'], set()).add(row['faction_id'])
            mk_report.setdefault(row['mk_id'],
                                 [0, 0])[1 if row['voted_against_majority'] else 0] += 1
            if row['voted_against_majority']:
                report_details.append({'vote_id': row['vote_id'],
                                       'vote_url': VOTE_URL_TEMPLATE.format(**row),
                                       'vote_datetime': row['vote_datetime'],
                                       'vote_knesset': row['vote_knesset'],
                                       'vote_plenum': row['vote_plenum'],
                                       'vote_assembly': row['vote_assembly'],
                                       'vote_pagra': row['vote_pagra'],
                                       'mk_id': row['mk_id'],
                                       'mk_name': mk_names[row['mk_id']],
                                       'faction_id': row['faction_id'],
                                       'faction_name': factions[row['faction_id']],
                                       'vote_majority': row['vote_majority']})

    def get_details():
        yield from report_details

    def get_report():
        for mk_id, mk_discipline in mk_report.items():
            with_votes, against_votes = mk_discipline
            # total_votes = with_votes + against_votes
            # with_votes_percent = int(with_votes / total_votes * 100)
            faction_names = [factions[faction_id] for faction_id in mk_faction_ids[mk_id]]
            yield {'mk_id': mk_id,
                   'mk_name': mk_names[mk_id],
                   'faction_names': ', '.join(faction_names),
                   'faction_ids': list(mk_faction_ids[mk_id]),
                   'party_discipline_votes': with_votes,
                   'party_non_discipline_votes': against_votes}

    # def get_percents_from_total(resource):
    #     highest, lowest = None, None
    #     report = []
    #     for row in resource:
    #         percent = row['party_discipline_votes_percent']
    #         if not highest or percent > highest:
    #             highest = percent
    #         if not lowest or percent < lowest:
    #             lowest = percent
    #         report.append(row)
    #     for row in report:
    #         percent = row['party_discipline_votes_percent']
    #         percent_from_total = int((percent - lowest) / (highest - lowest) * 100)
    #         row['party_discipline_votes_percent_from_total'] = percent_from_total
    #         yield row

    def get_resources(resources):
        for resource, descriptor in zip(resources, datapackage['resources']):
            if descriptor['name'] == 'mk_individual_names':
                yield get_mk_individual_names(resource)
            elif descriptor['name'] == 'factions':
                yield get_factions(resource)
            elif descriptor['name'] == 'mk_voted_against_majority':
                yield get_mk_voted_against_majority(resource)
            else:
                yield resource
        yield get_details()
        yield get_report()

    spew(datapackage, get_resources(resources))


if __name__ == '__main__':
    main()
