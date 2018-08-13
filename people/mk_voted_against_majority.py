import os, datetime, logging
from datapackage_pipelines.wrapper import ingest, spew
from datapackage_pipelines_knesset.common.get_mk_faction import get_mk_faction


def get_vote_faction_num_members(faction_memberships, vote_datetime):
    faction_num_members = {}
    vote_date = vote_datetime.date()
    for row in faction_memberships:
        start_date = row['start_date']
        finish_date = row['finish_date']
        if start_date <= vote_date <= finish_date:
            faction_id = row['faction_id']
            assert faction_id not in faction_num_members, 'invalid faction membership: {}'.format(row)
            faction_num_members[faction_id] = len(row['member_mk_ids'])
    return faction_num_members

def get_voted_against_party_majority(row, mk_factions, majority_percent, vote_datetime, vote_faction_num_members,
                                     minimal_num_members):
    party_votes = {}
    for vote_type in ['pro', 'against', 'abstain']:
        party_votes[vote_type] = {}
        mk_ids = row.get('mk_ids_{}'.format(vote_type))
        if mk_ids:
            for mk_id in mk_ids:
                faction_id = get_mk_faction(mk_factions.get(mk_id, []), vote_datetime)
                if faction_id:
                    party_votes[vote_type].setdefault(faction_id, set()).add(mk_id)
    party_pro_votes = party_votes.get('pro', {})
    party_against_votes = party_votes.get('against', {})
    party_abstain_votes = party_votes.get('abstain', {})
    voted_against_party_majority = {}
    for vote_type in ['pro', 'against', 'abstain']:
        mk_ids = row.get('mk_ids_{}'.format(vote_type))
        if mk_ids:
            for mk_id in mk_ids:
                faction_id = get_mk_faction(mk_factions.get(mk_id, []), vote_datetime)
                if faction_id:
                    faction_num_members = vote_faction_num_members.get(faction_id)
                    if faction_num_members:
                        if faction_num_members >= minimal_num_members:
                            party_pro_count = len(party_pro_votes.get(faction_id, []))
                            party_against_count = len(party_against_votes.get(faction_id, []))
                            party_abstain_count = len(party_abstain_votes.get(faction_id, []))
                            if party_pro_count / faction_num_members > majority_percent:
                                party_majority = 'pro'
                            elif party_against_count / faction_num_members > majority_percent:
                                party_majority = 'against'
                            elif party_abstain_count / faction_num_members > majority_percent:
                                party_majority = 'abstain'
                            else:
                                party_majority = None
                            if party_majority == 'pro' or party_majority == 'against':
                                if party_majority is not None and party_majority != vote_type:
                                    voted_against_party_majority[mk_id] = {'vote_majority': party_majority,
                                                                           'voted_against_majority': True}
                                else:
                                    voted_against_party_majority[mk_id] = {'vote_majority': party_majority,
                                                                           'voted_against_majority': False}
                    else:
                        logging.warning('failed to find faction num members: {} {} {}'.format(vote_datetime,
                                                                                              faction_id,
                                                                                              faction_num_members))
    return voted_against_party_majority


def mk_voted_against_majority(parameters, stats):
    resource_idx = {}
    mk_factions = {}
    faction_memberships = []

    def modify_datapackage(datapackage):
        for idx, resource in enumerate(datapackage['resources']):
            resource_idx[resource['name']] = idx
            if resource['name'] == 'view_vote_rslts_hdr_approved':
                resource['name'] = 'mk_voted_against_majority'
                resource['path'] = 'mk_voted_against_majority.csv'
                resource['schema']['fields'] = [{'name': 'vote_id', 'type': 'integer'},
                                                {'name': 'mk_id', 'type': 'integer'},
                                                {'name': 'faction_id', 'type': 'integer'},
                                                {'name': 'vote_knesset', 'type': 'integer'},
                                                {'name': 'vote_plenum', 'type': 'integer'},
                                                {'name': 'vote_assembly', 'type': 'integer'},
                                                {'name': 'vote_pagra', 'type': 'boolean'},
                                                {'name': 'vote_datetime', 'type': 'datetime'},
                                                {'name': 'vote_majority', 'type': 'string'},
                                                {'name': 'voted_against_majority', 'type': 'boolean'}]
        del datapackage['resources'][resource_idx['faction_memberships']]
        del datapackage['resources'][resource_idx['mk_individual_factions']]
        return datapackage

    def process_votes_resource(resource):
        stats['processed votes'] = 0
        for row in resource:
            stats['processed votes'] += 1
            vote_datetime = '{} {}'.format(row['vote_date'],
                                           row['vote_time'] if row['vote_time'] else '00:00')
            vote_datetime = datetime.datetime.strptime(vote_datetime, "%Y-%m-%d %H:%M")
            vote_faction_num_members = get_vote_faction_num_members(faction_memberships, vote_datetime)
            voted_against_majority = get_voted_against_party_majority(row, mk_factions,
                                                                      parameters['party-majority-percent'],
                                                                      vote_datetime,
                                                                      vote_faction_num_members,
                                                                      parameters['party-minimal-num-members'])
            vote_id = row['id']
            knesset, plenum, assembly, pagra = row['knesset'], row['plenum'], row['assembly'], row['pagra']
            for mk_id, voted_against in voted_against_majority.items():
                yield {'vote_id': vote_id,
                       'mk_id': mk_id,
                       'faction_id': get_mk_faction(mk_factions.get(mk_id, []),
                                                    vote_datetime),
                       'vote_knesset': knesset, 'vote_plenum': plenum, 'vote_assembly': assembly,
                       'vote_pagra': pagra, 'vote_datetime': vote_datetime,
                       'vote_majority': voted_against['vote_majority'],
                       'voted_against_majority': voted_against['voted_against_majority']}

    def process_resources(resources):
        for idx, resource in enumerate(resources):
            if idx == resource_idx['mk_individual_factions']:
                for row in resource:
                    mk_factions.setdefault(row['mk_individual_id'],
                                           []).append({'faction_id': row['faction_id'],
                                                       'start_date': row['start_date'],
                                                       'finish_date': row['finish_date']})
            elif idx == resource_idx['faction_memberships']:
                for row in resource:
                    faction_memberships.append(row)
            elif idx == resource_idx['view_vote_rslts_hdr_approved']:
                yield process_votes_resource(resource)
            else:
                yield resource

    return modify_datapackage, process_resources


def main(debug):
    parameters, datapackage, resources, stats = ingest(debug) + ({},)
    modify_datapackage, process_resources = mk_voted_against_majority(parameters, stats)
    datapackage = modify_datapackage(datapackage)
    spew(datapackage, process_resources(resources), stats)


if __name__ == '__main__':
    main(os.environ.get('KNESSET_DEBUG') == '1')
