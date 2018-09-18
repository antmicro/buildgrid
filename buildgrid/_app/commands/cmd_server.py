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
Server command
=================

Create a BuildGrid server.
"""

import asyncio
import logging
import sys

import click

from buildgrid.server.instance import BuildGridServer

from ..cli import pass_context
from ..settings import parser


@click.group(name='server', short_help="Start a local server instance.")
@pass_context
def cli(context):
    context.logger = logging.getLogger(__name__)


@cli.command('start', short_help="Setup a new server instance.")
@click.argument('CONFIG', type=click.Path(file_okay=True, dir_okay=False, writable=False))
@pass_context
def start(context, config):
    with open(config) as f:
        settings = parser.get_parser().safe_load(f)

    try:
        server = _create_server_from_config(settings)

    except KeyError as e:
        click.echo("ERROR: Could not parse config: {}.\n".format(str(e)), err=True)
        sys.exit(-1)

    loop = asyncio.get_event_loop()
    try:
        server.start()
        loop.run_forever()

    except KeyboardInterrupt:
        pass

    finally:
        context.logger.info("Stopping server")
        server.stop()
        loop.close()


def _create_server_from_config(config):
    server_settings = config['server']

    server = BuildGridServer()

    try:
        for channel in server_settings:
            server.add_port(channel.address, channel.credentials)

    except (AttributeError, TypeError) as e:
        click.echo("Error: Use list of `!channel` tags: {}.\n".format(e), err=True)
        sys.exit(-1)

    instances = config['instances']
    for instance in instances:
        instance_name = instance['name']
        services = instance['services']

        for service in services:
            service.register_instance_with_server(instance_name, server)

    return server
