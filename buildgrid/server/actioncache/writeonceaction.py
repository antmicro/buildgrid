# Copyright (C) 2019 Bloomberg LP
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
Write Once Action Cache
===================

Only allows an action digest's result to be written to once.
Any subsequent requests will raise a UpdateNotAllowedError

"""

import logging

from buildgrid._exceptions import NotFoundError, UpdateNotAllowedError


class WriteOnceActionCache:

    def __init__(self, action_cache):
        self.__logger = logging.getLogger(__name__)
        self._action_cache = action_cache

    @property
    def instance_name(self):
        return self._action_cache.instance_name

    @instance_name.setter
    def instance_name(self, instance_name):
        self._action_cache.instance_name = instance_name

    @property
    def allow_updates(self):
        return self._action_cache.allow_updates

    def hash_type(self):
        return self._action_cache.hash_type()

    def register_instance_with_server(self, instance_name, server):
        """Names and registers the action-cache instance with a given server."""
        if self._action_cache.instance_name is None:
            server.add_action_cache_instance(self, instance_name)
            self.instance_name = instance_name
        else:
            raise AssertionError("WriteOnceActionCache underlying ActionCache already registered "
                                 "as a service. Should initialize but not expose that ActionCache."
                                 "(Move out of `services:` config section)")
        # Otherwise the instance has already registered itself with the server

    def get_action_result(self, action_digest):
        """Retrieves the cached ActionResult for the given Action digest.

        Args:
            action_digest: The digest to get the result for

        Returns:
            The cached ActionResult matching the given key or raises
            NotFoundError.
        """
        return self._action_cache.get_action_result(action_digest)

    def update_action_result(self, action_digest, action_result):
        """
            Stores the result in cache for the given key only if that
            value hasn't already been set.

            Otherwise, it raises a UpdateNotAllowedError

        Args:
            action_digest (Digest): digest of Action to update
            action_result (Digest): digest of ActionResult to store.
        """
        try:
            self._action_cache.get_action_result(action_digest)
            # This should throw NotFoundError or actually exist
            self.__logger.warning("Result already cached for action [%s/%s], "
                                  "WriteOnceActionCache won't overwrite it to "
                                  "the new action_result=[%s]",
                                  action_digest.hash, action_digest.size_bytes,
                                  action_result)

            raise UpdateNotAllowedError("Result already stored for this action digest;"
                                        "WriteOnceActionCache doesn't allow updates.")
        except NotFoundError:
            self._action_cache.update_action_result(action_digest, action_result)
