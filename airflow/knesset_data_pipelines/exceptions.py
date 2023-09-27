class InvalidStatusCodeException(Exception):

    def __init__(self, status_code, response_content):
        self.status_code = status_code
        self.response_content = response_content
        super(InvalidStatusCodeException, self).__init__("invalid response status code: {}".format(status_code))


class ReachedMaxRetries(Exception):

    def __init__(self, exception):
        self.original_exception = exception
        super(ReachedMaxRetries, self).__init__("exceeded maximum retries, last error: {}".format(exception))
