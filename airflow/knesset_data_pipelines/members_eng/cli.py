import click


@click.group()
def members_eng():
    pass

@members_eng.command()
@click.option('--slow', is_flag=True)
def members_eng(**kwargs):
    '''Create a table of knesset member names in english
    '''
    from .members_eng import main
    main(**kwargs)
