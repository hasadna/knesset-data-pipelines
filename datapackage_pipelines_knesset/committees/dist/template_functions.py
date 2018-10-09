from jinja2 import Environment, FileSystemLoader, select_autoescape
import os, logging, socket, datetime, json, re
from .constants import COMMITTEES_INDEX_URL, MEMBERS_HOME_URL
import jsonpickle


def get_jinja_env(templates_path='templates'):
    return Environment(
        loader=FileSystemLoader(templates_path),
        autoescape=select_autoescape(['html', 'xml'])
    )


def get_jinja_template(jinja_env, template_name):
    return jinja_env.get_template(template_name)


def build_template(jinja_env, template_name, context, output_name=None, with_hash=None,
                   output_root_dir="../../data/committees/dist/dist"):
    if output_name is None:
        output_name = template_name
    dist_file_name = os.path.join(output_root_dir, output_name)
    json_file_name = re.sub(r'(.html)$', '.json', dist_file_name)
    hash_file_name = re.sub(r'(.html)$', '.hash', dist_file_name)
    old_hash = None
    if with_hash is not None and os.path.exists(hash_file_name):
        with open(hash_file_name) as f:
            old_hash = f.read()
    if old_hash is None or old_hash != with_hash:
        if with_hash is not None:
            context = context()
        os.makedirs(os.path.dirname(dist_file_name), exist_ok=True)
        logging.info("Building template {} to {}".format(template_name, dist_file_name))
        template = get_jinja_template(jinja_env, template_name)
        with open(dist_file_name, "w") as f:
            f.write(template.render(context))
        with open(json_file_name, 'w') as f:
            f.write(jsonpickle.dumps(context))
        if with_hash is not None:
            with open(hash_file_name, 'w') as f:
                f.write(with_hash)


def get_context(context):
    return dict(context, **{"create_hostname": socket.getfqdn(),
                            "create_time": datetime.datetime.now().strftime("%H:%M"),
                            "create_date": datetime.datetime.now().strftime("%d/%m/%Y"),
                            "committeelist_url": COMMITTEES_INDEX_URL,
                            "members_home_url": MEMBERS_HOME_URL})
