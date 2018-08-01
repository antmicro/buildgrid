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
Scheduler
=========
Schedules jobs.
"""

from collections import deque

from buildgrid._protos.google.longrunning import operations_pb2

from .job import ExecuteStage, LeaseState

class Scheduler():

    MAX_N_TRIES = 5

    def __init__(self):
        self.jobs = {}
        self.queue = deque()

    def register_client(self, name, queue):
        self.jobs[name].register_client(queue)

    def unregister_client(self, name, queue):
        job = self.jobs[name]
        job.unregister_client(queue)
        if job.check_job_finished():
            del self.jobs[name]

    def append_job(self, job):
        job.update_execute_stage(ExecuteStage.QUEUED)
        self.jobs[job.name] = job
        self.queue.append(job)

    def retry_job(self, name):
        job = self.jobs[name]

        if job.n_tries >= self.MAX_N_TRIES:
            # TODO: Decide what to do with these jobs
            job.update_execute_stage(ExecuteStage.COMPLETED)
        else:
            job.update_execute_stage(ExecuteStage.QUEUED)
            job.n_tries += 1
            self.queue.appendleft(job)

        self.jobs[name] = job

    def create_job(self):
        if len(self.queue) > 0:
            job = self.queue.popleft()
            job.update_execute_stage(ExecuteStage.EXECUTING)
            self.jobs[job.name] = job
            return job

    def job_complete(self, name, result):
        job = self.jobs[name]
        job.result = result
        job.update_execute_stage(ExecuteStage.COMPLETED)
        self.jobs[name] = job

    def get_operations(self):
        response = operations_pb2.ListOperationsResponse()
        for v in self.jobs.values():
            response.operations.extend([v.get_operation()])
        return response

    def update_lease(self, lease):
        name = lease.id
        job = self.jobs.get(name)
        state = lease.state

        if state   == LeaseState.LEASE_STATE_UNSPECIFIED.value:
            create_job = self.create_job()
            if create_job is None:
                # No job? Return lease.
                return lease
            else:
                job = create_job
                job.create_lease()

        elif state == LeaseState.PENDING.value:
            job.lease = lease

        elif state == LeaseState.ACTIVE.value:
            job.lease = lease

        elif state == LeaseState.COMPLETED.value:
            self.job_complete(job.name, lease.result)

            create_job = self.create_job()
            if create_job is None:
                # Docs say not to use this state though if job has
                # completed and no more jobs, then use this state to stop
                # job being processed again
                job.lease = lease
                job.lease.state = LeaseState.LEASE_STATE_UNSPECIFIED.value
            else:
                job = create_job
                job.lease = job.create_lease()

        elif state == LeaseState.CANCELLED.value:
            job.lease = lease

        else:
            raise Exception("Unknown state: {}".format(state))

        self.jobs[name] = job
        return job.lease

    def cancel_session(self, name):
        job = self.jobs[name]
        state = job.lease.state
        if state == LeaseState.PENDING.value or \
           state == LeaseState.ACTIVE.value:
            self.retry_job(name)
