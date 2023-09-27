import importlib

import click
import dotenv


@click.group(context_settings={'max_content_width': 200})
@click.option('--load-dotenv', is_flag=True)
def main(load_dotenv):
    """Knesset Data Pipelines"""
    if load_dotenv:
        dotenv.load_dotenv()
    pass


for module_name, function_name in [
    ('.google_drive_upload.cli', 'google_drive_upload'),
    ('.committees.cli', 'committees'),
]:
    main.add_command(getattr(importlib.import_module(module_name, __package__), function_name))


@main.command()
@click.argument("PIPELINE_ID")
@click.option('--limit-rows')
@click.option('--dump-to-db', is_flag=True)
@click.option('--dump-to-path', is_flag=True)
@click.option('--dump-to-storage', is_flag=True)
def run(**kwargs):
    """Run a single pipeline based on the old dpp pipeline id, e.g. 'bills/kns_bill'"""
    from .run_pipeline import main
    main(**kwargs)


@main.command('list')
@click.option('--filter-pipeline-ids', help='comma separated list of pipeline ids to filter')
def list_(**kwargs):
    """List all pipelines"""
    from .run_pipeline import list_pipelines
    for error, pipeline_id, pipeline_dependencies, pipeline_schedule in list_pipelines(**kwargs, all_=True, with_dependencies=True):
        print(f'- {pipeline_id}{" (e)" if error else ""} (dependencies: {pipeline_dependencies}){" (scheduled)" if pipeline_schedule else ""}')


@main.command()
@click.option('--filter-pipeline-ids')
def run_all(**kwargs):
    from .run_pipeline import run_all
    run_all(**kwargs)


@main.command()
def dpp_shell():
    from .run_pipeline import run_dpp_shell
    run_dpp_shell()


if __name__ == "__main__":
    main()
