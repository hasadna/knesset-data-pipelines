from dataflows import Flow, load, dump_to_path, PackageWrapper
import os
import datetime
import re
from collections import defaultdict
from datapackage_pipelines_knesset.common_flow import (rows_counter,
                                                       process_rows_remove_resource,
                                                       kns_knessetdates_processor,
                                                       get_knessetdate,
                                                       mk_individual_factions_processor,
                                                       mk_individual_names_processor,
                                                       get_mk_faction_ids)


def get_plenum_session_start_date(plenum_session):
    start_date = plenum_session['StartDate'].date()
    if start_date < datetime.date(1947, 1, 1):
        m = re.findall('([0-9]+)/([0-9]+)/([0-9]+)', plenum_session['Name'])
        assert m, 'failed to find date for session {}'.format(plenum_session)
        assert len(m) == 1
        start_date = datetime.date(*map(int, reversed(m[0])))
    return start_date


def flow():
    data_path = 'data{}/'.format('_samples' if os.environ.get('KNESSET_DATA_SAMPLES') else '')
    kns_knessetdates_sorted = []
    mk_individual_factions = {}
    all_mk_ids = set()
    session_voted_mk_ids = {}
    aggregates = {}

    def process_session_voters(rows):
        for row in rows_counter('session_voters', rows):
            session_voted_mk_ids[row['PlenumSessionID']] = row['voter_mk_ids']

    def get_session_voted_mk_ids(session_id):
        attended_mk_ids = session_voted_mk_ids.get(session_id)
        return attended_mk_ids if attended_mk_ids else []

    def process_kns_plenumsession(sessions):
        for session in rows_counter('kns_plenumsession', sessions):
            session_date = get_plenum_session_start_date(session)
            voted_mk_ids = get_session_voted_mk_ids(session['PlenumSessionID'])
            for mk_id, faction_id in get_mk_faction_ids(all_mk_ids, mk_individual_factions,
                                                        session_date):
                knessetdate = get_knessetdate(kns_knessetdates_sorted, session_date)
                agg = aggregates.setdefault(knessetdate['knesset'], {})\
                                .setdefault(knessetdate['plenum'], {})\
                                .setdefault(knessetdate['assembly'], {})\
                                .setdefault(knessetdate['pagra'], {})\
                                .setdefault(faction_id, {})\
                                .setdefault(mk_id, defaultdict(int))
                if mk_id in voted_mk_ids:
                    agg['voted_sessions'] += 1
                agg['total_sessions'] += 1

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
            if agg.get('total_sessions', 0) > 0:
                knesset, plenum, assembly, pagra, faction_id, mk_id = agg_key
                yield dict({'voted_sessions': 0,
                            'total_sessions': 0,
                            'voted_sessions_percent': 0, },
                           **agg, knesset=knesset, plenum=plenum, assembly=assembly,
                           pagra=int(pagra), faction_id=faction_id, mk_id=mk_id)

    def get_aggregates(package: PackageWrapper):
        schema_fields = [{'name': 'knesset', 'type': 'integer'},
                         {'name': 'plenum', 'type': 'integer'},
                         {'name': 'assembly', 'type': 'integer'},
                         {'name': 'pagra', 'type': 'integer'},
                         {'name': 'faction_id', 'type': 'integer'},
                         {'name': 'mk_id', 'type': 'integer'},
                         {'name': 'voted_sessions', 'type': 'integer'},
                         {'name': 'total_sessions', 'type': 'integer'},
                         {'name': 'voted_sessions_percent', 'type': 'integer'},]
        package.pkg.add_resource({'name': 'plenum_session_voters_stats',
                                  'path': 'plenum_session_voters_stats.csv',
                                  'schema': {'fields': schema_fields}})
        yield package.pkg
        yield from package
        min_voted_sessions_percent = 100
        max_voted_sessions_percent = 0
        for agg_key, agg in get_all_aggregates():
            total_sessions = agg.get('total_sessions', 0)
            if total_sessions > 0:
                voted_sessions_percent = int(agg.get('voted_sessions', 0)
                                             / total_sessions * 100)
                agg['voted_sessions_percent'] = voted_sessions_percent
                if voted_sessions_percent < min_voted_sessions_percent:
                    min_voted_sessions_percent = voted_sessions_percent
                elif voted_sessions_percent > max_voted_sessions_percent:
                    max_voted_sessions_percent = voted_sessions_percent
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
                load(data_path + 'people/plenum/session_voters/datapackage.json',
                     resources=['kns_plenumsession']),
                process_rows_remove_resource('kns_plenumsession',
                                             process_session_voters),
                load(data_path + 'plenum/kns_plenumsession/datapackage.json',
                     resources=['kns_plenumsession']),
                process_rows_remove_resource('kns_plenumsession',
                                               process_kns_plenumsession),
                get_aggregates,
                dump_to_path('data/people/plenum/session_voters_stats'),
                )


if __name__ == '__main__':
     flow().process()
