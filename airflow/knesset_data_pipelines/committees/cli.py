import click


@click.group()
def committees():
    pass


@committees.command()
def background_material_titles(**kwargs):
    from .background_material_titles import main
    main(**kwargs)


@committees.command()
def parsed_document_committee_sessions(**kwargs):
    from .parsed_document_committee_sessions import main
    main(**kwargs)
