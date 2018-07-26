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

import grpc
import pytest
import uuid

from unittest import mock

from grpc._server import _Context
from google.devtools.remoteexecution.v1test import remote_execution_pb2
from google.longrunning import operations_pb2
from google.protobuf import any_pb2

from buildgrid.server import scheduler, job
from buildgrid.server.execution import execution_instance, execution_service

@pytest.fixture
def context():
    cxt = mock.MagicMock(spec = _Context)
    yield cxt

@pytest.fixture
def schedule():
    yield scheduler.Scheduler()

@pytest.fixture
def execution(schedule):
    yield execution_instance.ExecutionInstance(schedule)

# Instance to test
@pytest.fixture
def instance(execution):
    yield execution_service.ExecutionService(execution)

@pytest.mark.parametrize("skip_cache_lookup", [True, False])
def test_execute(skip_cache_lookup, instance, context):
    action = remote_execution_pb2.Action()
    action.command_digest.hash = 'zhora'

    request = remote_execution_pb2.ExecuteRequest(instance_name = '',
                                                  action = action,
                                                  skip_cache_lookup = skip_cache_lookup)

    result = instance.Execute(request, context)

    assert isinstance(result, operations_pb2.Operation)

    if skip_cache_lookup is False:
        context.set_code.assert_called_once_with(grpc.StatusCode.UNIMPLEMENTED)
    else:
        metadata = remote_execution_pb2.ExecuteOperationMetadata()
        _unpack_any(result.metadata, metadata)
        assert metadata.stage == job.ExecuteStage.QUEUED.value
        assert uuid.UUID(result.name, version=4)
        assert result.done is False

def _unpack_any(unpack_from, to):
    any = any_pb2.Any()
    any.CopyFrom(unpack_from)
    any.Unpack(to)
    return to