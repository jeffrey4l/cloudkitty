# -*- coding: utf-8 -*-
# Copyright 2014 Objectif Libre
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#
# @author: Stéphane Albert
#
import os
from wsgiref import simple_server

from oslo.config import cfg
from oslo import messaging
from paste import deploy
import pecan

from cloudkitty.api import config as api_config
from cloudkitty.api import hooks
from cloudkitty.common import rpc
from cloudkitty import config  # noqa
from cloudkitty.openstack.common import log as logging


LOG = logging.getLogger(__name__)

auth_opts = [
    cfg.StrOpt('api_paste_config',
               default="api_paste.ini",
               help="Configuration file for WSGI definition of API."
               ),
]

api_opts = [
    cfg.StrOpt('host_ip',
               default="0.0.0.0",
               help="Host serving the API."
               ),
    cfg.IntOpt('port',
               default=8888,
               help="Host port serving the API."
               ),
]

CONF = cfg.CONF
CONF.register_opts(auth_opts)
CONF.register_opts(api_opts, group='api')


def get_pecan_config():
    # Set up the pecan configuration
    filename = api_config.__file__.replace('.pyc', '.py')
    return pecan.configuration.conf_from_file(filename)


def setup_app(pecan_config=None, extra_hooks=None):

    app_conf = get_pecan_config()

    target = messaging.Target(topic='cloudkitty',
                              version='1.0')

    client = rpc.get_client(target)

    app_hooks = [
        hooks.RPCHook(client)
    ]

    return pecan.make_app(
        app_conf.app.root,
        static_root=app_conf.app.static_root,
        template_path=app_conf.app.template_path,
        debug=CONF.debug,
        force_canonical=getattr(app_conf.app, 'force_canonical', True),
        hooks=app_hooks,
        guess_content_type_from_ext=False
    )


def setup_wsgi():
    cfg_file = cfg.CONF.api_paste_config
    if not os.path.exists(cfg_file):
        raise Exception('api_paste_config file not found')
    return deploy.loadapp("config:" + cfg_file)


def build_server():
    # Create the WSGI server and start it
    host = CONF.api.host_ip
    port = CONF.api.port

    server_cls = simple_server.WSGIServer
    handler_cls = simple_server.WSGIRequestHandler

    app = setup_app()

    srv = simple_server.make_server(
        host,
        port,
        app,
        server_cls,
        handler_cls)

    return srv
