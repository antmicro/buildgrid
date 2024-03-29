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
Action Cache
============

Implements an in-memory action Cache
"""

import logging

from ..referencestorage.storage import ReferenceCache
from ...utils import get_hash_type


class ActionCache(ReferenceCache):

    def __init__(self, storage, max_cached_refs, allow_updates=True, cache_failed_actions=True):
        """ Initialises a new ActionCache instance.

        Args:
            storage (StorageABC): storage backend instance to be used. Passed to ReferenceCache
            max_cached_refs (int): maximum number of entries to be stored. Passed to ReferenceCache
            allow_updates (bool): allow the client to write to storage. Passed to ReferenceCache
            cache_failed_actions (bool): cache actions with non-zero exit codes.
        """
        super().__init__(storage, max_cached_refs, allow_updates)

        self.__logger = logging.getLogger(__name__)

        self._instance_name = None

        self._cache_failed_actions = cache_failed_actions

    # --- Public API ---

    @property
    def instance_name(self):
        return self._instance_name

    @instance_name.setter
    def instance_name(self, instance_name):
        self._instance_name = instance_name

    def hash_type(self):
        return get_hash_type()

    def register_instance_with_server(self, instance_name, server):
        """Names and registers the action-cache instance with a given server."""
        if self._instance_name is None:
            server.add_action_cache_instance(self, instance_name)

            self._instance_name = instance_name

        else:
            raise AssertionError("Instance already registered")

    def get_action_result(self, action_digest):
        """Retrieves the cached result for an action."""
        key = self._get_key(action_digest)

        return self.get_action_reference(key)

    def update_action_result(self, action_digest, action_result):
        """Stores in cache a result for an action."""
        if self._cache_failed_actions or action_result.exit_code == 0:
            key = self._get_key(action_digest)

            self.update_reference(key, action_result)

            self.__logger.info("Result cached for action [%s/%s]",
                               action_digest.hash, action_digest.size_bytes)

    # --- Private API ---

    def _get_key(self, action_digest):
        return (action_digest.hash, action_digest.size_bytes)
