import click
import dotenv


@click.group(context_settings={'max_content_width': 200})
@click.option('--load-dotenv', is_flag=True)
def main(load_dotenv):
    """Knesset Data Pipelines"""
    if load_dotenv:
        dotenv.load_dotenv()
    pass


from .google_drive_upload.cli import google_drive_upload
main.add_command(google_drive_upload)


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
def list_():
    """List all pipelines"""
    from .run_pipeline import list_pipelines
    for pipeline_id in list_pipelines():
        print(f'- {pipeline_id}')


@main.command()
@click.option('--filter-pipeline-ids')
def run_all(**kwargs):
    from .run_pipeline import run_all
    run_all(**kwargs)


if __name__ == "__main__":
    main()
