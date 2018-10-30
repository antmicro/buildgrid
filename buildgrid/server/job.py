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


from datetime import datetime
import logging
import uuid

from google.protobuf import duration_pb2, timestamp_pb2

from buildgrid._enums import LeaseState, OperationStage
from buildgrid._exceptions import CancelledError
from buildgrid._protos.build.bazel.remote.execution.v2 import remote_execution_pb2
from buildgrid._protos.google.devtools.remoteworkers.v1test2 import bots_pb2
from buildgrid._protos.google.longrunning import operations_pb2
from buildgrid._protos.google.rpc import code_pb2


class Job:

    def __init__(self, action, action_digest, priority=0):
        self.__logger = logging.getLogger(__name__)

        self._name = str(uuid.uuid4())
        self._priority = priority
        self._action = remote_execution_pb2.Action()
        self._operation = operations_pb2.Operation()
        self._lease = None

        self.__execute_response = None
        self.__operation_metadata = remote_execution_pb2.ExecuteOperationMetadata()

        self.__queued_timestamp = timestamp_pb2.Timestamp()
        self.__queued_time_duration = duration_pb2.Duration()
        self.__worker_start_timestamp = timestamp_pb2.Timestamp()
        self.__worker_completed_timestamp = timestamp_pb2.Timestamp()

        self.__operation_message_queues = {}
        self.__operation_cancelled = False
        self.__lease_cancelled = False

        self.__operation_metadata.action_digest.CopyFrom(action_digest)
        self.__operation_metadata.stage = OperationStage.UNKNOWN.value

        self._action.CopyFrom(action)
        self._do_not_cache = self._action.do_not_cache
        self._operation.name = self._name
        self._operation.done = False
        self._n_tries = 0

    def __lt__(self, other):
        try:
            return self.priority < other.priority
        except AttributeError:
            return NotImplemented

    def __le__(self, other):
        try:
            return self.priority <= other.priority
        except AttributeError:
            return NotImplemented

    def __eq__(self, other):
        if isinstance(other, Job):
            return self.name == other.name
        return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __gt__(self, other):
        try:
            return self.priority > other.priority
        except AttributeError:
            return NotImplemented

    def __ge__(self, other):
        try:
            return self.priority >= other.priority
        except AttributeError:
            return NotImplemented

    # --- Public API ---

    @property
    def name(self):
        return self._name

    @property
    def priority(self):
        return self._priority

    @property
    def do_not_cache(self):
        return self._do_not_cache

    @property
    def action(self):
        return self._action

    @property
    def action_digest(self):
        return self.__operation_metadata.action_digest

    @property
    def action_result(self):
        if self.__execute_response is not None:
            return self.__execute_response.result
        else:
            return None

    @property
    def holds_cached_action_result(self):
        if self.__execute_response is not None:
            return self.__execute_response.cached_result
        else:
            return False

    @property
    def operation(self):
        return self._operation

    @property
    def operation_stage(self):
        return OperationStage(self.__operation_metadata.state)

    @property
    def lease(self):
        return self._lease

    @property
    def lease_state(self):
        if self._lease is not None:
            return LeaseState(self._lease.state)
        else:
            return None

    @property
    def lease_cancelled(self):
        return self.__lease_cancelled

    @property
    def n_tries(self):
        return self._n_tries

    @property
    def n_clients(self):
        return len(self.__operation_message_queues)

    def register_operation_peer(self, peer, message_queue):
        """Subscribes to the job's :class:`Operation` stage changes.

        Queues this :object:`Job` instance.

        Args:
            peer (str): a unique string identifying the client.
            message_queue (queue.Queue): the event queue to register.
        """
        if peer not in self.__operation_message_queues:
            self.__operation_message_queues[peer] = message_queue

        message_queue.put(self)

    def unregister_operation_peer(self, peer):
        """Unsubscribes to the job's :class:`Operation` stage change.

        Args:
            peer (str): a unique string identifying the client.
        """
        if peer not in self.__operation_message_queues:
            del self.__operation_message_queues[peer]

    def set_cached_result(self, action_result):
        """Allows specifying an action result form the action cache for the job.
        """
        self.__execute_response = remote_execution_pb2.ExecuteResponse()
        self.__execute_response.result.CopyFrom(action_result)
        self.__execute_response.cached_result = True

    def create_lease(self):
        """Emits a new :class:`Lease` for the job.

        Only one :class:`Lease` can be emitted for a given job. This method
        should only be used once, any furhter calls are ignored.
        """
        if self.__operation_cancelled:
            return None
        elif self._lease is not None:
            return None

        self._lease = bots_pb2.Lease()
        self._lease.id = self._name
        self._lease.payload.Pack(self.__operation_metadata.action_digest)
        self._lease.state = LeaseState.PENDING.value

        return self._lease

    def update_lease_state(self, state, status=None, result=None):
        """Operates a state transition for the job's current :class:Lease.

        Args:
            state (LeaseState): the lease state to transition to.
            status (google.rpc.Status): the lease execution status, only
                required if `state` is `COMPLETED`.
            result (google.protobuf.Any): the lease execution result, only
                required if `state` is `COMPLETED`.
        """
        if state.value == self._lease.state:
            return

        self._lease.state = state.value

        if self._lease.state == LeaseState.PENDING.value:
            self.__worker_start_timestamp.Clear()
            self.__worker_completed_timestamp.Clear()

            self._lease.status.Clear()
            self._lease.result.Clear()

        elif self._lease.state == LeaseState.ACTIVE.value:
            self.__worker_start_timestamp.GetCurrentTime()

        elif self._lease.state == LeaseState.COMPLETED.value:
            self.__worker_completed_timestamp.GetCurrentTime()

            action_result = remote_execution_pb2.ActionResult()

            # TODO: Make a distinction between build and bot failures!
            if status.code != code_pb2.OK:
                self._do_not_cache = True

            if result is not None:
                assert result.Is(action_result.DESCRIPTOR)
                result.Unpack(action_result)

            action_metadata = action_result.execution_metadata
            action_metadata.queued_timestamp.CopyFrom(self.__queued_timestamp)
            action_metadata.worker_start_timestamp.CopyFrom(self.__worker_start_timestamp)
            action_metadata.worker_completed_timestamp.CopyFrom(self.__worker_completed_timestamp)

            self.__execute_response = remote_execution_pb2.ExecuteResponse()
            self.__execute_response.result.CopyFrom(action_result)
            self.__execute_response.cached_result = False
            self.__execute_response.status.CopyFrom(status)

    def cancel_lease(self):
        """Triggers a job's :class:Lease cancellation.

        This will not cancel the job's :class:Operation.
        """
        self.__lease_cancelled = True
        if self._lease is not None:
            self.update_lease_state(LeaseState.CANCELLED)

    def delete_lease(self):
        """Discard the job's :class:Lease."""
        self.__worker_start_timestamp.Clear()
        self.__worker_completed_timestamp.Clear()

        self._lease = None

    def update_operation_stage(self, stage):
        """Operates a stage transition for the job's :class:Operation.

        Args:
            stage (OperationStage): the operation stage to transition to.
        """
        if stage.value == self.__operation_metadata.stage:
            return

        self.__operation_metadata.stage = stage.value

        if self.__operation_metadata.stage == OperationStage.QUEUED.value:
            if self.__queued_timestamp.ByteSize() == 0:
                self.__queued_timestamp.GetCurrentTime()
            self._n_tries += 1

        elif self.__operation_metadata.stage == OperationStage.EXECUTING.value:
            queue_in, queue_out = self.__queued_timestamp.ToDatetime(), datetime.now()
            self.__queued_time_duration.FromTimedelta(queue_out - queue_in)

        elif self.__operation_metadata.stage == OperationStage.COMPLETED.value:
            if self.__execute_response is not None:
                self._operation.response.Pack(self.__execute_response)
            self._operation.done = True

        self._operation.metadata.Pack(self.__operation_metadata)

        for message_queue in self.__operation_message_queues.values():
            message_queue.put(self)

    def check_operation_status(self):
        """Reports errors on unexpected job's :class:Operation state.

        Raises:
            CancelledError: if the job's :class:Operation was cancelled.
        """
        if self.__operation_cancelled:
            raise CancelledError(self.__execute_response.status.message)

    def cancel_operation(self):
        """Triggers a job's :class:Operation cancellation.

        This will also cancel any job's :class:Lease that may have been issued.
        """
        self.__operation_cancelled = True
        if self._lease is not None:
            self.cancel_lease()

        self.__execute_response = remote_execution_pb2.ExecuteResponse()
        self.__execute_response.status.code = code_pb2.CANCELLED
        self.__execute_response.status.message = "Operation cancelled by client."

        self.update_operation_stage(OperationStage.COMPLETED)

    # --- Public API: Monitoring ---

    def query_queue_time(self):
        return self.__queued_time_duration.ToTimedelta()

    def query_n_retries(self):
        return self._n_tries - 1 if self._n_tries > 0 else 0
