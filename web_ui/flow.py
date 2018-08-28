from dataflows import Flow, load, cache, PackageWrapper, ResourceWrapper
from collections import defaultdict
from traceback import print_exc
import sys


def update_meetings(package: PackageWrapper):
    yield package.pkg

    committees = {}
    mk_individuals = {}

    def update_meeting(meeting):
        try:
            speech_parts_list = list(get_speech_parts(meeting))
        except Exception as e:
            print_exc()
            print("failed to get speech parts for meeting {}".format(meeting["CommitteeSessionID"]),
                  sys.stderr)
            speech_parts_list = []

    print('loading...')
    load_stats = defaultdict(int)
    resource: ResourceWrapper
    for resource in package:
        if resource.res.name == 'kns_committee':
            for row in resource:
                committees[str(row['CommitteeID'])] = row
                load_stats['committees'] += 1
        elif resource.res.name == 'mk_individual_positions':
            for row in resource:
                mk_individuals[str(row['mk_individual_id'])] = row
                load_stats['mk_individuals'] += 1
        elif resource.res.name == 'kns_committeesession':
            for row in resource:
                update_meeting(row)
        yield resource
    print(load_stats)


def flow():
    load_steps = (load('data/committees/kns_committee/datapackage.json',
                       resources=['kns_committee']),
                  load('data/members/mk_individual/datapackage.json',
                       resources=['mk_individual_positions']),
                  load('data/people/committees/meeting-attendees/datapackage.json',
                       resources=['kns_committeesession']))
    load_steps = (cache(load_steps, cache_path='.cache/web_ui/meetings_load_steps'))
    return Flow(*load_steps + (update_meetings,))


if __name__ == '__main__':
     flow().process()
