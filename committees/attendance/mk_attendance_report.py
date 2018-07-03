from datapackage_pipelines.wrapper import ingest, spew
import logging
from datapackage_pipelines.utilities.resources import PROP_STREAMING
from datetime import datetime


def is_relevant_meeting(meeting, mk):
    return any((position["start_date"] <= meeting['StartDate'] and position["finish_date"] >= meeting['StartDate']
                for position in mk['positions']))


def is_attended_meeting(meeting, mk):
    return mk['mk_individual_id'] in meeting['attended_mk_individual_ids']


parameters, datapackage, resources, stats = ingest() + ({'relevant_mks': 0, 'relevant_meetings': 0},)


def get_resource():
    mks = []
    for mk_individual in next(resources):
        mk = {'name': '{} {}'.format(mk_individual['mk_individual_first_name'], mk_individual['mk_individual_name']),
              'relevant_meetings': 0, 'attended_meetings': 0, 'positions': [],
              'mk_individual_id': mk_individual['mk_individual_id']}
        for position in mk_individual['positions']:
            if position["position_id"] == 54:
                start_date = datetime.strptime(position["start_date"], "%Y-%m-%d %H:%M:%S")
                finish_date = datetime.strptime(position["finish_date"], "%Y-%m-%d %H:%M:%S") if position.get('finish_date') else datetime.now()
                if start_date >= datetime(2014, 1, 1):
                    mk['positions'].append({'start_date': start_date, 'finish_date': finish_date})
        if len(mk['positions']) > 0:
            mks.append(mk)
            logging.info('{}: {} positions'.format(mk['name'], len(mk['positions'])))
            stats['relevant_mks'] += 1
    logging.info(stats)
    for meeting in next(resources):
        if meeting['parts_parsed_filename'] and meeting['KnessetNum'] == 20:
            stats['relevant_meetings'] += 1
            for mk in mks:
                if is_relevant_meeting(meeting, mk):
                    mk['relevant_meetings'] += 1
                    if is_attended_meeting(meeting, mk):
                        mk['attended_meetings'] += 1
    for mk in mks:
        if mk['relevant_meetings'] > 0:
            yield {'mk': mk['name'], 'relevant_meetings': mk['relevant_meetings'], 'attended_meetings': mk['attended_meetings']}


datapackage['resources'] = [{PROP_STREAMING: True, 'name': 'attendance_report', 'path': 'attendance_report.csv',
                             'schema': {'fields': [{'name': 'mk', 'type': 'string'},
                                                   {'name': 'relevant_meetings', 'type': 'integer'},
                                                   {'name': 'attended_meetings', 'type': 'integer'}]}}]


spew(datapackage, [get_resource()], stats)
