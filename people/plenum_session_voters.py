from datapackage_pipelines.wrapper import ingest, spew


def get_votes(resource, data, stats):
    data['session_voters'] = {}
    stats['num_votes'] = 0
    stats['num_vote_mks'] = 0
    for vote in resource:
        voters = data['session_voters'].setdefault(vote['session_id'], set())
        for attr in ['mk_ids_pro', 'mk_ids_against', 'mk_ids_abstain']:
            mk_ids = vote[attr]
            if mk_ids:
                for mk_id in mk_ids:
                    voters.add(mk_id)
                    stats['num_vote_mks'] += 1
        stats['num_votes'] += 1


def get_plenum(resource, data, stats):
    stats.update(known_sessions=0, unknown_sessions=0)
    for session in resource:
        if session['PlenumSessionID'] in data['session_voters']:
            stats['known_sessions'] += 1
            session['voter_mk_ids'] = list(data['session_voters'][session['PlenumSessionID']])
        else:
            session['voter_mk_ids'] = None
            stats['unknown_sessions'] += 1
        if not session['voter_mk_ids']:
            session['voter_mk_ids'] = None
        yield session


def get_resources(resources, stats, data):
    for i, resource in enumerate(resources):
        if i == data['votes_index']:
            get_votes(resource, data, stats)
        elif i == data['plenum_index']:
            yield get_plenum(resource, data, stats)
        else:
            yield resource


def get_datapackage(datapackage, data):
    for i, descriptor in enumerate(datapackage['resources']):
        if descriptor['name'] == 'view_vote_rslts_hdr_approved':
            data['votes_index'] = i
        elif descriptor['name'] == 'kns_plenumsession':
            data['plenum_index'] = i
            fields = [{'name': 'voter_mk_ids', 'type': 'array'}]
            descriptor['schema']['fields'] += fields
    del datapackage['resources'][data['votes_index']]
    return datapackage


def main():
    parameters, datapackage, resources, stats, data = ingest() + ({}, {})
    spew(get_datapackage(datapackage, data),
         get_resources(resources, stats, data),
         stats)


if __name__ == '__main__':
    main()
