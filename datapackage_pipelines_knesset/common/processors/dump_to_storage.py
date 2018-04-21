from datapackage_pipelines.lib.dump.to_path import PathDumper
import logging, subprocess, sh


class StorageDumper(PathDumper):

    def initialize(self, params):
        super(StorageDumper, self).initialize(params)
        self.storage_url = params['storage-url']
        self.command = params.get('command')
        self.rsync_args = params['rsync-args']
        self.ls_args = params['ls-args']

    def finalize(self):
        logging.getLogger().setLevel(logging.INFO)
        if self.storage_url.startswith('http://storage.googleapis.com/'):
            url = self.storage_url.replace('http://storage.googleapis.com/', 'gs://')
            logging.info('uploading {} --> {}'.format(self.out_path, url))
            cmd = sh.Command(self.command)
            rsync_args = self.rsync_args + [self.out_path, url]
            ls_args = self.ls_args + [url]
            for line in cmd(*rsync_args, _iter=True):
                logging.info(line)
            for line in cmd(*ls_args, _iter=True):
                logging.info(line)
        else:
            logging.warning('invalid storage_url: {}'.format(self.storage_url))


if __name__ == '__main__':
    StorageDumper()()
