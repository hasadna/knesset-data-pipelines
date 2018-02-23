import logging
import os
import time

import requests

from datapackage_pipelines_knesset.dataservice.exceptions import ReachedMaxRetries, InvalidStatusCodeException

DEFAULT_USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.167 Safari/537.36'


def is_blocked(content):
    for str in ['if(u82222.w(u82222.O', 'window.rbzid=', '<html><head><meta charset="utf-8"><script>']:
        if str in content:
            return True
    return False


def get_retry_response_content(url, params, timeout, proxies, retry_num, num_retries, seconds_between_retries,
                               skip_not_found_errors=False):
    proxies = proxies if proxies else {}
    if os.environ.get("DATASERVICE_HTTP_PROXY"):
        proxies["http"] = os.environ["DATASERVICE_HTTP_PROXY"]

    headers = {}
    if os.environ.get("KNESET_DATASERVICE_COOKIE"):
        headers['Cookie'] = os.environ['KNESET_DATASERVICE_COOKIE']
        headers['User-Agent'] = DEFAULT_USER_AGENT
    try:
        logging.info("headers: %s", headers)
        response = requests.get(url, params=params, timeout=timeout, proxies=proxies, headers=headers)
    except requests.exceptions.InvalidSchema:
        # missing dependencies for SOCKS support
        raise
    except requests.RequestException as e:
        # network / http problem - start the retry mechanism
        if (retry_num < num_retries):
            logging.exception(e)
            logging.info("retry {} / {}, waiting {} seconds before retrying...".format(retry_num,
                                                                                       num_retries,
                                                                                       seconds_between_retries))
            time.sleep(seconds_between_retries)
            return get_retry_response_content(url, params, timeout, proxies, retry_num + 1, num_retries,
                                              seconds_between_retries)
        else:
            raise ReachedMaxRetries(e)
    if response.status_code != 200:
        # http status_code is not 200 - retry won't help here
        if response.status_code == 404 and skip_not_found_errors:
            return bytes("", "utf-8")
        else:
            raise InvalidStatusCodeException(response.status_code, response.content)
    else:
        try:
            response_text = response.content.decode('utf-8')
        except Exception:
            response_text = None
        if response_text and is_blocked(response_text):
            logging.info(response.content.decode('utf-8'))
            raise Exception("seems your request is blocked, you should use the app ssh socks proxy\n"
                            "url={}\n"
                            "params={}\n"
                            "proxies={}".format(url, params, proxies))
        else:
            return response.content
