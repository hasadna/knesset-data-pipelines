from dataflows import PackageWrapper
from datapackage import Package
import datetime


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
    last_knessetdate = None
    for knessetdate in kns_knessetdates_sorted:
        if event_date <= knessetdate['finish_date']:
            return dict(knessetdate, pagra=False)
        elif event_date < knessetdate['start_date']:
            return dict(last_knessetdate, pagra=True) if last_knessetdate else dict(knessetdate, pagra=True)
        last_knessetdate = knessetdate
    return dict(last_knessetdate, pagra=True)


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


def get_mk_faction(mk_individual_factions, mk_id, event_date):
    rows = mk_individual_factions.get(mk_id)
    if rows:
        for start_date, finish_date, faction_id in rows:
            if start_date <= event_date <= finish_date:
                return faction_id
    return None


def get_mk_faction_ids(all_mk_ids, mk_individual_factions, event_date):
    for mk_id in all_mk_ids:
        faction_id = get_mk_faction(mk_individual_factions, mk_id, event_date)
        if faction_id:
            yield mk_id, faction_id
