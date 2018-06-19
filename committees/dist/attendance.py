from datapackage_pipelines.wrapper import ingest, spew
import logging


parameters, datapackage, resources = ingest()
aggregations = {"committees": {},
                "stats": {}}


all_committees, attendees_descriptor, attendees_resource = {}, None, None
for descriptor, resource in zip(datapackage["resources"], resources):
    if descriptor["name"] == "kns_committee":
        for committee in resource:
            all_committees[int(committee["CommitteeID"])] = committee
    elif descriptor["name"] == "committee-meeting-attendees":
        attendees_resource = resource
        attendees_descriptor = descriptor
        attendees_descriptor["schema"]["fields"].append({"name": "committee_name", "type": "string"})
    else:
        raise Exception()


def get_attendance_resource(resource):
    for row in resource:
        committee_id = int(row["committee_id"])
        row["committee_name"] = all_committees[committee_id]["Name"]
        yield row


spew(dict(datapackage, resources=[attendees_descriptor]),
     [get_attendance_resource(attendees_resource)],
     aggregations["stats"])
