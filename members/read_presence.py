from datapackage_pipelines.wrapper import ingest, spew
from datapackage_pipelines.utilities.resources import PROP_STREAMING
import datetime, requests


parameters, datapackage, resources = ingest()
aggregations = {"stats": {}}


resources_list = list(resources)
mk_individual = {row["mk_individual_id"]: row for row in resources_list[0]}
site_id_to_kns_id = {row["SiteId"]: row["KnsID"] for row in resources_list[1]}


def flush_day(current_day):
    mk_ids_hours = current_day.get("mk_ids_hours", {})
    for mk_id, hours in mk_ids_hours.items():
        if mk_id not in mk_individual:
            mk_id = site_id_to_kns_id.get(mk_id)
        assert mk_id in mk_individual, f"mk_id {mk_id} not found"
        yield {"mk_id": mk_id,
               "mk_name": mk_individual[mk_id]["mk_individual_first_name"] + " " + mk_individual[mk_id]["mk_individual_name"],
               "date": datetime.date(current_day["year"], current_day["month"], current_day["day"]),
               "year": current_day["year"],
               "month": current_day["month"],
               "day": current_day["day"],
               "year_week_number": ((datetime.date(current_day["year"], current_day["month"], current_day["day"]) - datetime.date(current_day["year"], 1, 1)).days // 7) + 1,
               "total_attended_hours": len(hours)}


def get_presence_lines():
    for line in requests.get(parameters["presence-oknesset-url"], stream=True).iter_lines(decode_unicode=True):
        yield line
    with open(parameters['presence-path']) as f:
        for line in f:
            yield line


def get_presence_resource():
    current_day = {}
    for line in get_presence_lines():
        line = [field.strip() for field in line.split(",") if field and len(field.strip()) > 0]
        dt = datetime.datetime.strptime(line.pop(0), '%Y-%m-%d %H:%M:%S')
        if current_day.get("year") != dt.year or current_day.get("month") != dt.month or current_day.get("day") != dt.day:
            # new day - flush previous day
            yield from flush_day(current_day)
            # reset current_day
            current_day.update(year=dt.year, month=dt.month, day=dt.day, mk_ids_hours={})
        for mk_id in map(int, line):
            current_day["mk_ids_hours"].setdefault(mk_id, {})[dt.hour] = True
    # flush the last current_day
    yield from flush_day(current_day)


datapackage["resources"] = [{PROP_STREAMING: True,
                             "name": "presence",
                             "path": "presence.csv",
                             "schema": {"fields": [{"name": "mk_id", "type": "integer"},
                                                   {"name": "mk_name", "type": "string"},
                                                   {"name": "date", "type": "date"},
                                                   {"name": "year", "type": "integer"},
                                                   {"name": "month", "type": "integer"},
                                                   {"name": "day", "type": "integer"},
                                                   {"name": "year_week_number", "type": "integer"},
                                                   {"name": "total_attended_hours", "type": "integer"}]}}]


spew(datapackage, [get_presence_resource()], aggregations["stats"])
