from datapackage_pipelines.wrapper import ingest, spew


parameters, datapackage, resources = ingest()
aggs = {"stats": {}}


committees_metadata, meetings_topics, meetings_resource, meetings_descriptor = {}, {}, None, None
for descriptor, resource in zip(datapackage["resources"], resources):
    if descriptor["name"] == "kns_committee":
        for row in resource:
            committees_metadata[int(row["CommitteeID"])] = {"committee_name": row["Name"],
                                                            "committee_type": row["CommitteeTypeDesc"]}
    elif descriptor["name"] == "kns_cmtsessionitem":
        for row in resource:
            meetings_topics.setdefault(int(row["CommitteeSessionID"]), []).append(row["Name"])
    elif descriptor["name"] == "kns_committeesession":
        meetings_resource = resource
        meetings_descriptor = descriptor
    else:
        raise Exception()


def get_resource(resource):
    for meeting in resource:
        meeting_id = int(meeting["CommitteeSessionID"])
        meeting["topics"] = ", ".join(meetings_topics[meeting_id]) if meeting_id in meetings_topics else ""
        meeting.update(committees_metadata[int(meeting["CommitteeID"])])
        yield meeting


meetings_descriptor["schema"]["fields"] += [{"name": "topics", "type": "string"},
                                            {"name": "committee_name", "type": "string"},
                                            {"name": "committee_type", "type": "string"}]


spew(dict(datapackage, resources=[meetings_descriptor]), [get_resource(meetings_resource)], aggs)
