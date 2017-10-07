import csv, os, io, contextlib
from minio import Minio
from minio.error import NoSuchBucket, NoSuchKey
from datapackage_pipelines_knesset.common import utils
from urllib.parse import urlparse


def get_minio():
    if not os.environ.get("DPP_MINIO_CONFIG"):
        return False, False
    else:
        host = urlparse(os.environ.get("S3_ENDPOINT_URL")).netloc
        access_key = os.environ.get("AWS_ACCESS_KEY_ID")
        secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
        return Minio(host, access_key, secret_key, secure=False)


def exists(bucket, object_name, min_size=None):
    minio = get_minio()
    try:
        with utils.temp_loglevel():
            res = minio.stat_object(bucket, object_name)
    except Exception:
        res = False
    if res and min_size:
        return res.size > min_size
    else:
        return bool(res)


def get_write_object_data(data):
    if isinstance(data, str):
        data = data.encode()
    return io.BytesIO(data), len(data)


def write(bucket, object_name, data=None, file_name=None, create_bucket=True):
    minio = get_minio()
    try:
        with utils.temp_loglevel():
            if file_name is not None and data is None:
                minio.fput_object(bucket, object_name, file_name)
            elif data is not None and file_name is None:
                minio.put_object(bucket, object_name, *get_write_object_data(data))
            else:
                raise AttributeError()
    except NoSuchBucket:
        if create_bucket:
            with utils.temp_loglevel():
                minio.make_bucket(bucket)
            write(bucket, object_name, data=data, file_name=file_name, create_bucket=False)
        else:
            raise


def delete(bucket, object_name):
    minio = get_minio()
    if exists(bucket, object_name):
        # if the object exists - we ensure it's deleted without cathing any exceptions
        with utils.temp_loglevel():
            minio.remove_object(bucket, object_name)


@contextlib.contextmanager
def temp_download(bucket, object_name):
    with utils.temp_file() as file_name:
        download(bucket, object_name, file_name)
        yield file_name


def download(bucket, object_name, file_name):
    minio = get_minio()
    with utils.temp_loglevel():
        res = minio.fget_object(bucket, object_name, file_name)
    return bool(res)


def read(bucket, object_name):
    minio = get_minio()
    with utils.temp_loglevel():
        res = minio.get_object(bucket, object_name)
    return res.read()


@contextlib.contextmanager
def csv_writer(bucket, object_name):
    with utils.temp_file() as filename:
        with open(filename, "w") as f:
            yield csv.writer(f)
        write(bucket, object_name, file_name=filename)
