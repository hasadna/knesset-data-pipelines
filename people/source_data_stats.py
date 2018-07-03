from datapackage_pipelines.wrapper import ingest, spew
import logging, yaml, json


parameters, datapackage, resources, stats = ingest() + ({},)


def incr_stat(k):
    stats.setdefault(k, 0)
    stats[k] += 1


def get_mk_individual_resource(resource):
    for mk_individual in resource:
        incr_stat('mk individuals')
        logging.info(mk_individual)
        yield mk_individual


def get_committee_session_resource(resource):
    stats.update(**{'committee sessions': 0})
    for committee_session in resource:
        incr_stat('committee sessions')
        incr_stat('committee sessions KnessetNum = {}'.format(committee_session['KnessetNum']))
        if committee_session['parts_parsed_filename']:
            incr_stat('committee sessions with parts_parsed_filename')
        if committee_session['text_parsed_filename']:
            incr_stat('committee sessions with text_parsed_filename')
        yield committee_session


def get_resources():
    for descriptor, resource in zip(datapackage['resources'], resources):
        if descriptor['name'] == 'mk_individual':
            yield get_mk_individual_resource(resource)
        elif descriptor['name'] == 'kns_committeesession':
            yield get_committee_session_resource(resource)
        else:
            yield resource


spew(datapackage, get_resources(), stats)
