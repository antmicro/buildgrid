# Copyright (C) 2018 Codethink Limited
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
#
# Authors:
#        Finn Ball <finn.ball@codethink.co.uk>

"""
Execute command
=================

Request work to be executed and monitor status of jobs.
"""

import click
import grpc

from ...server import build_grid_server
from ..cli import pass_context

from google.devtools.remoteexecution.v1test import remote_execution_pb2, remote_execution_pb2_grpc
from google.devtools.remoteexecution.v1test.remote_execution_pb2 import ExecuteOperationMetadata
from google.longrunning import operations_pb2, operations_pb2_grpc
from google.protobuf import any_pb2

@click.group(short_help = "Simple execute client")
@click.option('--port', default='50051')
@pass_context
def cli(context, port):
    context.vlog("Verbose mode!")
    context.log("Starting on port {}".format(port))

    context.channel = grpc.insecure_channel('localhost:{}'.format(port))
    context.port = port

@cli.command('request', short_help='Send a dummy action')
@click.option('--instance-name', default="testing")
@pass_context
def request(context, instance_name):
    context.log("Sending execution request...\n")
    stub = remote_execution_pb2_grpc.ExecutionStub(context.channel)

    action = remote_execution_pb2.Action(command_digest = None,
                                         input_root_digest = None,
                                         output_files = [],
                                         output_directories = None,
                                         platform = None,
                                         timeout = None,
                                         do_not_cache = True)

    request = remote_execution_pb2.ExecuteRequest(instance_name = instance_name,
                                                  action = action,
                                                  skip_cache_lookup = True)
    try:
        response = stub.Execute(request)

    except Exception as e:
        context.log(e)

    context.log("Response name: {}".format(response.name))

@cli.command('status', short_help='Get the status of an operation')
@click.argument('operation-name')
@pass_context
def operation_status(context, operation_name):
    context.log("Getting operation status...\n")
    stub = operations_pb2_grpc.OperationsStub(context.channel)

    request = operations_pb2.GetOperationRequest(name=operation_name)

    try:
        response = stub.GetOperation(request)
        _log_operation(context, response)

    except Exception as e:
        context.log(e)

@cli.command('list', short_help='List operations')
@pass_context
def list_operations(context):
    context.log("Getting list of operations...\n")
    stub = operations_pb2_grpc.OperationsStub(context.channel)

    request = operations_pb2.ListOperationsRequest()

    try:
        response = stub.ListOperations(request)

    except Exception as e:
        context.log(e)

    for op in response.operations:
        _log_operation(context, op)
    
def _log_operation(context, operation):
    op_any = any_pb2.Any()
    op_meta = ExecuteOperationMetadata()
    op_any.CopyFrom(operation.metadata)
    op_any.Unpack(op_meta)

    context.log("Name  : {}".format(operation.name))
    context.log("Done  : {}".format(operation.done))
    context.log("Stage : {}\n".format(ExecuteOperationMetadata.Stage.Name(op_meta.stage)))
