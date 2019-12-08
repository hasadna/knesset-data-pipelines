from datapackage_pipelines.wrapper import ingest, spew
import logging
from collections import defaultdict


def modify_datapackage(datapackage):
    new_resources = []
    for resource in datapackage['resources']:
        if resource['name'] != 'kns_bill':
            if resource['name'] == 'kns_committeesession':
                resource['schema']['fields'] += [
                    {'name': 'bill_names', 'type': 'array'},
                    {'name': 'bill_types', 'type': 'array'},
                    {'name': 'related_to_legislation', 'type': 'boolean'}
                ]
            new_resources.append(resource)
    datapackage.update(resources=new_resources)
    return datapackage


def related_to_legislation(session):
    if len(session['bill_names']) > 0:
        return True
    else:
        if session['item_type_ids']:
            for item_type_id in session['item_type_ids']:
                if item_type_id in [6000, 6001, 6002, 6003]:
                    return True
        topics = session.get('topics') or []
        topics = ' ' + ' '.join(topics + [session.get('Note') or '']) + ' '
        for keyword in [
            'חוק',
            'תקנות',
            'צו'
        ]:
            if ' '+keyword+' ' in topics:
                return True
    return False


def process_sessions(rows, bills, stats):
    for row in rows:
        bill_names = set()
        bill_types = set()
        if row['item_type_ids'] and row['item_ids'] and len(row['item_type_ids']) == len(row['item_ids']):
            for i, item_type_id in enumerate(row['item_type_ids']):
                if item_type_id == 2:
                    item_id = row['item_ids'][i]
                    bill_name, bill_type = bills.get(item_id, (None, None))
                    bill_names.add(bill_name)
                    bill_types.add(bill_type)
        row['bill_names'] = list(bill_names)
        row['bill_types'] = list(bill_types)
        row['related_to_legislation'] = related_to_legislation(row)
        if row['related_to_legislation']:
            stats['num_sessions_related_to_legislation'] += 1
        else:
            stats['num_sessions_not_related_to_legislation'] += 1
        yield row


def process_bills(rows, bills, stats):
    for row in rows:
        bills[row['BillID']] = (row['Name'], row['SubTypeDesc'])
        stats['num_bills'] += 1


def process_resources(resources, stats):
    bills = {}
    for resource_num, resource in enumerate(resources):
        if resource_num == 0:
            process_bills(resource, bills, stats)
        elif resource_num == 1:
            yield process_sessions(resource, bills, stats)
        else:
            yield (row for row in resource)


if __name__ == '__main__':
    parameters, datapackage, resource_iterator = ingest()
    stats = defaultdict(int)
    modify_datapackage(datapackage)
    spew(datapackage, process_resources(resource_iterator, stats), stats)
