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
Storage Instances
=========
Instances of CAS and ByteStream
"""

import logging

from buildgrid._exceptions import InvalidArgumentError, NotFoundError, OutOfRangeError
from buildgrid._protos.google.bytestream import bytestream_pb2
from buildgrid._protos.build.bazel.remote.execution.v2 import remote_execution_pb2 as re_pb2
from buildgrid.settings import HASH, HASH_LENGTH
from buildgrid.utils import get_hash_type


class ContentAddressableStorageInstance:

    def __init__(self, storage):
        self.__logger = logging.getLogger(__name__)

        self._storage = storage

    def register_instance_with_server(self, instance_name, server):
        server.add_cas_instance(self, instance_name)

    def hash_type(self):
        return get_hash_type()

    def max_batch_total_size_bytes(self):
        # TODO: link with max size
        # Should be added from settings in MR !119
        return 2000000

    def symlink_absolute_path_strategy(self):
        # Currently this strategy is hardcoded into BuildGrid
        # With no setting to reference
        return re_pb2.CacheCapabilities().DISALLOWED

    def find_missing_blobs(self, blob_digests):
        storage = self._storage
        return re_pb2.FindMissingBlobsResponse(
            missing_blob_digests=storage.missing_blobs(blob_digests))

    def batch_update_blobs(self, requests):
        storage = self._storage
        store = []
        for request_proto in requests:
            store.append((request_proto.digest, request_proto.data))

        response = re_pb2.BatchUpdateBlobsResponse()
        statuses = storage.bulk_update_blobs(store)

        for (digest, _), status in zip(store, statuses):
            response_proto = response.responses.add()
            response_proto.digest.CopyFrom(digest)
            response_proto.status.CopyFrom(status)

        return response


class ByteStreamInstance:

    BLOCK_SIZE = 1 * 1024 * 1024  # 1 MB block size

    def __init__(self, storage):
        self.__logger = logging.getLogger(__name__)

        self._storage = storage

    def register_instance_with_server(self, instance_name, server):
        server.add_bytestream_instance(self, instance_name)

    def read(self, digest_hash, digest_size, read_offset, read_limit):
        if len(digest_hash) != HASH_LENGTH or not digest_size.isdigit():
            raise InvalidArgumentError("Invalid digest [{}/{}]"
                                       .format(digest_hash, digest_size))

        digest = re_pb2.Digest(hash=digest_hash, size_bytes=int(digest_size))

        # Check the given read offset and limit.
        if read_offset < 0 or read_offset > digest.size_bytes:
            raise OutOfRangeError("Read offset out of range")

        elif read_limit == 0:
            bytes_remaining = digest.size_bytes - read_offset

        elif read_limit > 0:
            bytes_remaining = read_limit

        else:
            raise InvalidArgumentError("Negative read_limit is invalid")

        # Read the blob from storage and send its contents to the client.
        result = self._storage.get_blob(digest)
        if result is None:
            raise NotFoundError("Blob not found")

        elif result.seekable():
            result.seek(read_offset)

        else:
            result.read(read_offset)

        while bytes_remaining > 0:
            yield bytestream_pb2.ReadResponse(
                data=result.read(min(self.BLOCK_SIZE, bytes_remaining)))
            bytes_remaining -= self.BLOCK_SIZE

    def write(self, digest_hash, digest_size, first_block, other_blocks):
        if len(digest_hash) != HASH_LENGTH or not digest_size.isdigit():
            raise InvalidArgumentError("Invalid digest [{}/{}]"
                                       .format(digest_hash, digest_size))

        digest = re_pb2.Digest(hash=digest_hash, size_bytes=int(digest_size))

        write_session = self._storage.begin_write(digest)

        # Start the write session and write the first request's data.
        write_session.write(first_block)

        computed_hash = HASH(first_block)
        bytes_written = len(first_block)

        # Handle subsequent write requests.
        for next_block in other_blocks:
            write_session.write(next_block)

            computed_hash.update(next_block)
            bytes_written += len(next_block)

        # Check that the data matches the provided digest.
        if bytes_written != digest.size_bytes:
            raise NotImplementedError("Cannot close stream before finishing write")

        elif computed_hash.hexdigest() != digest.hash:
            raise InvalidArgumentError("Data does not match hash")

        self._storage.commit_write(digest, write_session)

        return bytestream_pb2.WriteResponse(committed_size=bytes_written)
