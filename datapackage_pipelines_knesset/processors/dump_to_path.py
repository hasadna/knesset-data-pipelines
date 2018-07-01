from datapackage_pipelines.lib.dump.to_path import PathDumper
import logging, sh, os


class StorageDumper(PathDumper):

    def initialize(self, params):
        params['pretty-descriptor'] = True
        super(StorageDumper, self).initialize(params)
        if os.environ.get('DUMP_TO_STORAGE'):
            storage_url = params.get('storage-url')
            if not storage_url and self.out_path.startswith('../data/'):
                storage_url = self.out_path.replace('../data/', 'http://storage.googleapis.com/knesset-data-pipelines/data/')
            assert storage_url
            self.sync_paths = {self.out_path: storage_url}
            self.sync_paths.update(**params.get('additional-paths', {}))
            for path, url in self.sync_paths.items():
                assert url.startswith('http://storage.googleapis.com/')
                assert path
            self.command = params.get('command', 'python2')
            self.rsync_args = params.get('rsync-args', ['/gsutil/gsutil', '-m', 'rsync', '-a', 'public-read', '-r'])
            self.ls_args = params.get('ls-args', ['/gsutil/gsutil', 'ls', '-l'])

    def finalize(self):
        super(StorageDumper, self).finalize()
        if os.environ.get('DUMP_TO_STORAGE'):
            logging.getLogger().setLevel(logging.INFO)
            for path, url in self.sync_paths.items():
                url = url.replace('http://storage.googleapis.com/', 'gs://')
                logging.info('uploading {} --> {}'.format(path, url))
                cmd = sh.Command(self.command)
                rsync_args = self.rsync_args + [path, url]
                ls_args = self.ls_args + [url]
                for line in cmd(*rsync_args, _iter=True):
                    logging.info(line)
                for line in cmd(*ls_args, _iter=True):
                    logging.info(line)


if __name__ == '__main__':
    StorageDumper()()
