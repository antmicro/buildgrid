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

import logging
import uuid

from enum import Enum

from buildgrid._protos.build.bazel.remote.execution.v2.remote_execution_pb2 import ExecuteOperationMetadata
from buildgrid._protos.build.bazel.remote.execution.v2.remote_execution_pb2 import ExecuteResponse
from buildgrid._protos.google.devtools.remoteworkers.v1test2 import bots_pb2, worker_pb2
from buildgrid._protos.google.longrunning import operations_pb2
from google.protobuf import any_pb2


class ExecuteStage(Enum):
    UNKNOWN = ExecuteOperationMetadata.Stage.Value('UNKNOWN')

    # Checking the result against the cache.
    CACHE_CHECK = ExecuteOperationMetadata.Stage.Value('CACHE_CHECK')

    # Currently idle, awaiting a free machine to execute.
    QUEUED = ExecuteOperationMetadata.Stage.Value('QUEUED')

    # Currently being executed by a worker.
    EXECUTING = ExecuteOperationMetadata.Stage.Value('EXECUTING')

    # Finished execution.
    COMPLETED = ExecuteOperationMetadata.Stage.Value('COMPLETED')


class BotStatus(Enum):
    BOT_STATUS_UNSPECIFIED = bots_pb2.BotStatus.Value('BOT_STATUS_UNSPECIFIED')

    # The bot is healthy, and will accept leases as normal.
    OK = bots_pb2.BotStatus.Value('OK')

    # The bot is unhealthy and will not accept new leases.
    UNHEALTHY = bots_pb2.BotStatus.Value('UNHEALTHY')

    # The bot has been asked to reboot the host.
    HOST_REBOOTING = bots_pb2.BotStatus.Value('HOST_REBOOTING')

    # The bot has been asked to shut down.
    BOT_TERMINATING = bots_pb2.BotStatus.Value('BOT_TERMINATING')


class LeaseState(Enum):
    LEASE_STATE_UNSPECIFIED = bots_pb2.LeaseState.Value('LEASE_STATE_UNSPECIFIED')

    # The server expects the bot to accept this lease.
    PENDING = bots_pb2.LeaseState.Value('PENDING')

    # The bot has accepted this lease.
    ACTIVE = bots_pb2.LeaseState.Value('ACTIVE')

    # The bot is no longer leased.
    COMPLETED = bots_pb2.LeaseState.Value('COMPLETED')

    # The bot should immediately release all resources associated with the lease.
    CANCELLED = bots_pb2.LeaseState.Value('CANCELLED')


class Job():

    def __init__(self, action_digest, do_not_cache=False, message_queue=None):
        self.lease = None
        self.logger = logging.getLogger(__name__)
        self.result = None
        self.result_cached = False

        self._action_digest = action_digest
        self._do_not_cache = do_not_cache
        self._execute_stage = ExecuteStage.UNKNOWN
        self._n_tries = 0
        self._name = str(uuid.uuid4())
        self._operation = operations_pb2.Operation(name=self._name)
        self._operation_update_queues = []

        if message_queue is not None:
            self.register_client(message_queue)

    @property
    def name(self):
        return self._name

    @property
    def action_digest(self):
        return self._action_digest

    @property
    def do_not_cache(self):
        return self._do_not_cache

    def check_job_finished(self):
        if not self._operation_update_queues:
            return self._operation.done
        return False

    def register_client(self, queue):
        self._operation_update_queues.append(queue)
        queue.put(self.get_operation())

    def unregister_client(self, queue):
        self._operation_update_queues.remove(queue)

    def get_operation(self):
        self._operation.metadata.CopyFrom(self._pack_any(self.get_operation_meta()))
        if self.result is not None:
            self._operation.done = True
            response = ExecuteResponse()
            self.result.Unpack(response.result)
            response.cached_result = self.result_cached
            self._operation.response.CopyFrom(self._pack_any(response))

        return self._operation

    def get_operation_meta(self):
        meta = ExecuteOperationMetadata()
        meta.stage = self._execute_stage.value
        meta.action_digest.CopyFrom(self._action_digest)

        return meta

    def create_lease(self):
        action_digest = self._pack_any(self._action_digest)

        lease = bots_pb2.Lease(id=self.name,
                               payload=action_digest,
                               state=LeaseState.PENDING.value)
        self.lease = lease
        return lease

    def get_operations(self):
        return operations_pb2.ListOperationsResponse(operations=[self.get_operation()])

    def update_execute_stage(self, stage):
        self._execute_stage = stage
        for queue in self._operation_update_queues:
            queue.put(self.get_operation())

    def _pack_any(self, pack):
        any = any_pb2.Any()
        any.Pack(pack)
        return any
