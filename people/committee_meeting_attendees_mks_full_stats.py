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
    all_mk_ids = set()
    session_attended_mk_ids = {}
    aggregates = {}

    def process_meeting_attendees(rows):
        for row in rows_counter('meeting_attendees', rows):
            session_attended_mk_ids[row['CommitteeSessionID']] = row['attended_mk_individual_ids']

    def get_session_attended_mk_ids(session_id):
        attended_mk_ids = session_attended_mk_ids.get(session_id)
        return attended_mk_ids if attended_mk_ids else []

    def process_kns_committeesession(sessions):
        for session in rows_counter('kns_committeesession', sessions):
            committee_id = session['CommitteeID']
            session_date = session['StartDate'].date()
            attended_mk_ids = get_session_attended_mk_ids(session['CommitteeSessionID'])
            for mk_id, faction_id in get_mk_faction_ids(all_mk_ids, mk_individual_factions,
                                                        session_date):
                knessetdate = get_knessetdate(kns_knessetdates_sorted, session_date)
                if not knessetdate:
                    continue
                agg = aggregates.setdefault(knessetdate['knesset'], {})\
                                .setdefault(knessetdate['plenum'], {})\
                                .setdefault(knessetdate['assembly'], {})\
                                .setdefault(knessetdate['pagra'], {})\
                                .setdefault(committee_id, {})\
                                .setdefault(faction_id, {})\
                                .setdefault(mk_id, defaultdict(int))
                if mk_id in attended_mk_ids:
                    agg['attended_meetings'] += 1
                if session['parts_parsed_filename']:
                    agg['protocol_meetings'] += 1
                if session['TypeDesc'] == 'פתוחה':
                    agg['open_meetings'] += 1

    def get_all_aggregates():
        for knesset, aggs in aggregates.items():
            for plenum, aggs in aggs.items():
                for assembly, aggs in aggs.items():
                    for pagra, aggs in aggs.items():
                        for committee_id, aggs in aggs.items():
                            for faction_id, aggs in aggs.items():
                                for mk_id, agg in aggs.items():
                                    yield (knesset, plenum, assembly, pagra,
                                           committee_id, faction_id, mk_id), agg

    def get_mk_aggregates():
        for agg_key, agg in get_all_aggregates():
            if agg.get('protocol_meetings', 0) > 0:
                knesset, plenum, assembly, pagra, committee_id, faction_id, mk_id = agg_key
                yield dict({'attended_meetings': 0,
                            'protocol_meetings': 0,
                            'open_meetings': 0,
                            'attended_meetings_percent': 0,
                            'attended_meetings_relative_percent': 0,},
                           **agg, knesset=knesset, plenum=plenum, assembly=assembly,
                           pagra=int(pagra), committee_id=committee_id, faction_id=faction_id,
                           mk_id=mk_id)

    def get_aggregates(package: PackageWrapper):
        schema_fields = [{'name': 'knesset', 'type': 'integer'},
                         {'name': 'plenum', 'type': 'integer'},
                         {'name': 'assembly', 'type': 'integer'},
                         {'name': 'pagra', 'type': 'integer'},
                         {'name': 'committee_id', 'type': 'integer'},
                         {'name': 'faction_id', 'type': 'integer'},
                         {'name': 'mk_id', 'type': 'integer'},
                         {'name': 'attended_meetings', 'type': 'integer'},
                         {'name': 'protocol_meetings', 'type': 'integer'},
                         {'name': 'open_meetings', 'type': 'integer'},
                         {'name': 'attended_meetings_percent', 'type': 'integer'},
                         {'name': 'attended_meetings_relative_percent', 'type': 'integer'},]
        package.pkg.add_resource({'name': 'meeting_attendees_mks_full_stats',
                                  'path': 'meeting_attendees_mks_full_stats.csv',
                                  'schema': {'fields': schema_fields}})
        yield package.pkg
        yield from package
        min_attended_meetings_percent = 100
        max_attended_meetings_percent = 0
        for agg_key, agg in get_all_aggregates():
            protocol_meetings = agg.get('protocol_meetings', 0)
            if protocol_meetings > 0:
                attended_meetings_percent = int(agg.get('attended_meetings', 0)
                                                / protocol_meetings * 100)
                agg['attended_meetings_percent'] = attended_meetings_percent
                if attended_meetings_percent < min_attended_meetings_percent:
                    min_attended_meetings_percent = attended_meetings_percent
                elif attended_meetings_percent > max_attended_meetings_percent:
                    max_attended_meetings_percent = attended_meetings_percent
        for agg_key, agg in get_all_aggregates():
            if agg.get('protocol_meetings', 0) > 0:
                attended_meetings_percent = agg.get('attended_meetings_percent', 0)
                relative_percent = int((attended_meetings_percent - min_attended_meetings_percent)
                                       / (max_attended_meetings_percent - min_attended_meetings_percent)
                                       * 100)
                agg['attended_meetings_relative_percent'] = relative_percent
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
                load(data_path + 'people/committees/meeting-attendees/datapackage.json',
                     resources=['kns_committeesession']),
                process_rows_remove_resource('kns_committeesession',
                                             process_meeting_attendees),
                load(data_path + 'committees/kns_committeesession/datapackage.json',
                     resources=['kns_committeesession']),
                process_rows_remove_resource('kns_committeesession',
                                             process_kns_committeesession),
                get_aggregates,
                dump_to_path('data/people/committees/meeting_attendees_mks_full_stats'),
                )


if __name__ == '__main__':
     flow().process()
