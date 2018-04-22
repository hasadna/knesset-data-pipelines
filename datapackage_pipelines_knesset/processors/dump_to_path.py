from datapackage_pipelines.lib.dump.to_path import PathDumper
import logging, sh, os


class StorageDumper(PathDumper):

    def initialize(self, params):
        super(StorageDumper, self).initialize(params)
        if os.environ.get('DUMP_TO_STORAGE'):
            self.storage_url = params.get('storage-url')
            if not self.storage_url and self.out_path.startswith('../data/'):
                self.storage_url = self.out_path.replace('../data/', 'http://storage.googleapis.com/knesset-data-pipelines/data/')
            assert self.storage_url
            self.command = params.get('command', 'python2')
            self.rsync_args = params.get('rsync-args', ['/gsutil/gsutil', '-m', 'rsync', '-a', 'public-read', '-r'])
            self.ls_args = params.get('ls-args', ['/gsutil/gsutil', 'ls', '-l'])

    def finalize(self):
        super(StorageDumper, self).finalize()
        if os.environ.get('DUMP_TO_STORAGE'):
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
