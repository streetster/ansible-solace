#!/usr/bin/python
# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------------------------------
# MIT License
#
# Copyright (c) 2020, Solace Corporation, Ricardo Gomez-Ulmke (ricardo.gomez-ulmke@solace.com)
# Copyright (c) 2020, Solace Corporation, Swen-Helge Huber <swen-helge.huber@solace.com
# Copyright (c) 2019, Mark Street <mkst@protonmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
# ---------------------------------------------------------------------------------------------

"""Collection of utility classes and functions to aid the solace_* modules."""

import re
import traceback
import logging
import json
import os
from distutils.util import strtobool
from ansible.errors import AnsibleError

try:
    import requests

    HAS_REQUESTS = True
except ImportError:
    REQUESTS_IMP_ERR = traceback.format_exc()
    HAS_REQUESTS = False

SEMP_V2_CONFIG = '/SEMP/v2/config'

""" VPN level reources """

MSG_VPNS = 'msgVpns'
TOPIC_ENDPOINTS = 'topicEndpoints'
ACL_PROFILES = 'aclProfiles'
ACL_PROFILES_CLIENT_CONNECT_EXCEPTIONS = 'clientConnectExceptions'
# ACL_PROFILES_PUBLISH_TOPIC_EXCEPTIONS = 'publishTopicExceptions'
# ACL_PROFILES_SUBSCRIBE_TOPIC_EXCEPTIONS = 'subscribeTopicExceptions'
# ACL_PROFILES_PUBLISH_EXCEPTIONS = 'publishExceptions'
# ACL_PROFILES_SUBSCRIBE_EXCEPTIONS = 'subscribeExceptions'
CLIENT_PROFILES = 'clientProfiles'
CLIENT_USERNAMES = 'clientUsernames'
DMR_BRIDGES = 'dmrBridges'
BRIDGES = 'bridges'
BRIDGES_REMOTE_MSG_VPNS = 'remoteMsgVpns'
BRIDGES_REMOTE_SUBSCRIPTIONS = 'remoteSubscriptions'
BRIDGES_TRUSTED_COMMON_NAMES = 'tlsTrustedCommonNames'

QUEUES = 'queues'
SUBSCRIPTIONS = 'subscriptions'

""" RDP Resources """
RDP_REST_DELIVERY_POINTS = 'restDeliveryPoints'
RDP_REST_CONSUMERS = 'restConsumers'
RDP_TLS_TRUSTED_COMMON_NAMES = 'tlsTrustedCommonNames'
RDP_QUEUE_BINDINGS = 'queueBindings'

""" DMR Resources """
DMR_CLUSTERS = 'dmrClusters'
LINKS = 'links'
REMOTE_ADDRESSES = 'remoteAddresses'
TLS_TRUSTED_COMMON_NAMES = 'tlsTrustedCommonNames'
""" cert authority resources """
CERT_AUTHORITIES = 'certAuthorities'

################################################################################################
# initialize logging
ENABLE_LOGGING = False  # False to disable
enableLoggingEnvVal = os.getenv('ANSIBLE_SOLACE_ENABLE_LOGGING')
if enableLoggingEnvVal is not None and enableLoggingEnvVal != '':
    try:
        ENABLE_LOGGING = bool(strtobool(enableLoggingEnvVal))
    except ValueError:
        raise ValueError("invalid value for env var: 'ANSIBLE_SOLACE_ENABLE_LOGGING={}'. use 'true' or 'false' instead.".format(enableLoggingEnvVal))

if ENABLE_LOGGING:
    logging.basicConfig(filename='ansible-solace.log',
                        level=logging.DEBUG,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(funcName)s(): %(message)s')
    logging.info('Module start #############################################################################################')

################################################################################################


class SolaceConfig(object):
    """Solace Configuration object"""

    def __init__(self,
                 vmr_host,
                 vmr_port,
                 vmr_auth,
                 vmr_secure=False,
                 vmr_timeout=1,
                 x_broker='',
                 vmr_sempVersion=''):
        self.vmr_auth = vmr_auth
        self.vmr_timeout = float(vmr_timeout)
        self.vmr_url = ('https' if vmr_secure else 'http') + '://' + vmr_host + ':' + str(vmr_port)
        self.x_broker = x_broker
        self.vmr_sempVersion = vmr_sempVersion
        return


class SolaceTask:

    def __init__(self, module):
        self.module = module
        self.solace_config = SolaceConfig(
            vmr_host=self.module.params['host'],
            vmr_port=self.module.params['port'],
            vmr_auth=(self.module.params['username'], self.module.params['password']),
            vmr_secure=self.module.params['secure_connection'],
            vmr_timeout=self.module.params['timeout'],
            x_broker=self.module.params.get('x_broker', ''),
            vmr_sempVersion=self.module.params.get('semp_version', '')
        )
        return

    def do_task(self):

        if not HAS_REQUESTS:
            self.module.fail_json(msg='Missing requests module', exception=REQUESTS_IMP_ERR)

        result = dict(
            changed=False,
            response=dict()
        )

        crud_args = self.crud_args()

        settings = self.module.params['settings']

        if settings:
            # jinja treats everything as a string, so cast ints and floats
            settings = _type_conversion(settings)

        ok, resp = self.get_func(self.solace_config, *(self.get_args() + [self.lookup_item()]))

        if not ok:
            self.module.fail_json(msg=resp, **result)
        # else response was good
        current_configuration = resp
        # whitelist of configuration items that are not returned by GET
        whitelist = ['password']

        if self.lookup_item() in current_configuration:
            if self.module.params['state'] == 'absent':
                if not self.module.check_mode:
                    ok, resp = self.delete_func(self.solace_config, *(self.get_args() + [self.lookup_item()]))
                    if not ok:
                        self.module.fail_json(msg=resp, **result)
                result['changed'] = True
            else:
                if settings and len(settings.keys()):
                    # compare new settings against configuration
                    current_settings = current_configuration[self.lookup_item()]
                    bad_keys = [key for key in settings if key not in current_settings.keys()]
                    # remove whitelist items from bad_keys
                    bad_keys = [item for item in bad_keys if item not in whitelist]
                    # removed keys
                    removed_keys = [item for item in settings if item in whitelist]
                    # fail if any unexpected settings found
                    if len(bad_keys):
                        self.module.fail_json(msg='Invalid key(s): ' + ', '.join(bad_keys), **result)
                    # changed keys are those that exist in settings and don't match current settings
                    changed_keys = [x for x in settings if x in current_settings.keys()
                                    and settings[x] != current_settings[x]]
                    # add back in anything from the whitelist
                    changed_keys = changed_keys + removed_keys
                    # add any whitelisted items
                    if len(changed_keys):
                        delta_settings = {key: settings[key] for key in changed_keys}
                        crud_args.append(delta_settings)
                        if not self.module.check_mode:
                            ok, resp = self.update_func(self.solace_config, *crud_args)
                            result['response'] = resp
                            if not ok:
                                self.module.fail_json(msg=resp, **result)
                        result['delta'] = delta_settings
                        result['changed'] = True
                else:
                    result['response'] = current_configuration[self.lookup_item()]
        else:
            if self.module.params['state'] == 'present':
                if not self.module.check_mode:
                    if settings:
                        crud_args.append(settings)
                    ok, resp = self.create_func(self.solace_config, *crud_args)
                    if ok:
                        result['response'] = resp
                    else:
                        self.module.fail_json(msg=resp, **result)
                result['changed'] = True

        return result

    def get_func(self, solace_config, *args):
        return

    def create_func(self, solace_config, *args):
        return

    def update_func(self, solace_config, *args):
        return

    def delete_func(self, solace_config, *args):
        return

    def lookup_item(self):
        return

    def get_args(self):
        return []

    def crud_args(self):
        return self.get_args() + [self.lookup_item()]

    def lookup_semp_version(self, semp_version):
        raise AnsibleError("argument 'semp_version' not supported by module: {}. implement 'lookup_semp_version()' in module.".format(self.module._name))

    def get_semp_version_key(self, lookup_dict, lookup_vmr_semp_version, lookup_key):
        try:
            v = float(lookup_vmr_semp_version)
        except ValueError:
            raise ValueError("semp_version: '{}' cannot be converted to a float. see 'solace_get_facts' for examples of how to pass in the 'semp_version' argument.".format(lookup_vmr_semp_version))
        ok, version_key = self.lookup_semp_version(v)
        if not ok:
            raise ValueError("unsupported semp_version: '{}'".format(lookup_vmr_semp_version))

        if version_key not in lookup_dict:
            raise ValueError("version_key: '{}' not found in lookup_dict: {}".format(version_key, json.dumps(lookup_dict)))
        version_lookup_dict = lookup_dict[version_key]
        if lookup_key not in version_lookup_dict:
            raise ValueError("lookup_key: '{}' not found in lookup_dict['{}']: '{}'".format(lookup_key, version_key, json.dumps(version_lookup_dict)))
        return version_lookup_dict[lookup_key]


def compose_module_args(module_args):
    _module_args = dict(
        host=dict(type='str', default='localhost'),
        port=dict(type='int', default=8080),
        secure_connection=dict(type='bool', default=False),
        username=dict(type='str', default='admin'),
        password=dict(type='str', default='admin', no_log=True),
        settings=dict(type='dict', require=False),
        state=dict(default='present', choices=['absent', 'present']),
        timeout=dict(default='1', require=False),
        x_broker=dict(type='str', default=''),
        semp_version=dict(type='str', require=False)
    )
    _module_args.update(module_args)
    return _module_args


def merge_dicts(*argv):
    data = dict()
    for arg in argv:
        if arg:
            data.update(arg)
    return data


def _build_config_dict(resp, key):
    if not type(resp) is dict:
        raise TypeError("argument 'resp' is not a 'dict' but {}. Hint: check you are using Sempv2 GET single item call and not a list of items.".format(type(resp)))
    # wrong LOOKUP_ITEM_KEY in module
    if key not in resp:
        raise ValueError("wrong 'LOOKUP_ITEM_KEY' in module. semp GET response does not contain key='{}'".format(key))
    # resp is a single dict, not an array
    # return an array with 1 element
    d = dict()
    d[resp[key]] = resp
    return d


def _type_conversion(d):
    for k, i in d.items():
        t = type(i)
        if (t == str) and re.search(r'^[0-9]+$', i):
            d[k] = int(i)
        elif (t == str) and re.search(r'^[0-9]+\.[0-9]$', i):
            d[k] = float(i)
        elif t == dict:
            d[k] = _type_conversion(i)
    return d


# response contains 1 dict if lookup_item/key is found
# if lookup_item is not found, response http-code: 400 with extra info in meta.error
def get_configuration(solace_config, path_array, key):
    ok, resp = make_get_request(solace_config, path_array)
    if ok:
        return True, _build_config_dict(resp, key)
    else:
        # check if responseCode=400 and error.code=6 ==> not found
        if (type(resp) is dict
                and resp['responseCode'] == 400
                and 'error' in resp.keys()
                and 'code' in resp['error'].keys()
                and resp['error']['code'] == 6):
            return True, dict()
    return False, resp


# request/response handling

def log_http_roundtrip(resp):
    # body is either empty or of type 'bytes'
    if hasattr(resp.request, 'body') and resp.request.body is not None:
        body = json.loads(resp.request.body.decode())
    else:
        body = "{}"

    log = {
        'request': {
            'method': resp.request.method,
            'url': resp.request.url,
            'headers': dict(resp.request.headers),
            'body': body
        },
        'response': {
            'code': resp.status_code,
            'reason': resp.reason,
            'url': resp.url,
            'headers': dict(resp.headers),
            'body': json.loads(resp.text)
        }
    }
    logging.debug("http-roundtrip-log=\n%s", json.dumps(log, indent=2))
    return


def _parse_response(resp):
    if ENABLE_LOGGING:
        log_http_roundtrip(resp)
    if resp.status_code != 200:
        return False, parse_bad_response(resp)
    return True, parse_good_response(resp)


def parse_good_response(resp):
    j = resp.json()
    if 'data' in j.keys():
        return j['data']
    return dict()


def parse_bad_response(resp):
    j = resp.json()
    if 'meta' in j.keys() and \
            'error' in j['meta'].keys() and \
            'description' in j['meta']['error'].keys():
        # return j['meta']['error']['description']
        # we want to see the full message, including the code & request
        return j['meta']
    return 'Unknown error'


def compose_path(path_array):
    if not type(path_array) is list:
        raise TypeError("argument 'path_array' is not an array but {}".format(type(path_array)))
    # ensure elements are 'url encoded'
    # except first one: /SEMP/v2/config
    paths = []
    for i, path_elem in enumerate(path_array):
        if i > 0:
            paths.append(path_elem.replace('/', '%2F'))
        else:
            paths.append(path_elem)
    return '/'.join(paths)


def _make_request(func, solace_config, path_array, json=None):

    path = compose_path(path_array)

    try:
        return _parse_response(
            func(
                solace_config.vmr_url + path,
                json=json,
                auth=solace_config.vmr_auth,
                timeout=solace_config.vmr_timeout,
                headers={'x-broker-name': solace_config.x_broker},
                params=None
            )
        )
    except requests.exceptions.ConnectionError as e:
        return False, str(e)


def make_get_request(solace_config, path_array):
    return _make_request(requests.get, solace_config, path_array)


def make_post_request(solace_config, path_array, json=None):
    return _make_request(requests.post, solace_config, path_array, json)


def make_delete_request(solace_config, path_array, json=None):
    return _make_request(requests.delete, solace_config, path_array, json)


def make_patch_request(solace_config, path_array, json=None):
    return _make_request(requests.patch, solace_config, path_array, json)

###
# The End.
