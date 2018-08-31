from dataflows import Flow, load, dump_to_path, PackageWrapper
import os
from collections import defaultdict
from functools import lru_cache
from datapackage_pipelines_knesset.common_flow import (rows_counter,
                                                       process_rows_remove_resource,
                                                       kns_knessetdates_processor,
                                                       get_knessetdate,
                                                       mk_individual_factions_processor,
                                                       mk_individual_names_processor,
                                                       get_mk_faction_ids)


def flow():
    data_path = 'data{}/'.format('_samples' if os.environ.get('KNESSET_DATA_SAMPLES') else '')
    kns_knessetdates_sorted = []
    mk_individual_factions = {}
    vote_discipline = {}
    all_mk_ids = set()
    aggregates = {}

    def get_vote_discipline_mk_ids(vote_id):
        return vote_discipline.get(vote_id, [set(), set()])

    def process_voted_against_majority(rows):
        for row in rows:
            undisciplined_mk_ids, disciplined_mk_ids = vote_discipline.setdefault(row['vote_id'], [set(), set()])
            if row['vote_majority'] in ['against', 'pro']:
                if row['voted_against_majority']:
                    undisciplined_mk_ids.add(row['mk_id'])
                else:
                    disciplined_mk_ids.add(row['mk_id'])

    def process_votes(votes):
        for vote in rows_counter('view_vote_rslts_hdr_approved', votes):
            vote_date = vote['vote_date']
            undisciplined_mk_ids, disciplined_mk_ids = get_vote_discipline_mk_ids(vote['id'])
            for mk_id, faction_id in get_mk_faction_ids(all_mk_ids, mk_individual_factions,
                                                        vote_date):
                knessetdate = get_knessetdate(kns_knessetdates_sorted, vote_date)
                agg = aggregates.setdefault(knessetdate['knesset'], {})\
                                .setdefault(knessetdate['plenum'], {})\
                                .setdefault(knessetdate['assembly'], {})\
                                .setdefault(knessetdate['pagra'], {})\
                                .setdefault(faction_id, {})\
                                .setdefault(mk_id, defaultdict(int))
                if mk_id in undisciplined_mk_ids:
                    agg['undisciplined_votes'] += 1
                elif mk_id in disciplined_mk_ids:
                    agg['disciplined_votes'] += 1
                agg['total_votes'] += 1

    def get_all_aggregates():
        for knesset, aggs in aggregates.items():
            for plenum, aggs in aggs.items():
                for assembly, aggs in aggs.items():
                    for pagra, aggs in aggs.items():
                            for faction_id, aggs in aggs.items():
                                for mk_id, agg in aggs.items():
                                    yield (knesset, plenum, assembly, pagra,
                                           faction_id, mk_id), agg

    def get_mk_aggregates():
        for agg_key, agg in get_all_aggregates():
            total_votes = agg.get('total_votes', 0)
            if total_votes > 0:
                undisciplined_votes_percent = int(agg.get('undisciplined_votes', 0)
                                                  / total_votes * 100)
                disciplined_votes_percent = int(agg.get('disciplined_votes', 0)
                                                / total_votes * 100)
                knesset, plenum, assembly, pagra, faction_id, mk_id = agg_key
                yield dict({'undisciplined_votes': 0,
                            'disciplined_votes': 0,
                            'total_votes': 0,},
                           **agg,
                           undisciplined_votes_percent=undisciplined_votes_percent,
                           disciplined_votes_percent=disciplined_votes_percent,
                           knesset=knesset, plenum=plenum, assembly=assembly,
                           pagra=int(pagra), faction_id=faction_id,
                           mk_id=mk_id)

    def get_aggregates(package: PackageWrapper):
        schema_fields = [{'name': 'knesset', 'type': 'integer'},
                         {'name': 'plenum', 'type': 'integer'},
                         {'name': 'assembly', 'type': 'integer'},
                         {'name': 'pagra', 'type': 'integer'},
                         {'name': 'faction_id', 'type': 'integer'},
                         {'name': 'mk_id', 'type': 'integer'},
                         {'name': 'undisciplined_votes', 'type': 'integer'},
                         {'name': 'disciplined_votes', 'type': 'integer'},
                         {'name': 'total_votes', 'type': 'integer'},
                         {'name': 'undisciplined_votes_percent', 'type': 'integer'},
                         {'name': 'disciplined_votes_percent', 'type': 'integer'},]
        package.pkg.add_resource({'name': 'mk_party_discipline_stats',
                                  'path': 'mk_party_discipline_stats.csv',
                                  'schema': {'fields': schema_fields}})
        yield package.pkg
        yield from package
        yield get_mk_aggregates()

    return Flow(load(data_path + 'members/mk_individual/datapackage.json',
                     resources=['mk_individual_names']),
                process_rows_remove_resource('mk_individual_names',
                                             mk_individual_names_processor(all_mk_ids)),
                load(data_path + 'members/mk_individual/datapackage.json',
                     resources=['mk_individual_factions']),
                process_rows_remove_resource('mk_individual_factions',
                                             mk_individual_factions_processor(mk_individual_factions)),
                load(data_path + 'knesset/kns_knessetdates/datapackage.json',
                     resources=['kns_knessetdates']),
                process_rows_remove_resource('kns_knessetdates',
                                             kns_knessetdates_processor(kns_knessetdates_sorted)),
                load(data_path + 'people/mk_voted_against_majority/datapackage.json',
                     resources=['mk_voted_against_majority']),
                process_rows_remove_resource('mk_voted_against_majority',
                                             process_voted_against_majority),
                load(data_path + 'votes/view_vote_rslts_hdr_approved/datapackage.json',
                     resources=['view_vote_rslts_hdr_approved']),
                process_rows_remove_resource('view_vote_rslts_hdr_approved',
                                             process_votes),
                get_aggregates,
                dump_to_path('data/people/mk_party_discipline_stats'),
                )


if __name__ == '__main__':
     flow().process()
