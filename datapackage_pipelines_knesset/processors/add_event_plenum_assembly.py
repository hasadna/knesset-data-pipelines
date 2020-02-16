from datapackage_pipelines.wrapper import process
import datetime, logging


kns_knessetdates = []


def process_row(row, row_index, spec, resource_index, parameters, stats):
    if spec['name'] == 'kns_knessetdates':
        kns_knessetdates.append((row['KnessetNum'], row['Assembly'], row['Plenum'],
                                 row['PlenumStart'], row['PlenumFinish']))
    elif spec['name'] == parameters['resource']:
        if row_index == 0:
            for i, v in enumerate(sorted(kns_knessetdates, key=lambda k: k[3])):
                kns_knessetdates[i] = v
        event_date = parameters.get('event-date')
        event_time = parameters.get('event-time')
        event_datetime = parameters.get('event-datetime')
        try:
            if event_date and event_time:
                event_date = row[event_date]
                if isinstance(event_date, datetime.datetime):
                    event_date = event_date.date()
                event_datetime = '{} {}'.format(event_date,
                                                row[event_time] if row[event_time] else '00:00')
                event_datetime = datetime.datetime.strptime(event_datetime, "%Y-%m-%d %H:%M")
            elif event_datetime:
                event_datetime = datetime.datetime.strptime(row[event_datetime], "%Y-%m-%d %H:%M:%S")
            assert event_datetime
        except Exception:
            logging.info(spec)
            logging.info(row)
            raise
        knesset_field = parameters.get('knesset', 'knesset')
        plenum_field = parameters.get('plenum', 'plenum')
        assembly_field = parameters.get('assembly', 'assembly')
        pagra_field = parameters.get('pagra', 'pagra')
        last_knesset, last_assembly, last_plenum = None, None, None
        updated = False
        for knesset, assembly, plenum, plenum_start, plenum_finish in kns_knessetdates:
            if event_datetime < plenum_start:
                updated = True
                if not pagra_field:
                    if plenum_field:
                        row[plenum_field] = plenum
                    if assembly_field:
                        row[assembly_field] = assembly
                    row[knesset_field] = knesset
                else:
                    if plenum_field:
                        row[plenum_field] = last_plenum
                    if assembly_field:
                        row[assembly_field] = last_assembly
                    row.update(**{knesset_field: last_knesset,
                                  pagra_field: True})
                break
            elif not plenum_finish or event_datetime <= plenum_finish:
                updated = True
                if assembly_field:
                    row[assembly_field] = assembly
                if plenum_field:
                    row[plenum_field] = plenum
                row[knesset_field] = knesset
                if pagra_field:
                    row[pagra_field] = False
                break
            last_knesset, last_assembly, last_plenum = knesset, assembly, plenum
        if not updated:
            logging.warning('failed to update plenum/assembly for event_datetime: {}'.format(event_datetime))
            if assembly_field:
                row[assembly_field] = ''
            if plenum_field:
                row[plenum_field] = ''
            if pagra_field:
                row[pagra_field] = ''
    return row


def modify_datapackage(datapackage, parameters, stats):
    for resource in datapackage['resources']:
        if resource['name'] == parameters['resource']:
            knesset_field = parameters.get('knesset', 'knesset')
            plenum_field = parameters.get('plenum', 'plenum')
            assembly_field = parameters.get('assembly', 'assembly')
            pagra_field = parameters.get('pagra', 'pagra')
            existing_fields = {field['name']: field for field in resource['schema']['fields']}
            for new_field_name in (knesset_field, plenum_field, assembly_field, pagra_field):
                if not new_field_name:
                    continue
                new_field_type = 'boolean' if new_field_name == pagra_field else 'integer'
                if new_field_name in existing_fields:
                    existing_fields[new_field_name]['type'] = new_field_type
                else:
                    resource['schema']['fields'].append({'name': new_field_name,
                                                         'type': new_field_type})
    return datapackage


if __name__ == '__main__':
    process(modify_datapackage, process_row)