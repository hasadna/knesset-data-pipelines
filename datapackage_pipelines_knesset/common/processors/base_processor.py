class BaseProcessor(object):

    def __init__(self, parameters=None, datapackage=None, resources=None):
        self._parameters = parameters if parameters else {}
        self._datapackage = datapackage if datapackage else {}
        self._resources = resources if resources else []

    @classmethod
    def main(cls):
        from datapackage_pipelines.wrapper import ingest, spew
        spew(*cls(*ingest()).spew())

    def spew(self):
        self._datapackage, self._resources = self._process(self._datapackage, self._resources)
        return self._datapackage, self._resources

    def _process(self, datapackage, resources):
        return datapackage, resources
