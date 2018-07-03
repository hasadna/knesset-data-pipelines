from datapackage_pipelines.wrapper import ingest, spew
import os, logging


parameters, datapackage, resources, stats = ingest() + ({},)
if os.environ.get("TEST_DATA") == "1" or parameters.get("test-data"):
    parameters.update(**{"committee-ids": [2026, 2022, 1013, 1012, 2017],
                         "max-meetings-per-committee": 5,})


stats.update(**{"committees": 0, "skipped committees": 0})
all_committee_ids = []


# filter committees by committee ids and/or knesset-nums
def get_committees(committees):
    for committee in committees:
        if all([not parameters.get("committee-ids") or committee["CommitteeID"] in parameters["committee-ids"],
                not parameters.get("knesset-nums") or committee["KnessetNum"] in parameters["knesset-nums"]]):
            yield committee
            stats["committees"] += 1
            all_committee_ids.append(committee["CommitteeID"])
        else:
            stats["skipped committees"] += 1


stats.update(**{"mks": 0, "skipped mks": 0})


# filter mks by knesset-nums
def get_mks(mks):
    for mk in mks:
        if parameters.get("knesset-nums"):
            position_included = False
            for position in mk["positions"]:
                if position.get("KnessetNum") and position["KnessetNum"] in parameters["KnessetNum"]:
                    position_included = True
                    break
            if position_included:
                yield mk
                stats["mks"] += 1
            else:
                stats["skipped mks"] += 1
        else:
            yield mk
            stats["mks"] += 1


stats.update(**{"meetings": 0, "skipped meetings": 0})


# filter meetings for the filtered committees
def get_meetings(resource):
    committee_meeting_nums = {}
    for row in resource:
        if row["CommitteeID"] in all_committee_ids:
            if not parameters.get("max-meetings-per-committee") or committee_meeting_nums.setdefault(row["CommitteeID"], 0) < parameters["max-meetings-per-committee"]:
                yield row
                stats["meetings"] += 1
                committee_meeting_nums.setdefault(row["CommitteeID"], 0)
                committee_meeting_nums[row["CommitteeID"]] += 1
            else:
                stats["skipped meetings"] += 1
        else:
            stats["skipped meetings"] += 1
            # this is usually due to edge case where a committee was just added
            # so we get the id from meetings but don't have the corresponding committee
            # it will be fixed when the committees package is updated on the next run
            logging.info('skipped meeting {} - missing committee {}'.format(row['CommitteeSessionID'],
                                                                            row['CommitteeID']))


def get_resources():
    for descriptor, resource in zip(datapackage["resources"], resources):
        if descriptor["name"] == "kns_committee":
            yield get_committees(resource)
        elif descriptor["name"] == "mk_individual":
            yield get_mks(resource)
        elif descriptor["name"] == "kns_committeesession":
            yield get_meetings(resource)
        else:
            raise Exception("Invalid resource {}".format(descriptor["name"]))


spew(datapackage, get_resources(), stats)
