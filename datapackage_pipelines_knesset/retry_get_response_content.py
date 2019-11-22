import logging
import os
import time

import requests

from datapackage_pipelines_knesset.dataservice.exceptions import ReachedMaxRetries, InvalidStatusCodeException

def is_blocked(content):
    for str in ['if(u82222.w(u82222.O', 'window.rbzid=', '<html><head><meta charset="utf-8"><script>']:
        if str in content:
            return True
    return False


def get_retry_response_content(url, params, timeout, proxies, retry_num, num_retries, seconds_between_retries,
                               skip_not_found_errors=False, headers=None):
    if not timeout or float(timeout) < 60:
        timeout = 60
    proxies = proxies if proxies else {}
    headers = headers if headers else {}

    if os.environ.get("DATASERVICE_HTTP_PROXY"):
        proxies["http"] = os.environ["DATASERVICE_HTTP_PROXY"]

    try:
        response = requests.get(url, params=params, timeout=timeout, proxies=proxies, headers=headers)
    except requests.exceptions.InvalidSchema:
        # missing dependencies for SOCKS support
        raise
    except requests.RequestException as e:
        # network / http problem - start the retry mechanism
        if (retry_num < num_retries):
            logging.exception(e)
            logging.info("url: {} params: {}".format(url, params))
            logging.info("retry {} / {}, waiting {} seconds before retrying...".format(retry_num,
                                                                                       num_retries,
                                                                                       seconds_between_retries))
            time.sleep(seconds_between_retries)
            return get_retry_response_content(url, params, timeout, proxies, retry_num + 1, num_retries,
                                              seconds_between_retries, headers=headers)
        else:
            logging.info("url: {} params: {}".format(url, params))
            raise ReachedMaxRetries(e)
    if response.status_code != 200:
        # http status_code is not 200 - retry won't help here
        if response.status_code == 404 and skip_not_found_errors:
            return bytes("", "utf-8")
        else:
            logging.info("url: {} params: {}".format(url, params))
            raise InvalidStatusCodeException(response.status_code, response.content)
    else:
        try:
            response_text = response.content.decode('utf-8')
        except Exception:
            response_text = None
        if response_text and is_blocked(response_text) and 'Set-Cookie' in response.headers and 'Cookie' not in headers:
            # try again, but this time with the cookie we were given
            first_cookie = response.headers['Set-Cookie'].split(";")[0]
            headers['Cookie'] = first_cookie
            return get_retry_response_content(url, params, timeout, proxies, retry_num, num_retries,
                                              seconds_between_retries, headers=headers)
        if response_text and is_blocked(response_text):
            # logging.info(response.content.decode('utf-8'))
            raise Exception("seems your request is blocked, you should use the app ssh socks proxy\n"
                            "url={}\n"
                            "params={}\n"
                            "proxies={}\n"
                            "headers={}".format(url, params, proxies, headers))
        else:
            return response.content
