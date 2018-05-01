from datapackage_pipelines.lib.load_resource import ResourceLoader
import os


class KnessetResourceLoader(ResourceLoader):

    def __init__(self):
        super(KnessetResourceLoader, self).__init__()
        if os.environ.get('LOAD_FROM_URL'):
            if self.parameters.get('url', '').startswith('../data/'):
                self.parameters['url'] = self.parameters['url'].replace('../data/', 'http://storage.googleapis.com/knesset-data-pipelines/data/')


if __name__ == '__main__':
    KnessetResourceLoader()()
