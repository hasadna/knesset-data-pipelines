import yaml
import logging
from datapackage_pipelines.wrapper import ingest, spew
import os, subprocess, logging
from datapackage_pipelines_knesset.committees.dist.template_functions import build_template, get_jinja_env, get_context
from datapackage_pipelines_knesset.committees.dist.constants import HOMEPAGE_URL


parameters, datapackage, resources, stats = ingest() + ({},)


def get_data_category_items(id):
    with open(f'../../{id}/knesset.source-spec.yaml') as f:
        source_spec = yaml.load(f)
    for data_item_id, spec in source_spec.items():
        if spec.get('description'):
            yield {
                'id': data_item_id,
                'description': spec['description'],
            }


def get_data_category(id, title):
    return {
        'id': id,
        'title': title,
        'data_items': list(get_data_category_items(id))
    }


def get_data_categories():
    return [
        get_data_category('committees', 'ועדות'),
        get_data_category('knesset', 'נתונים כלליים'),
        get_data_category('laws', 'חוקים'),
        get_data_category('lobbyists', 'לוביסטים'),
        get_data_category('members', 'ח"כים'),
        get_data_category('people', 'מידע על אנשים המופיעים במידע'),
        get_data_category('plenum', 'מליאה'),
        get_data_category('votes', 'הצבעות'),
    ]


def get_homepage_context():
    return get_context({
        "data_categories": get_data_categories()
    })


jinja_env = get_jinja_env()

build_template(jinja_env, "homepage.html", get_homepage_context(), HOMEPAGE_URL)

if os.environ.get("SKIP_STATIC") != "1":
    logging.info("Copying static files from ./static to ./dist/static")
    subprocess.check_call(["mkdir", "-p", "../../data/committees/dist/dist"])
    subprocess.check_call(["cp", "-rf", "static", "../../data/committees/dist/dist/"])
else:
    logging.info("Skipping copying static files because SKIP_STATIC=1")


spew(dict(datapackage, resources=[]), [], stats)
