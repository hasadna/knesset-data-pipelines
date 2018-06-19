from datapackage_pipelines.wrapper import ingest, spew
import logging, sh


parameters, datapackage, resources = ingest()


source = '../../data/committees/dist/dist'
target = 'gs://knesset-data-pipelines/data/dist'


logging.info('uploading {} --> {}'.format(source, target))
cmd = sh.Command('python2')
rsync_args = ['/gsutil/gsutil', '-qm', 'rsync', '-a', 'public-read', '-r', source, target]
ls_args = ['/gsutil/gsutil', 'ls', '-l', target]
for line in cmd(*rsync_args, _iter=True):
    logging.info(line)
for line in cmd(*ls_args, _iter=True):
    logging.info(line)


spew(dict(datapackage, resources=[]), [])
