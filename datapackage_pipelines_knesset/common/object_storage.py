import csv, os, io, contextlib
from botocore.client import Config
from botocore.exceptions import ClientError
import boto3
from datapackage_pipelines_knesset.common import utils
import json
import datetime


def get_s3():
    url, key, secret = map(os.environ.get, ["S3_ENDPOINT_URL", "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"])
    s3 = False
    if url and key and secret:
        with utils.temp_loglevel():
            s3 = boto3.client('s3', endpoint_url=os.environ["S3_ENDPOINT_URL"],
                              aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
                              aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
                              config=Config(signature_version='s3v4'), region_name='us-east-1')
    return s3


def exists(s3, bucket, object_name, min_size=None):
    try:
        with utils.temp_loglevel():
            res = s3.head_object(Bucket=bucket, Key=object_name)
    except Exception:
        res = False
    if res and min_size:
        return res['ContentLength'] > min_size
    else:
        return bool(res)


def get_write_object_data(data):
    if isinstance(data, str):
        data = data.encode()
    return io.BytesIO(data)


def write(s3, bucket, object_name, data=None, file_name=None, create_bucket=True, public_bucket=False):
    try:
        with utils.temp_loglevel():
            if public_bucket:
                s3.put_bucket_policy(Bucket=bucket, Policy=json.dumps({
                    "Version": str(datetime.datetime.now()).replace(" ", "-"),
                    "Statement": [{"Sid": "AddPerm", "Effect": "Allow", "Principal": "*",
                                   "Action": ["s3:GetObject"], "Resource": ["arn:aws:s3:::{}/*".format(bucket)]}]}))
            if file_name is not None and data is None:
                s3.put_object(Body=open(file_name, 'rb'), Bucket=bucket, Key=object_name)
            elif data is not None and file_name is None:
                s3.put_object(Body=get_write_object_data(data), Bucket=bucket, Key=object_name)
            else:
                raise AttributeError()
    except ClientError:
        if create_bucket:
            with utils.temp_loglevel():
                s3.create_bucket(Bucket=bucket)
            write(s3, bucket, object_name, data=data, file_name=file_name, create_bucket=False, public_bucket=public_bucket)
        else:
            raise


def delete(s3, bucket, object_name):
    if exists(s3, bucket, object_name):
        with utils.temp_loglevel():
            s3.delete_object(Bucket=bucket, Key=object_name)


@contextlib.contextmanager
def temp_download(s3, bucket, object_name):
    with utils.temp_file() as file_name:
        download(s3, bucket, object_name, file_name)
        yield file_name

def get_read_object_data(data):
    return io.BytesIO(data)


def download(s3, bucket, object_name, file_name):
    with utils.temp_loglevel():
        res = s3.get_object(Bucket=bucket, Key=object_name)
        with open(file_name, "wb") as f:
            f.write(res["Body"].read())
    return bool(res)


def read(s3, bucket, object_name):
    with utils.temp_loglevel():
        res = s3.get_object(Bucket=bucket, Key=object_name)
    return res["Body"].read()


@contextlib.contextmanager
def csv_writer(s3, bucket, object_name, public_bucket=False):
    with utils.temp_file() as filename:
        with open(filename, "w") as f:
            yield csv.writer(f)
        write(s3, bucket, object_name, file_name=filename, public_bucket=public_bucket)
