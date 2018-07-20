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
Server command
=================

Create a BuildGrid server.
"""


import asyncio
import click
import logging

from buildgrid.server import build_grid_server
from buildgrid.server.cas.storage.disk import DiskStorage
from buildgrid.server.cas.storage.lru_memory_cache import LRUMemoryCache
from buildgrid.server.cas.storage.s3 import S3Storage
from buildgrid.server.cas.storage.with_cache import WithCacheStorage

from ..cli import pass_context

@click.group(short_help = "Start local server")
@pass_context
def cli(context):
    context.logger = logging.getLogger(__name__)
    context.logger.info("BuildGrid server booting up")

@cli.command('start', short_help='Starts server')
@click.option('--port', default='50051')
@click.option('--cas',
              type=click.Choice(('lru', 's3', 'disk', 'with-cache')),
              help='CAS storage type to use.')
@click.option('--cas-cache',
              type=click.Choice(('lru', 's3', 'disk')),
              help='For --cas=with-cache, the CAS storage to use as the cache.')
@click.option('--cas-fallback',
              type=click.Choice(('lru', 's3', 'disk')),
              help='For --cas=with-cache, the CAS storage to use as the fallback.')
@click.option('--cas-lru-size', help='For --cas=lru, the LRU cache\'s memory limit.')
@click.option('--cas-s3-bucket', help='For --cas=s3, the bucket name.')
@click.option('--cas-s3-endpoint', help='For --cas=s3, the endpoint URI.')
@click.option('--cas-disk-directory',
              type=click.Path(file_okay=False, dir_okay=True, writable=True),
              help='For --cas=disk, the folder to store CAS blobs in.')
@pass_context
def start(context, port, cas, **cas_args):
    context.logger.info("Starting on port {}".format(port))

    loop = asyncio.get_event_loop()

    cas_storage = _make_cas_storage(context, cas, cas_args)
    if cas_storage is None:
        context.logger.info("Running without CAS")
    server = build_grid_server.BuildGridServer(port, cas_storage=cas_storage)

    try:
        asyncio.ensure_future(server.start())
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        loop.run_until_complete(server.stop())
        loop.close()

@cli.command('stop', short_help='Stops server')
@pass_context
def stop(context):
    context.logger.error("Not implemented yet")

def _make_cas_storage(context, cas_type, cas_args):
    """Returns the storage provider corresponding to the given `cas_type`,
    or None if the provider cannot be created.
    """
    if cas_type == "lru":
        if cas_args["cas_lru_size"] is None:
            context.logger.error("--cas-lru-size is required for LRU CAS")
            return None
        try:
            size = _parse_size(cas_args["cas_lru_size"])
        except ValueError:
            context.logger.error('Invalid LRU size "{0}"'.format(cas_args["cas_lru_size"]))
            return None
        return LRUMemoryCache(size)
    elif cas_type == "s3":
        if cas_args["cas_s3_bucket"] is None:
            context.logger.error("--cas-s3-bucket is required for S3 CAS")
            return None
        if cas_args["cas_s3_endpoint"] is not None:
            return S3Storage(cas_args["cas_s3_bucket"],
                             endpoint_url=cas_args["cas_s3_endpoint"])
        return S3Storage(cas_args["cas_s3_bucket"])
    elif cas_type == "disk":
        if cas_args["cas_disk_directory"] is None:
            context.logger.error("--cas-disk-directory is required for disk CAS")
            return None
        return DiskStorage(cas_args["cas_disk_directory"])
    elif cas_type == "with-cache":
        cache = _make_cas_storage(context, cas_args["cas_cache"], cas_args)
        fallback = _make_cas_storage(context, cas_args["cas_fallback"], cas_args)
        if cache is None:
            context.logger.error("Missing cache provider for --cas=with-cache")
            return None
        elif fallback is None:
            context.logger.error("Missing fallback provider for --cas=with-cache")
            return None
        return WithCacheStorage(cache, fallback)
    elif cas_type is None:
        return None

_SIZE_PREFIXES = {'k': 2 ** 10, 'm': 2 ** 20, 'g': 2 ** 30, 't': 2 ** 40}
def _parse_size(size):
    """Convert a string containing a size in bytes (e.g. '2GB') to a number."""
    size = size.lower()
    if size[-1] == 'b':
        size = size[:-1]
    if size[-1] in _SIZE_PREFIXES:
        return int(size[:-1]) * _SIZE_PREFIXES[size[-1]]
    return int(size)
