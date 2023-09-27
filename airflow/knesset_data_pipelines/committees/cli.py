import click


@click.group()
def committees():
    pass


@committees.command()
def background_material_titles(**kwargs):
    from .background_material_titles import main
    main(**kwargs)
