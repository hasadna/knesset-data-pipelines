from datapackage_pipelines.wrapper import ingest, spew


# this members have a problem with their names
# we can match them directly
KMMBR_IDS_DIRECT_MATCH_TO_PERSON_ID = {'000000431': 431}


def get_mk_individuals(resource, data):
    data['mks'] = []
    for mk in resource:
        yield mk
        knesset_nums = set()
        for position in mk['positions']:
            if position.get('KnessetNum'):
                knesset_nums.add(position['KnessetNum'])
        data['mks'].append({'id': mk['mk_individual_id'],
                            'first_name': mk['mk_individual_first_name'].strip(),
                            'last_name': mk['mk_individual_name'].strip(),
                            'altnames': [name.strip() for name in mk['altnames']],
                            'knesset_nums': knesset_nums,
                            'person_id': mk['PersonID']})


def get_mk_individual_id(knesset_nums, kmmbr, data):
    if kmmbr['id'] in KMMBR_IDS_DIRECT_MATCH_TO_PERSON_ID:
        person_id = KMMBR_IDS_DIRECT_MATCH_TO_PERSON_ID[kmmbr['id']]
        mk_individual_ids = set((mk['id'] for mk in data['mks'] if mk['person_id'] == person_id))
    else:
        mk_individual_ids = set()
        for mk in data['mks']:
            if any([knesset_num in mk['knesset_nums'] for knesset_num in knesset_nums]):
                if '{} {}'.format(mk['first_name'], mk['last_name']) in kmmbr['names']:
                    mk_individual_ids.add(mk['id'])
                if '{} {}'.format(mk['last_name'], mk['first_name']) in kmmbr['names']:
                    mk_individual_ids.add(mk['id'])
                if any([name in kmmbr['names'] for name in mk['altnames']]):
                    mk_individual_ids.add(mk['id'])
    if len(mk_individual_ids) == 0:
        return None
    else:
        assert len(mk_individual_ids) == 1, \
            'num of mk ids is not 1 for kmmbr names {}: {}'.format(kmmbr['names'], mk_individual_ids)
        return mk_individual_ids.pop()


def get_kmmbr_results(kmmbr, data):
    knesset_nums = set()
    for vote_rslt in kmmbr['vote_rslts']:
        knesset_nums.add(vote_rslt['knesset_num'])
    mk_individual_id = get_mk_individual_id(knesset_nums, kmmbr, data)
    for vote_rslt in kmmbr['vote_rslts']:
        vote_rslt['mk_individual_id'] = mk_individual_id if mk_individual_id is not None else -1
        yield vote_rslt


def get_vote_rslts(resource, data):
    kmmbr = None
    for vote_rslt in resource:
        if not kmmbr or kmmbr['id'] != vote_rslt['kmmbr_id']:
            if kmmbr:
                yield from get_kmmbr_results(kmmbr, data)
            kmmbr = {'id': vote_rslt['kmmbr_id'],
                     'names': set(),
                     'vote_rslts': []}
        kmmbr['names'].add(vote_rslt['kmmbr_name'].strip())
        kmmbr['names'].add(vote_rslt['kmmbr_name'].strip().replace('`', "'"))
        kmmbr['vote_rslts'].append(vote_rslt)
    yield from get_kmmbr_results(kmmbr, data)


def get_resources(datapackage, resources):
    data = {}
    for descriptor, resource in zip(datapackage['resources'], resources):
        if descriptor['name'] == 'mk_individual_positions':
            yield get_mk_individuals(resource, data)
        elif descriptor['name'] == 'vote_rslts_kmmbr_shadow':
            yield get_vote_rslts(resource, data)
        else:
            yield resource


def get_datapackage(datapackage):
    for descriptor in datapackage['resources']:
        if descriptor['name'] == 'vote_rslts_kmmbr_shadow':
            new_fields = [{'name': 'mk_individual_id', 'type': 'integer'}]
            descriptor['schema']['fields'] = [field for field in descriptor['schema']['fields']
                                              if field['name'] not in [f['name'] for f in new_fields]]
            descriptor['schema']['fields'] += new_fields
    return datapackage


def main():
    parameters, datapackage, resources, stats = ingest() + ({},)
    spew(get_datapackage(datapackage),
         get_resources(datapackage, resources),
         stats)


if __name__ == '__main__':
    main()