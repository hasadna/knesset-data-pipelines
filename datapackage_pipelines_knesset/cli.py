import os, requests, datetime
from datapackage_pipelines_knesset.common import influxdb


def dpp_send_metrics():
    url = os.environ.get("DPP_PIPELINES_URL", "http://localhost:5000").rstrip("/")
    url = "{}/api/raw/status".format(url)
    res = requests.get(url)
    res.raise_for_status()
    pipelines = res.json()
    stats = {}
    for pipeline in pipelines:
        influxdb.send_metric("dpp_status",
                             {"id": pipeline["id"].lstrip("./"),
                              "state": str(pipeline["state"]),
                              "dirty": bool(pipeline["dirty"]),
                              "success": bool(pipeline["success"])},
                             {"pipelines": 1},
                             must_succeed=True)
        key = "{}{}".format(pipeline["state"], " (dirty)" if pipeline["dirty"] else "")
        if key not in stats:
            stats[key] = 1
        else:
            stats[key] += 1
    print(" > {}".format(datetime.datetime.now()))
    for k, v in stats.items():
        print("{}: {}".format(k, v))
    exit(0)
