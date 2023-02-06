import click
import dotenv


@click.group(context_settings={'max_content_width': 200})
@click.option('--load-dotenv', is_flag=True)
def main(load_dotenv):
    """Knesset Data Pipelines"""
    if load_dotenv:
        dotenv.load_dotenv()
    pass


@main.command()
@click.argument("PIPELINE_ID")
@click.option('--limit-rows')
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


if __name__ == "__main__":
    main()
