import click


@click.group()
def members_eng():
    pass

@members_eng.command()
def members_eng(**kwargs):
    '''Create a table of knesset member names in english
    '''
    from .members_eng import main
    print("running main")
    main(**kwargs)
