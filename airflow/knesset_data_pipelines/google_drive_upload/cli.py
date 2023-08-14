import click


@click.group()
def google_drive_upload():
    pass


@google_drive_upload.command()
@click.option('--download-from-url', is_flag=True)
@click.option('--knesset-num', type=int)
@click.option('--limit', type=int)
@click.option('--only-session-id', type=int)
def committee_meeting_protocols(**kwargs):
    from .committee_meeting_protocols import main
    main(**kwargs)
