from dataflows import Flow, load, dump_to_path
import os
import datetime
import re
from datapackage_pipelines_knesset.common_flow import (rows_counter,
                                                       process_rows_modify_descriptor,
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

    def process_session_voters(rows):
        for row in rows_counter('session_voters', rows):
            session_voted_mk_ids[row['PlenumSessionID']] = row['voter_mk_ids']

    def get_session_voted_mk_ids(session_id):
        attended_mk_ids = session_voted_mk_ids.get(session_id)
        return attended_mk_ids if attended_mk_ids else []

    def process_kns_plenumsession(sessions):
        num_yielded_rows = 0
        for num_sessions, session in enumerate(rows_counter('kns_plenumsession', sessions), start=1):
            session_date = get_plenum_session_start_date(session)
            attended_mk_ids = get_session_voted_mk_ids(session['PlenumSessionID'])
            for mk_id, faction_id in get_mk_faction_ids(all_mk_ids,
                                                        mk_individual_factions,
                                                        session_date):
                knessetdate = get_knessetdate(kns_knessetdates_sorted, session_date)
                yield {'PlenumSessionID': session['PlenumSessionID'],
                       'mk_individual_id': mk_id,
                       'faction_id': faction_id,
                       'attended': int(mk_id in attended_mk_ids),
                       'knesset': knessetdate['knesset'],
                       'plenum': knessetdate['plenum'],
                       'assembly': knessetdate['assembly'],
                       'pagra': int(knessetdate['pagra'])}
                num_yielded_rows += 1
        print('yielded {} plenum session voters stats rows'.format(num_yielded_rows))

    def modify_kns_plenumsession_descriptor(descriptor):
        descriptor.update(name='plenum_session_voters_stats',
                          path='plenum_session_voters_stats.csv',
                          schema={'fields': [{'name': 'PlenumSessionID', 'type': 'integer'},
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
                load(data_path + 'people/plenum/session_voters/datapackage.json',
                     resources=['kns_plenumsession']),
                process_rows_remove_resource('kns_plenumsession',
                                             process_session_voters),
                load(data_path + 'plenum/kns_plenumsession/datapackage.json',
                     resources=['kns_plenumsession']),
                process_rows_modify_descriptor('kns_plenumsession',
                                               process_kns_plenumsession,
                                               modify_kns_plenumsession_descriptor),
                dump_to_path('data/people/plenum/session_voters_stats'),
                )


if __name__ == '__main__':
     flow().process()
