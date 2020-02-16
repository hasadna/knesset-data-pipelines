from datapackage import Package
import datetime
import os
import logging


try:
    from dataflows import PackageWrapper, load, Flow, cache
except Exception:
    pass


def load_knesset_data(path, use_data=False, **kwargs):
    return load(get_knesset_data_url_or_path(path, use_data), **kwargs)


def get_knesset_data_url_or_path(path, use_data=False):
    if os.environ.get('KNESSET_PIPELINES_DATA_PATH') and use_data:
        url = os.path.join(os.environ['KNESSET_PIPELINES_DATA_PATH'], path)
        logging.info('loading from data path: {}'.format(url))
    else:
        url = 'https://storage.googleapis.com/knesset-data-pipelines/data/' + path
        logging.info('loading from url: {}'.format(url))
    return url


def rows_counter(title, rows, count_every=10000):
    first_print = True
    i = 0
    for i, row in enumerate(rows, start=1):
        yield row
        if i % count_every == 0:
            if first_print:
                first_print = False
                print('-- ' + title + ' --')
            print('processed {} rows'.format(i))
    if first_print:
        print('-- ' + title + ' --')
        print('processed {} rows'.format(i))
    elif i % count_every != 0:
        print('processed {} rows'.format(i))


def process_rows_remove_resource(resource_name, process_rows_func):

    def step(package: PackageWrapper):
        resource_names = [resource.name for resource in package.pkg.resources]
        package.pkg.remove_resource(resource_name)
        yield package.pkg
        processed_rows = False
        for name, rows in zip(resource_names, package):
            if name == resource_name:
                process_rows_func(rows)
                processed_rows = True
            else:
                yield rows
        assert processed_rows, 'did not process rows for resource {}'.format(resource_name)

    return step


def process_rows_modify_descriptor(resource_name, process_rows_func, modify_descriptor_func):

    def step(package: PackageWrapper):
        resource_names = [resource.name for resource in package.pkg.resources]
        modify_descriptor_func(package.pkg.descriptor['resources'][resource_names.index(resource_name)])
        yield Package(package.pkg.descriptor)
        for name, rows in zip(resource_names, package):
            yield process_rows_func(rows) if name == resource_name else rows

    return step


def kns_knessetdates_processor(kns_knessetdates_sorted):

    def processor(rows):
        for knessetdate in sorted(rows_counter('kns_knessetdates', rows),
                                  key=lambda row: row['PlenumStart']):
            finish_date = knessetdate['PlenumFinish']
            finish_date = finish_date.date() if finish_date else datetime.date.today()
            kns_knessetdates_sorted.append({'start_date': knessetdate['PlenumStart'].date(),
                                            'finish_date': finish_date,
                                            'knesset': knessetdate['KnessetNum'],
                                            'plenum': knessetdate['Plenum'],
                                            'assembly': knessetdate['Assembly']})

    return processor


def get_knessetdate(kns_knessetdates_sorted, event_date):
    # returns knessetdate object for given event date, including pagra attribute
    # if pagra is True - it means event occured at pagra after the returned knesset date
    for knessetdate in get_knessetdates_with_pagra(kns_knessetdates_sorted):
        if event_date <= knessetdate['finish_date']:
            return knessetdate
    logging.warning('failed to get knessetdate for event_date: {}'.format(event_date))
    return None


def get_knessetdates_with_pagra(kns_knessetdates_sorted):
    # returns all the knessetdates with pagra attribute
    # start and finish dates are inclusive
    # the pagra is after the knesset date
    last_knessetdate = None
    for knessetdate in kns_knessetdates_sorted:
        if last_knessetdate:
            yield dict(last_knessetdate,
                       start_date=last_knessetdate['finish_date'] + datetime.timedelta(days=1),
                       finish_date=knessetdate['start_date'] - datetime.timedelta(days=1),
                       pagra=True)
        yield dict(knessetdate, pagra=False)
        last_knessetdate = knessetdate


def mk_individual_factions_processor(mk_individual_factions):

    def processor(rows):
        for mk_faction in rows_counter('mk_individual_factions', rows):
            mk_rows_list = mk_individual_factions.setdefault(mk_faction['mk_individual_id'], [])
            start_date, finish_date = mk_faction['start_date'], mk_faction['finish_date']
            if not finish_date:
                finish_date = datetime.date.today()
            mk_rows_list.append((start_date, finish_date, mk_faction['faction_id']))

    return processor


def mk_individual_names_processor(all_mk_ids):

    def processor(rows):
        for mk_individual_name in rows_counter('mk_individual_names', rows):
            all_mk_ids.add(mk_individual_name['mk_individual_id'])

    return processor


def get_mk_faction(mk_individual_factions, mk_id, event_start_date, event_finish_date=None):
    rows = mk_individual_factions.get(mk_id)
    if rows:
        for faction_start_date, faction_finish_date, faction_id in rows:
            if event_finish_date:
                if faction_start_date <= event_start_date and event_finish_date <= faction_finish_date:
                    return faction_id
            elif faction_start_date <= event_start_date <= faction_finish_date:
                return faction_id
    return None


def get_mk_faction_ids(all_mk_ids, mk_individual_factions, event_start_date, event_finish_date=None):
    for mk_id in all_mk_ids:
        faction_id = get_mk_faction(mk_individual_factions, mk_id, event_start_date, event_finish_date)
        if faction_id:
            yield mk_id, faction_id


def load_member_names(cache_path='.cache/members-mk-individual-names', use_data=False):
    member_names = {}

    def _load_member_names(rows):
        for row in rows:
            member_names[row['mk_individual_id']] = row['names'][0]
            yield row

    load_step = load_knesset_data('members/mk_individual/datapackage.json', use_data=use_data, resources=['mk_individual_names'])
    Flow(
        load_step if use_data else cache(load_step, cache_path=cache_path),
        _load_member_names
    ).process()
    return member_names
