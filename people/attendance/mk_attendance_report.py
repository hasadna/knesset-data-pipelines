from datapackage_pipelines.wrapper import ingest, spew
import logging
from datapackage_pipelines.utilities.resources import PROP_STREAMING
from datetime import datetime


ATTENDANCE_FIELDS = [{'name': 'mk', 'type': 'string'},
                     {'name': 'factions', 'type': 'string'},
                     {'name': 'relevant_meetings', 'type': 'integer'},
                     {'name': 'attended_meetings', 'type': 'integer'},
                     {'name': 'attendance_percent', 'type': 'integer'},
                     {'name': 'attendance_percent_from_total', 'type': 'integer'}]


def is_relevant_meeting(meeting, plenum_assembly, knessetsdata, parameters):
    if not plenum_assembly:
        # no plenum assembly filtering
        # all meetings are filtered for the selected knesset num
        # taking into account pagra parameter
        if parameters['pagra'] == 'include':
            # pagra should be included - so all meetings are relevant
            return True
        else:
            # find out if meeting was during pagra or not
            last_assembly_finish = None
            pagra = False
            for plenum_assembly in sorted(knessetsdata['plenum_assemblies'].values(),
                                          key=lambda kd: (kd['Plenum'], kd['Assembly'])):
                if last_assembly_finish:
                    if last_assembly_finish <= meeting['StartDate'] <= plenum_assembly['PlenumStart']:
                        pagra = True
                        break
                last_assembly_finish = plenum_assembly['PlenumFinish']
            if parameters['pagra'] == 'only':
                return pagra
            elif parameters['pagra'] == 'exclude':
                return not pagra
            else:
                raise Exception('invalid pagra parameter: {}'.format(parameters['pagra']))
    else:
        plenum_assembly = knessetsdata['plenum_assemblies'][plenum_assembly]
        return plenum_assembly['PlenumStart'] <= meeting['StartDate'] <= plenum_assembly['PlenumFinish']


def is_relevant_meeting_for_mk(meeting, mk):
    return any((position["start_date"] <= meeting['StartDate'] <= position["finish_date"]
                for position in mk['positions']))


def is_attended_meeting(meeting, mk, parameters):
    if parameters.get('plenum-session-voters'):
        return mk['mk_individual_id'] in meeting['voter_mk_ids']
    else:
        return mk['mk_individual_id'] in meeting['attended_mk_individual_ids']


def get_security_attendance_knesset_20_until_sep_2017(resource, knessetsdata):
    knessetsdata['shakuf_security_knesset_20_until_sep_2017'] = []
    for row in resource:
        yield row
        knessetsdata['shakuf_security_knesset_20_until_sep_2017'].append(row)


def get_knessetsdata(resource, knessetsdata, parameters):
    knessetsdata.update(**{'current_knesset_num': None,
                           'prev_knesset_last_date': None,
                           'next_knesset_first_date': None,
                           'plenum_assemblies': {}})
    for knessetdate in resource:
        yield knessetdate
        if knessetdate.get('IsCurrent'):
            assert (knessetsdata['current_knesset_num'] is None
                    or knessetsdata['current_knesset_num'] == knessetdate['KnessetNum'])
            knessetsdata['current_knesset_num'] = knessetdate['KnessetNum']
        if knessetdate.get('KnessetNum') == parameters['KnessetNum']:
            knessetsdata['plenum_assemblies'][
                '{}-{}'.format(knessetdate['Plenum'], knessetdate['Assembly'])] = knessetdate
        elif knessetdate.get('KnessetNum') == parameters['KnessetNum'] - 1:
            if (knessetsdata['prev_knesset_last_date'] is None
                    or knessetsdata['prev_knesset_last_date'] < knessetdate['PlenumFinish']):
                knessetsdata['prev_knesset_last_date'] = knessetdate['PlenumFinish']
        elif knessetdate.get('KnessetNum') == parameters['KnessetNum'] + 1:
            if (knessetsdata['next_knesset_first_date'] is None
                    or knessetsdata['next_knesset_first_date'] > knessetdate['PlenumStart']):
                knessetsdata['next_knesset_first_date'] = knessetdate['PlenumStart']


def get_mks(resource, knessetsdata, parameters):
    knessetsdata['mks'] = []
    for mk_individual in resource:
        yield mk_individual
        mk = {'name': '{} {}'.format(mk_individual['mk_individual_first_name'],
                                     mk_individual['mk_individual_name']),
              'relevant_meetings': 0,
              'attended_meetings': 0,
              'positions': [],
              'mk_individual_id': mk_individual['mk_individual_id'],
              'factions': set()}
        for position in mk_individual['positions']:
            if position["position_id"] == 54 and position.get('KnessetNum') == parameters['KnessetNum']:
                start_date = datetime.strptime(position["start_date"], "%Y-%m-%d %H:%M:%S")
                if position.get('finish_date'):
                    finish_date = datetime.strptime(position["finish_date"], "%Y-%m-%d %H:%M:%S")
                else:
                    finish_date = datetime.now()
                mk['positions'].append({'start_date': start_date, 'finish_date': finish_date})
                if len(position['FactionName']) > 1:
                    mk['factions'].add(position['FactionName'])
        mk['factions'] = ', '.join(mk['factions'])
        if len(mk['positions']) > 0:
            knessetsdata['mks'].append(mk)
            # logging.info('relevant mk --- {}: {} positions'.format(mk['name'], len(mk['positions'])))
            # stats['relevant_mks'] += 1

def get_shakuf_security(mks, knessetsdata):
    knessetsdata['shakuf_security_committees'] = set()
    # invalid_shakuf_security_committees = set()
    for row in knessetsdata['shakuf_security_knesset_20_until_sep_2017']:
        committee_name = row['שם הוועדה']
        if committee_name == 'ועדת המשנה למוכנות ולביטחון שוטף':
            committee_name = 'ועדת המשנה לכוננות ולביטחון שוטף'
        elif committee_name == 'הוועדה המשותפת לתקציב הביטחון':
            committee_name = 'הוועדה המשותפת לוועדת החוץ והביטחון ולוועדת הכספים לתקציב הביטחון'
        mk_name = row['שם מלא']
        if mk_name == 'אבי דיכטר':
            mk_name = 'אבי (משה) דיכטר'
        elif mk_name == "שלי יחימוביץ'":
            mk_name = "שלי יחימוביץ" + '`'
        elif mk_name == 'איל בן ראובן':
            mk_name = 'איל בן-ראובן'
        elif mk_name == 'יואב בן צור':
            mk_name = 'יואב בן-צור'
        elif mk_name == 'מירב בן ארי':
            mk_name = 'מירב  בן-ארי'
        elif mk_name == "עיסאווי פריג'":
            mk_name = "עיסאווי פריג" + '`'
        if mk_name:
            try:
                num_attended_meetings = int(row['נוכחות במספר דיונים'])
                num_missed_meetings = int(row['כמה ישיבות החסיר?'])
                knessetsdata['shakuf_security_committees'].add(committee_name)
            except Exception:
                # invalid_shakuf_security_committees.add(committee_name)
                num_attended_meetings, num_missed_meetings = None, None
            if num_attended_meetings is not None and num_missed_meetings is not None:
                found_mk = False
                for mk in mks:
                    if mk['name'] == mk_name:
                        mk['relevant_meetings'] += num_attended_meetings + num_missed_meetings
                        mk['attended_meetings'] += num_attended_meetings
                        found_mk = True
                        break
                if not found_mk:
                    logging.info('failed to find matching mk "{}"'.format(mk_name))
    # logging.info('shakuf_security_committees={}'.format(shakuf_security_committees))
    # logging.info('invalid_shakuf_security_committees={}'.format(invalid_shakuf_security_committees))


def get_meetings(resource, knessetsdata, parameters, stats):
    if parameters.get('with-shakuf-security'):
        get_shakuf_security(knessetsdata['mks'], knessetsdata)
    stats.update(**{parameters['name'] + ': total meetings': 0,
                    parameters['name'] + ': relevant meetings': 0,
                    parameters['name'] + ': relevant meetings for mks': 0})
    for meeting in resource:
        yield meeting
        if parameters.get('with-shakuf-security') and meeting['committee_name'] in knessetsdata['shakuf_security_committees']:
            continue
        if parameters.get('max-year') and meeting['StartDate'].year > parameters['max-year']:
            continue
        if parameters.get('max-month') and meeting['StartDate'].month > parameters['max-month']:
            continue
        if parameters.get('plenum-session-voters') and not meeting['voter_mk_ids']:
            continue
        if not parameters.get('plenum-session-voters') and not meeting['parts_parsed_filename']:
            continue
        if meeting['KnessetNum'] == parameters['KnessetNum']:
            stats[parameters['name'] + ': total meetings'] += 1
            if is_relevant_meeting(meeting, parameters.get('Plenum-Assembly'), knessetsdata, parameters):
                stats[parameters['name'] + ': relevant meetings'] += 1
                is_meeting_relevant_for_mks = False
                for mk in knessetsdata['mks']:
                    if is_relevant_meeting_for_mk(meeting, mk):
                        is_meeting_relevant_for_mks = True
                        mk['relevant_meetings'] += 1
                        if is_attended_meeting(meeting, mk, parameters):
                            mk['attended_meetings'] += 1
                if is_meeting_relevant_for_mks:
                    stats[parameters['name'] + ': relevant meetings for mks'] += 1


def get_mks_attendance(knessetsdata):
    relevant_mks = []
    max_percent = 0
    min_percent = 100
    for mk in knessetsdata['mks']:
        if mk['relevant_meetings'] > 0:
            mk = {'mk': mk['name'], 'factions': mk['factions'],
                  'relevant_meetings': mk['relevant_meetings'],
                  'attended_meetings': mk['attended_meetings'],}
            relevant_mks.append(mk)
            attendance_percent = int(mk['attended_meetings'] / mk['relevant_meetings'] * 100)
            if attendance_percent > max_percent:
                max_percent = attendance_percent
            elif attendance_percent < min_percent:
                min_percent = attendance_percent
            mk['attendance_percent'] = attendance_percent
    for mk in relevant_mks:
        relative_percent = int((mk['attendance_percent'] - min_percent)
                               / (max_percent - min_percent)
                               * 100)
        if mk['attended_meetings'] > 0 and relative_percent == 0:
            relative_percent = 1
        mk['attendance_percent_from_total'] = relative_percent
        yield mk


def get_resources(datapackage, resources, parameters, stats):
    knessetsdata = {}
    for descriptor, resource in zip(datapackage['resources'], resources):
        if descriptor['name'] == 'security-attendance-knesset-20-until-sep-2017':
            yield get_security_attendance_knesset_20_until_sep_2017(resource, knessetsdata)
        elif descriptor['name'] == 'kns_knessetdates':
            yield get_knessetsdata(resource, knessetsdata, parameters)
        elif descriptor['name'] == 'mk_individual_positions':
            yield get_mks(resource, knessetsdata, parameters)
        elif descriptor['name'] == 'kns_committeesession' or descriptor['name'] == 'kns_plenumsession':
            yield get_meetings(resource, knessetsdata, parameters, stats)
        else:
            yield resource
    yield get_mks_attendance(knessetsdata)


def get_datapackage(datapackage, parameters, stats):
    datapackage['resources'].append({PROP_STREAMING: True,
                                     'name': parameters['name'],
                                     'path': parameters['name'] + '.csv',
                                     'schema': {'fields': ATTENDANCE_FIELDS}})
    return datapackage


def main():
    parameters, datapackage, resources, stats = ingest() + ({},)
    spew(get_datapackage(datapackage, parameters, stats),
         get_resources(datapackage, resources, parameters, stats),
         stats)


if __name__ == '__main__':
    main()
