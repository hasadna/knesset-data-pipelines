from datapackage_pipelines.wrapper import ingest, spew


def get_kmmbr_votes(resource, data, stats):
    data['votes'] = {}
    stats.update(known_vote_types=0, unknown_vote_types=0)
    for kmmbr_vote in resource:
        vote = data['votes'].setdefault(kmmbr_vote['vote_id'], {'בעד': [],
                                                                'נמנע': [],
                                                                'נגד': []})
        if kmmbr_vote['result_type_name'] in vote:
            vote[kmmbr_vote['result_type_name']].append(kmmbr_vote['mk_individual_id'])
            stats['known_vote_types'] += 1
        else:
            stats['unknown_vote_types'] += 1
    percent_unknowns = stats['unknown_vote_types'] / stats['known_vote_types']
    assert percent_unknowns < 2, 'got too many unknown vote types: {}%'.format(percent_unknowns)


def get_vote_results(resource, data, stats):
    stats.update(known_votes=0, unknown_votes=0)
    for vote_result in resource:
        vote = data['votes'].get(vote_result['id'])
        if vote:
            vote_result.update(mk_ids_pro=vote['בעד'],
                               mk_ids_against=vote['נגד'],
                               mk_ids_abstain=vote['נמנע'])
            stats['known_votes'] += 1
        else:
            stats['unknown_votes'] += 1
        yield vote_result
    percent_unknowns = stats['unknown_votes'] / stats['known_votes']
    assert percent_unknowns < 2, 'got too many unknown votes: {}%'.format(percent_unknowns)


def get_resources(resources, stats, data):
    for i, resource in enumerate(resources):
        if i == data['kmmbr_index']:
            get_kmmbr_votes(resource, data, stats)
        elif i == data['votes_index']:
            yield get_vote_results(resource, data, stats)
        else:
            yield resource


def get_datapackage(datapackage, data):
    for i, descriptor in enumerate(datapackage['resources']):
        if descriptor['name'] == 'view_vote_rslts_hdr_approved':
            data['votes_index'] = i
            existing_fields = {field['name']: field for field in descriptor['schema']['fields']}
            new_fields = [{'name': 'mk_ids_pro', 'type': 'array'},
                          {'name': 'mk_ids_against', 'type': 'array'},
                          {'name': 'mk_ids_abstain', 'type': 'array'},]
            for new_field in new_fields:
                if new_field['name'] in existing_fields:
                    existing_fields[new_field['name']].update(new_field)
                else:
                    descriptor['schema']['fields'].append(new_field)
        elif descriptor['name'] == 'vote_rslts_kmmbr_shadow':
            data['kmmbr_index'] = i
    del datapackage['resources'][data['kmmbr_index']]
    return datapackage


def main():
    parameters, datapackage, resources, stats, data = ingest() + ({}, {})
    spew(get_datapackage(datapackage, data),
         get_resources(resources, stats, data),
         stats)


if __name__ == '__main__':
    main()
