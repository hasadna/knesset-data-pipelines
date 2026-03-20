import click


@click.group()
def committees():
    pass


@committees.command()
def parsed_document_committee_sessions(**kwargs):
    from .parsed_document_committee_sessions import main
    main(**kwargs)
