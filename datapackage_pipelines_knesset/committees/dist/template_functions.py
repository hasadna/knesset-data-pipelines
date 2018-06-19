from jinja2 import Environment, FileSystemLoader, select_autoescape
import os, logging, socket, datetime, json, re
from .constants import COMMITTEES_INDEX_URL, MEMBERS_HOME_URL
import jsonpickle


def get_jinja_env():
    return Environment(
        loader=FileSystemLoader('templates'),
        autoescape=select_autoescape(['html', 'xml'])
    )


def get_jinja_template(jinja_env, template_name):
    return jinja_env.get_template(template_name)


def build_template(jinja_env, template_name, context, output_name=None):
    if output_name is None:
        output_name = template_name
    dist_file_name = os.path.join("../../data/committees/dist/dist", output_name)
    os.makedirs(os.path.dirname(dist_file_name), exist_ok=True)
    logging.info("Building template {} to {}".format(template_name, dist_file_name))
    template = get_jinja_template(jinja_env, template_name)
    with open(dist_file_name, "w") as f:
        f.write(template.render(context))
    with open(re.sub(r'(.html)$', '.json', dist_file_name), 'w') as f:
        f.write(jsonpickle.dumps(context))


def get_context(context):
    return dict(context, **{"create_hostname": socket.getfqdn(),
                            "create_time": datetime.datetime.now().strftime("%H:%M"),
                            "create_date": datetime.datetime.now().strftime("%d/%m/%Y"),
                            "committeelist_url": COMMITTEES_INDEX_URL,
                            "members_home_url": MEMBERS_HOME_URL})
