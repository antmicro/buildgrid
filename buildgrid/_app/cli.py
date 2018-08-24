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
import grpc
from xdg import XDG_CACHE_HOME, XDG_CONFIG_HOME, XDG_DATA_HOME

from buildgrid.utils import read_file

from . import _logging

CONTEXT_SETTINGS = dict(auto_envvar_prefix='BUILDGRID')


class Context:

    def __init__(self):
        self.verbose = False

        self.user_home = os.getcwd()

        self.cache_home = os.path.join(XDG_CACHE_HOME, 'buildgrid')
        self.config_home = os.path.join(XDG_CONFIG_HOME, 'buildgrid')
        self.data_home = os.path.join(XDG_DATA_HOME, 'buildgrid')

    def load_server_credentials(self, server_key=None, server_cert=None,
                                client_certs=None, use_default_client_certs=False):
        """Looks-up and loads TLS server gRPC credentials.

        Every private and public keys are expected to be PEM-encoded.

        Args:
            server_key(str): private server key file path.
            server_cert(str): public server certificate file path.
            client_certs(str): public client certificates file path.
            use_default_client_certs(bool, optional): whether or not to try
                loading public client certificates from default location.
                Defaults to False.

        Returns:
            :obj:`ServerCredentials`: The credentials for use for a
            TLS-encrypted gRPC server channel.
        """
        if not server_key or not os.path.exists(server_key):
            server_key = os.path.join(self.config_home, 'server.key')
            if not os.path.exists(server_key):
                return None

        if not server_cert or not os.path.exists(server_cert):
            server_cert = os.path.join(self.config_home, 'server.crt')
            if not os.path.exists(server_cert):
                return None

        if not client_certs or not os.path.exists(client_certs):
            if use_default_client_certs:
                client_certs = os.path.join(self.config_home, 'client.crt')
            else:
                client_certs = None

        server_key_pem = read_file(server_key)
        server_cert_pem = read_file(server_cert)
        if client_certs and os.path.exists(client_certs):
            client_certs_pem = read_file(client_certs)
        else:
            client_certs_pem = None

        return grpc.ssl_server_credentials([(server_key_pem, server_cert_pem)],
                                           root_certificates=client_certs_pem,
                                           require_client_auth=bool(client_certs))


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
