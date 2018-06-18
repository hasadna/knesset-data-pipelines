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
                    self.parameters['url'] = os.path.join(os.environ['KNESSET_PIPELINES_DATA_PATH'], path)
                else:
                    self.parameters['url'] = 'http://storage.googleapis.com/knesset-data-pipelines/data/{}'.format(path)
            elif app == 'committees':
                if os.environ.get('KNESSET_COMMITTEES_DATA_PATH'):
                    self.parameters['url'] = os.path.join(os.environ['KNESSET_COMMITTEES_DATA_PATH'], path)
                else:
                    self.parameters['url'] = 'http://storage.googleapis.com/knesset-data-pipelines/data/committees-build/{}'.format(path)
            elif app == 'people':
                if os.environ.get('KNESSET_PEOPLE_DATA_PATH'):
                    self.parameters['url'] = os.path.join(os.environ['KNESSET_PEOPLE_DATA_PATH'], path)
                else:
                    self.parameters['url'] = 'http://storage.googleapis.com/knesset-data-pipelines/data/people/{}'.format(path)
        logging.info(self.parameters)


if __name__ == '__main__':
    KnessetResourceLoader()()
