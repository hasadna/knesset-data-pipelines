import datetime


def get_mk_faction(mk_factions, event_datetime):
    for faction_id, start_date, finish_date in [(f['faction_id'], f['start_date'], f['finish_date'])
                                                for f in mk_factions]:
        if not finish_date:
            finish_date = datetime.date.today()
        start_date = datetime.datetime.combine(start_date, datetime.time())
        finish_date = datetime.datetime.combine(finish_date, datetime.time())
        start_date = start_date - datetime.timedelta(days=2)
        finish_date = finish_date + datetime.timedelta(days=2)
        if start_date <= event_datetime <= finish_date:
            return faction_id
    return None
