from datapackage_pipelines.lib.load_resource import ResourceLoader
import os, logging


class KnessetResourceLoader(ResourceLoader):

    def __init__(self, **kwargs):
        super(KnessetResourceLoader, self).__init__()
        self.parameters.update(**kwargs)
        if self.parameters.get('path'):
            path = self.parameters.pop('path')
            app = self.parameters.pop('app') if self.parameters.get('app') else 'pipelines'
            if app == 'pipelines':
                if os.environ.get('KNESSET_PIPELINES_DATA_PATH'):
                    self.parameters['url'] = os.path.join(os.environ.get('KNESSET_PIPELINES_DATA_PATH', 'data'), path)
                else:
                    self.parameters['url'] = 'http://storage.googleapis.com/knesset-data-pipelines/data/{}'.format(path)
            elif app == 'committees':
                if os.environ.get('KNESSET_PIPELINES_DATA_PATH'):
                    self.parameters['url'] = os.path.join(os.environ.get('KNESSET_PIPELINES_DATA_PATH'), 'committees/dist', path)
                else:
                    self.parameters['url'] = 'http://storage.googleapis.com/knesset-data-pipelines/data/committees-build/{}'.format(path)
            elif app == 'people':
                if os.environ.get('KNESSET_PIPELINES_DATA_PATH'):
                    self.parameters['url'] = os.path.join(os.environ.get('KNESSET_PIPELINES_DATA_PATH'), 'people', path)
                else:
                    self.parameters['url'] = 'http://storage.googleapis.com/knesset-data-pipelines/data/people/{}'.format(path)
        # logging.info(self.parameters)

    def process_datapackage(self, dp_):
        # logging.info(dp_.descriptor)
        return super(KnessetResourceLoader, self).process_datapackage(dp_)


if __name__ == '__main__':
    KnessetResourceLoader()()
