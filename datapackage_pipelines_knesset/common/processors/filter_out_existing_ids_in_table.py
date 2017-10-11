from datapackage_pipelines_knesset.common.base_processors.base_resource import BaseResourceProcessor
from datapackage_pipelines_knesset.common.utils import parse_import_func_parameter
import logging


class FilterExistingIdsProcessor(BaseResourceProcessor):

    def __init__(self, *args, **kwargs):
        super(FilterExistingIdsProcessor, self).__init__(*args, **kwargs)

    def _process(self, datapackage, resources):
        self._db_table = self.db_meta.tables.get(self._parameters["table"])
        if self._db_table is not None:
            logging.info("table is cool")
            self._id_column = getattr(self._db_table.c, self._parameters["id-column"])
            self._existing_ids = set([int(row[0]) for row in self.db_session.query(self._id_column).all()])
            logging.info("existing_ids %s" % str(self._existing_ids))
        else:
            logging.info("table is NOT cool")
            self._existing_ids = []
        return super(FilterExistingIdsProcessor, self)._process(datapackage, resources)

    def _filter_row(self, row):
        logging.info("id field %s" % self._parameters["id-field"])
        is_in_existing_ids = int(row[self._parameters["id-field"]]) in self._existing_ids
        filter_row = self._parameters.get("filter-row")
        if filter_row:
            return parse_import_func_parameter(filter_row, row, is_in_existing_ids)
        elif is_in_existing_ids:
            return None
        else:
            return row

if __name__ == '__main__':
    FilterExistingIdsProcessor.main()