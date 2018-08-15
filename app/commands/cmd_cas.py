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
Execute command
=================

Request work to be executed and monitor status of jobs.
"""

import logging
import click
import grpc

from buildgrid.utils import merkle_maker, create_digest
from buildgrid._protos.build.bazel.remote.execution.v2 import remote_execution_pb2, remote_execution_pb2_grpc

from ..cli import pass_context


@click.group(short_help='Interact with the CAS')
@click.option('--port', default='50051')
@click.option('--host', default='localhost')
@pass_context
def cli(context, host, port):
    context.logger = logging.getLogger(__name__)
    context.logger.info("Starting on port {}".format(port))

    context.channel = grpc.insecure_channel('{}:{}'.format(host, port))
    context.port = port


@cli.command('upload-files', short_help='Upload files')
@click.argument('files', nargs=-1, type=click.File('rb'))
@click.option('--instance-name', default='testing')
@pass_context
def upload_files(context, files, instance_name):
    stub = remote_execution_pb2_grpc.ContentAddressableStorageStub(context.channel)

    requests = []
    for file in files:
        chunk = file.read()
        requests.append(remote_execution_pb2.BatchUpdateBlobsRequest.Request(
            digest=create_digest(chunk), data=chunk))

    request = remote_execution_pb2.BatchUpdateBlobsRequest(instance_name=instance_name,
                                                           requests=requests)

    context.logger.info("Sending: {}".format(request))
    response = stub.BatchUpdateBlobs(request)
    context.logger.info("Response: {}".format(response))


@cli.command('upload-dir', short_help='Upload files')
@click.argument('directory')
@click.option('--instance-name', default='testing')
@pass_context
def upload_dir(context, directory, instance_name):
    context.logger.info("Uploading directory to cas")
    stub = remote_execution_pb2_grpc.ContentAddressableStorageStub(context.channel)

    requests = []

    for chunk, file_digest in merkle_maker(directory):
        requests.append(remote_execution_pb2.BatchUpdateBlobsRequest.Request(
            digest=file_digest, data=chunk))

    request = remote_execution_pb2.BatchUpdateBlobsRequest(instance_name=instance_name,
                                                           requests=requests)

    context.logger.info("Request:\n{}".format(request))
    response = stub.BatchUpdateBlobs(request)
    context.logger.info("Response:\n{}".format(response))
