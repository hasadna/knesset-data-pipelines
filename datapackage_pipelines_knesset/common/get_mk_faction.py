import datetime


def get_mk_faction(mk_factions, event_datetime):
    for faction_id, start_date, finish_date in [(f['faction_id'], f['start_date'], f['finish_date'])
                                                for f in mk_factions]:
        start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d %H:%M:%S')
        finish_date = datetime.datetime.strptime(finish_date, '%Y-%m-%d %H:%M:%S') if finish_date else datetime.datetime.now()
        start_date = start_date - datetime.timedelta(days=2)
        finish_date = finish_date + datetime.timedelta(days=2)
        if start_date <= event_datetime <= finish_date:
            return faction_id
    return None
