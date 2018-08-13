from datapackage_pipelines.wrapper import ingest, spew
from datapackage_pipelines_knesset.committees.dist.template_functions import get_jinja_env
import logging, os, subprocess
from datetime import datetime
from datapackage_pipelines_knesset.committees.dist.template_functions import build_template, get_context
from datapackage_pipelines_knesset.committees.dist.constants import FACTION_HOME_URL, FACTION_URL, MEMBER_URL, MEMBERS_HOME_URL


def main():
    parameters, datapackage, resources = ingest()

    jinja_env = get_jinja_env()

    members = {}
    factions = {}
    knessets = {}
    counts = {}

    for descriptor, resource in zip(datapackage["resources"], resources):
        if descriptor["name"] == "members":
            for member in resource:
                members[member["mk_individual_id"]] = member
        elif descriptor["name"] == "positions":
            for position in resource:
                if position["object_type"] == "faction":
                    factions[position["object_id"]] = {
                        "faction_num": position["object_id"],
                        "faction_name": position["object_name"],
                        "mks": []
                    }
                    for id in position["mk_individual_ids"]:
                        factions[position["object_id"]]["mks"].append(members[id])
        elif descriptor["name"] == "knessets":
            for knesset in resource:
                knessets[knesset["KnessetNum"]] = []
                for id in knesset["faction"]:
                    knessets[knesset["KnessetNum"]].append(factions[id])

    for knesset_num, factions in knessets.items():
        mks = set()

        build_template(jinja_env, "factions_index.html",
                       get_context({
                           "knesset_num": knesset_num,
                           "factions": factions,
                           "faction_url": FACTION_URL.format(knesset_num=knesset_num,faction_id="{faction_id}"),
                           "member_url": MEMBER_URL
                       }),
                       FACTION_HOME_URL.format(knesset_num=knesset_num))

        for faction in factions:
            if not faction['faction_name']:
                continue

            for mk in faction['mks']:
                mks.add(mk['mk_individual_id'])

            build_template(jinja_env, "faction_detail.html",
                           get_context({
                               "knesset_num": knesset_num,
                               "faction_num": faction["faction_num"],
                               "faction_name": faction["faction_name"],
                               "mks": faction["mks"],
                               "faction_home_url": FACTION_HOME_URL.format(knesset_num=knesset_num),
                               "member_url": MEMBER_URL
                           }),
                           FACTION_URL.format(knesset_num=knesset_num,faction_id=faction["faction_num"]))

        counts[knesset_num] = {
            'factions': len(factions),
            'mks': len(mks)
        }

    build_template(jinja_env, "members_index.html",
                   get_context({
                       "keys": sorted(counts, reverse=True),
                       "knessets": counts,
                        "url": FACTION_HOME_URL
                   }),
                   MEMBERS_HOME_URL)

    if os.environ.get("SKIP_STATIC") != "1":
        subprocess.check_call(["mkdir", "-p", "../../data/committees/dist/dist"])
        subprocess.check_call(["cp", "-rf", "static", "../../data/committees/dist/dist/"])

    spew(dict(datapackage, resources=[]), [], {})


if __name__ == "__main__":
    main()
