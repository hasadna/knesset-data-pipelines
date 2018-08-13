from datapackage_pipelines.wrapper import ingest, spew
import logging, sh, os


parameters, datapackage, resources = ingest()


def finalizer():
    source = parameters['source']
    target = parameters['target']

    if os.path.exists('/gsutil/gsutil'):
        logging.info('uploading {} --> {}'.format(source, target))
        cmd = sh.Command('python2')
        rsync_args = ['/gsutil/gsutil', '-q', 'rsync', '-a', 'public-read', '-r', source, target]
        ls_args = ['/gsutil/gsutil', 'ls', '-l', target]
        for line in cmd(*rsync_args, _iter=True):
            logging.info(line)
        for line in cmd(*ls_args, _iter=True):
            logging.info(line)
    else:
        logging.warning('skipping sync: missing /gsutil/gsutil')


spew(datapackage, resources, finalizer=finalizer)
