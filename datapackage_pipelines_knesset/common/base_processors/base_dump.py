from datapackage_pipelines_knesset.common.base_processors.filter_resource import FilterResourceBaseProcessor
import logging


DEFAULT_COMMIT_EVERY = 1000


class BaseDumpProcessor(FilterResourceBaseProcessor):

    def _commit(self, rows):
        raise NotImplementedError()

    @property
    def _log_prefix(self):
        raise NotImplementedError()

    def _flush_rows_buffer(self):
        if len(self._rows_buffer) > 0:
            self._commit(self._rows_buffer)
            self._rows_buffer = []

    def _filter_row(self, resource_number, row):
        for row in super(BaseDumpProcessor, self)._filter_row(resource_number, row):
            self._row_num += 1
            if self._commit_buffer_length > 1:
                if self._row_num%self._commit_buffer_length == 0:
                    self._flush_rows_buffer()
            self._rows_buffer.append(row)
            if self._commit_buffer_length < 2:
                self._flush_rows_buffer()
            yield row

    def _filter_resource(self, *args):
        self._commit_buffer_length = int(self._parameters.get("commit-every", DEFAULT_COMMIT_EVERY))
        self._set_stat("commit every rows", self._commit_buffer_length)
        self._row_num = 0
        self._rows_buffer = []
        if self._commit_buffer_length > 1:
            logging.info("{}: initialized, committing every {} rows".format(self._log_prefix,
                                                                            self._commit_buffer_length))
        else:
            logging.info("{}: initialized".format(self._log_prefix))
        yield from super(BaseDumpProcessor, self)._filter_resource(*args)
        self._flush_rows_buffer()

    def _filter_stat_key(self, stat):
        stat = "{}: {}".format(self._log_prefix, stat)
        return stat
