from dataflows import Flow, load, dump_to_path
import os
from datapackage_pipelines_knesset.common_flow import (rows_counter,
                                                       process_rows_modify_descriptor,
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

    def process_meeting_attendees(rows):
        for row in rows_counter('meeting_attendees', rows):
            session_attended_mk_ids[row['CommitteeSessionID']] = row['attended_mk_individual_ids']

    def get_session_attended_mk_ids(session_id):
        attended_mk_ids = session_attended_mk_ids.get(session_id)
        return attended_mk_ids if attended_mk_ids else []

    def process_kns_committeesession(sessions):
        num_yielded_rows = 0
        for num_sessions, session in enumerate(rows_counter('kns_committeesession', sessions), start=1):
            session_date = session['StartDate'].date()
            attended_mk_ids = get_session_attended_mk_ids(session['CommitteeSessionID'])
            for mk_id, faction_id in get_mk_faction_ids(all_mk_ids, mk_individual_factions,
                                                        session_date):
                knessetdate = get_knessetdate(kns_knessetdates_sorted, session_date)
                yield {'CommitteeSessionID': session['CommitteeSessionID'],
                       'CommitteeID': session['CommitteeID'],
                       'mk_individual_id': mk_id,
                       'faction_id': faction_id,
                       'attended': int(mk_id in attended_mk_ids),
                       'knesset': knessetdate['knesset'],
                       'plenum': knessetdate['plenum'],
                       'assembly': knessetdate['assembly'],
                       'pagra': int(knessetdate['pagra'])}
                num_yielded_rows += 1
        print('yielded {} meeting attendees mks full stats rows'.format(num_yielded_rows))

    def modify_kns_committeesession_descriptor(descriptor):
        descriptor.update(name='meeting_attendees_mks_full_stats',
                          path='meeting_attendees_mks_full_stats.csv',
                          schema={'fields': [{'name': 'CommitteeSessionID', 'type': 'integer'},
                                             {'name': 'CommitteeID', 'type': 'integer'},
                                             {'name': 'mk_individual_id', 'type': 'integer'},
                                             {'name': 'faction_id', 'type': 'integer'},
                                             {'name': 'attended', 'type': 'integer'},
                                             {'name': 'knesset', 'type': 'integer'},
                                             {'name': 'plenum', 'type': 'integer'},
                                             {'name': 'assembly', 'type': 'integer'},
                                             {'name': 'pagra', 'type': 'integer'},
                                             ]})

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
                process_rows_modify_descriptor('kns_committeesession',
                                               process_kns_committeesession,
                                               modify_kns_committeesession_descriptor),
                dump_to_path('data/people/committees/meeting_attendees_mks_full_stats'),
                )


if __name__ == '__main__':
     flow().process()
