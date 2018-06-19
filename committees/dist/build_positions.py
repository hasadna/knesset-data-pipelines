from datapackage_pipelines.wrapper import ingest, spew
from datapackage_pipelines.utilities.resources import PROP_STREAMING
import logging

parameters, datapackage, resources, stats = ingest() + ({},)

output_positions = {}
output_knessets = {}
output_members = []

for descriptor, resource in zip(datapackage["resources"], resources):
    positions = {
        "position_id": {
            "type": "position",
            "name": "position"
        },
        "GovMinistryID": {
            "type": "ministry",
            "name": "GovMinistryName"
        },
        "FactionID": {
            "type": "faction",
            "name": "FactionName"
        },
        "CommitteeID": {
            "type": "committee",
            "name": "CommitteeName"
        }
    }

    for member in resource:
        id = member["mk_individual_id"]

        output_members.append({
            "mk_individual_id": id,
            "FirstName": member["FirstName"],
            "LastName": member["LastName"],
            "mk_individual_photo": member["mk_individual_photo"]
        })

        for rows in member["positions"]:
            for position, settings in positions.items():

                if(position in rows):

                    if "KnessetNum" in rows:
                        if rows["KnessetNum"] not in output_knessets:
                            output_knessets[rows["KnessetNum"]] = {
                                "KnessetNum": rows["KnessetNum"],
                                "position": [],
                                "ministry": [],
                                "faction": [],
                                "committee": []
                            }

                        knesset = output_knessets[rows["KnessetNum"]]

                        if rows[position] not in knesset[settings["type"]]:
                            knesset[settings["type"]].append(rows[position])

                    key = str(rows[position]) + settings["type"]

                    if(key in output_positions):
                        if id not in output_positions[key]["mk_individual_ids"]:
                            output_positions[key]["mk_individual_ids"].append(id)
                    else:
                        output_positions[key] = {
                            "object_id": rows[position],
                            "object_type": settings["type"],
                            "object_name": rows[settings["name"]],
                            "knesset_num": rows["KnessetNum"] if "KnessetNum" in rows else "",
                            "mk_individual_ids": [id]
                        }

output_resources = [output_positions.values(), output_knessets.values(), output_members]

descriptor_positions = {
    PROP_STREAMING: True,
   "encoding": "utf-8",
   "format": "csv",
   "name": "positions",
   "path": "positions.csv",
   "schema": {
      "fields": [
         {
             "name": "object_id",
             "type": "integer"
         },
         {
             "name": "object_type",
             "type": "string"
         },
         {
             "name": "object_name",
             "type": "string"
         },
         {
             "name": "knesset_num",
             "type": "integer"
         },
         {
             "name": "mk_individual_ids",
             "type": "array"
         }
      ],
      "primaryKey": ["object_id", "object_type"]
   }
}
descriptor_knessets = {
    PROP_STREAMING: True,
   "encoding": "utf-8",
   "format": "csv",
   "name": "knessets",
   "path": "knessets.csv",
   "schema": {
      "fields": [
         {
             "name": "KnessetNum",
             "type": "integer"
         },
         {
             "name": "position",
             "type": "array"
         },
         {
             "name": "ministry",
             "type": "array"
         },
         {
             "name": "faction",
             "type": "array"
         },
         {
             "name": "committee",
             "type": "array"
         }
      ],
      "primaryKey": ["KnessetNum"]
   }
}
descriptor_members = {
    PROP_STREAMING: True,
   "encoding": "utf-8",
   "format": "csv",
   "name": "members",
   "path": "members.csv",
   "schema": {
      "fields": [
         {
             "name": "mk_individual_id",
             "type": "integer"
         },
         {
             "name": "FirstName",
             "type": "string"
         },
         {
             "name": "LastName",
             "type": "string"
         },
         {
             "name": "mk_individual_photo",
             "type": "string"
         }
      ],
      "primaryKey": ["mk_individual_id"]
   }
}

output_datapackage = dict(name="positions_aggr", resources=[descriptor_positions,
                                                  descriptor_knessets,
                                                  descriptor_members])

spew(output_datapackage, output_resources, stats)