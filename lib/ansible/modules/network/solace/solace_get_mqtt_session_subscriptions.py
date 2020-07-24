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

ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'community'}

import ansible.module_utils.network.solace.solace_utils as su
from ansible.module_utils.basic import AnsibleModule

DOCUMENTATION = '''
---
module: solace_get_mqtt_session_subscriptions

version_added: '2.9.10'

short_description: Get a list of MQTT Session Subscription Objects

description:
- "Get a list of MQTT Session Subscription Objects. Retrieves all objects that match the criteria defined in the 'where' clause and returns the fields defined in the 'select' parameter."
- "Reference: U(https://docs.solace.com/API-Developer-Online-Ref-Documentation/swagger-ui/config/index.html#/mqttSession/getMsgVpnMqttSessionSubscriptions)."

options:
  mqtt_session_client_id:
    description: The MQTT session client id. Maps to 'mqttSessionClientId' in the API.
    type: str
    required: true
    aliases: [client_id, client]

extends_documentation_fragment:
- solace.broker
- solace.vpn
- solace.virtual_router
- solace.query

seealso:
- module: solace_mqtt_session_subscription

author:
  - Ricardo Gomez-Ulmke (ricardo.gomez-ulmke@solace.com)
'''

EXAMPLES = '''
    - name: Get subscriptions
      solace_get_mqtt_session_subscriptions:
        client_id: "{{ mqttSessionClientId }}"
        query_params:
          where:
            - "subscriptionTopic==ansible-solace/test/*"
          select:
            - "mqttSessionClientId"
            - "mqttSessionVirtualRouter"
            - "subscriptionTopic"
            - "subscriptionQos"
      register: get_subscription_result

    - name: Print existing list
      debug:
        msg: "{{ get_subscription_result.result_list }}"

    - name: Print count of existing queue list
      debug:
        msg: "{{ get_subscription_result.result_list_count }}"

'''

RETURN = '''
result_list:
    description: The list of objects found containing requested fields.
    returned: on success
    type: list
    elements: complex
    sample: [
        {
            "mqttSessionClientId": "ansible-solace_test_mqtt__4__",
            "mqttSessionVirtualRouter": "primary",
            "subscriptionQos": 1,
            "subscriptionTopic": "ansible-solace/test/__4__/topic/subscription/1/>"
        },
        {
            "mqttSessionClientId": "ansible-solace_test_mqtt__4__",
            "mqttSessionVirtualRouter": "primary",
            "subscriptionQos": 1,
            "subscriptionTopic": "ansible-solace/test/__4__/topic/subscription/3/>"
        }
    ]

result_list_count:
    description: Number of items in result_list.
    returned: on success
    type: int

'''


class SolaceGetMqttSessionSubscritionsTask(su.SolaceTask):

    def __init__(self, module):
        su.SolaceTask.__init__(self, module)

    def get_list(self):
        # GET /msgVpns/{msgVpnName}/mqttSessions/{mqttSessionClientId},{mqttSessionVirtualRouter}/subscriptions

        vpn = self.module.params['msg_vpn']
        client_id = self.module.params['mqtt_session_client_id']
        virtual_router = self.module.params['virtual_router']

        uri_ext = ','.join([client_id, virtual_router])

        path_array = [su.SEMP_V2_CONFIG, su.MSG_VPNS, vpn, su.MQTT_SESSIONS, uri_ext, su.MQTT_SESSION_SUBSCRIPTIONS]

        query_params = self.module.params['query_params']
        ok, resp = su.get_list(self.solace_config, path_array, query_params)
        if ok:
            queue_list = resp
        else:
            return False, resp

        return True, queue_list


def run_module():
    """Entrypoint to module"""

    """Compose module arguments"""
    module_args = dict(
        mqtt_session_client_id=dict(type='str', aliases=['client_id', 'client'], required=True),
    )
    arg_spec = su.arg_spec_broker()
    arg_spec.update(su.arg_spec_vpn())
    arg_spec.update(su.arg_spec_virtual_router())
    arg_spec.update(su.arg_spec_query())
    # module_args override standard arg_specs
    arg_spec.update(module_args)

    module = AnsibleModule(
        argument_spec=arg_spec,
        supports_check_mode=True
    )

    result = dict(
        changed=False
    )

    solace_task = SolaceGetMqttSessionSubscritionsTask(module)
    ok, resp_or_list = solace_task.get_list()
    if not ok:
        module.fail_json(msg=resp_or_list, **result)

    result['result_list'] = resp_or_list
    result['result_list_count'] = len(resp_or_list)
    module.exit_json(**result)


def main():
    """Standard boilerplate"""
    run_module()


if __name__ == '__main__':
    main()

###
# The End.