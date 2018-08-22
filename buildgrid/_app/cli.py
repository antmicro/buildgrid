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
CommandLineInterface
===================

Any files in the commands/ folder with the name cmd_*.py
will be attempted to be imported.
"""

import os
import logging

import click

from . import _logging

CONTEXT_SETTINGS = dict(auto_envvar_prefix='BUILDGRID')


class Context:

    def __init__(self):
        self.verbose = False
        self.home = os.getcwd()


pass_context = click.make_pass_decorator(Context, ensure=True)
cmd_folder = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                          'commands'))


class BuildGridCLI(click.MultiCommand):

    def list_commands(self, context):
        commands = []
        for filename in os.listdir(cmd_folder):
            if filename.endswith('.py') and \
               filename.startswith('cmd_'):
                commands.append(filename[4:-3])
        commands.sort()
        return commands

    def get_command(self, context, name):
        try:
            mod = __import__(name='buildgrid._app.commands.cmd_{}'.format(name),
                             fromlist=['cli'])
        except ImportError:
            return None
        return mod.cli


@click.command(cls=BuildGridCLI, context_settings=CONTEXT_SETTINGS)
@click.option('-v', '--verbose', is_flag=True,
              help='Enables verbose mode.')
@pass_context
def cli(context, verbose):
    """BuildGrid App"""
    logger = _logging.bgd_logger()
    context.verbose = verbose
    if verbose:
        logger.setLevel(logging.DEBUG)