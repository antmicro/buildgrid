# Copyright (C) 2018 Bloomberg LP
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#  <http://www.apache.org/licenses/LICENSE-2.0>
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


"""
S3Storage
==================

A storage provider that stores data in an Amazon S3 bucket.
"""

import io
import logging

import boto3
from botocore.exceptions import ClientError

from .storage_abc import StorageABC


class S3Storage(StorageABC):

    def __init__(self, bucket, **kwargs):
        self.__logger = logging.getLogger(__name__)

        self._bucket_template = bucket
        self._s3 = boto3.resource('s3', **kwargs)

    def _get_bucket_name(self, digest):
        return self._bucket_template.format(digest=digest)

    def has_blob(self, digest):
        self.__logger.debug("Checking for blob: [{}]".format(digest))
        try:
            self._s3.Object(self._get_bucket_name(digest.hash),
                            digest.hash + '_' + str(digest.size_bytes)).load()
        except ClientError as e:
            if e.response['Error']['Code'] not in ['404', 'NoSuchKey']:
                raise
            return False
        return True

    def get_blob(self, digest):
        self.__logger.debug("Getting blob: [{}]".format(digest))
        try:
            obj = self._s3.Object(self._get_bucket_name(digest.hash),
                                  digest.hash + '_' + str(digest.size_bytes))
            return io.BytesIO(obj.get()['Body'].read())
        except ClientError as e:
            if e.response['Error']['Code'] not in ['404', 'NoSuchKey']:
                raise
            return None

    def delete_blob(self, digest):
        self.__logger.debug("Deleting blob: [{}]".format(digest))
        try:
            self._s3.Object(self._get_bucket_name(digest.hash),
                            digest.hash + '_' + str(digest.size_bytes)).delete()
        except ClientError as e:
            if e.response['Error']['Code'] not in ['404', 'NoSuchKey']:
                raise

    def begin_write(self, _digest):
        # TODO use multipart API for large blobs?
        return io.BytesIO()

    def commit_write(self, digest, write_session):
        self.__logger.debug("Writing blob: [{}]".format(digest))
        write_session.seek(0)
        self._s3.Bucket(self._get_bucket_name(digest.hash)) \
                .upload_fileobj(write_session,
                                digest.hash + '_' + str(digest.size_bytes))
        write_session.close()
