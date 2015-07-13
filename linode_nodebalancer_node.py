#!/usr/bin/python
# -*- coding: utf-8 -*-

try:
    from linode import api as linode_api
    HAS_LINODE = True
except ImportError as ie:
    HAS_LINODE = False
    LINODE_IMPORT_ERROR = str(ie)


DOCUMENTATION = '''
---
module: linode_nodebalancer_node
short_description: Add / Delete / Update nodes from a linode nodebalancer
description:
    - Wrapper around the linode nodebalancer api https://www.linode.com/api/nodebalancer
version_added: "0.1"
author: Duncan Morris (@duncanmorris)
requirements:
    - This module runs locally, not on the remote server(s)
    - It relies on the linode-python library https://github.com/tjfontaine/linode-python
options:
    api_key:
        required: false
        type: string
        description:
            - Your linode api key, (see https://www.linode.com/docs/platform/api/api-key). You could pass it in directly to the modele, or set it as an environment variable (LINODE_API_KEY).
    name:
        required: false
        type: string
        description:
            - The name of the NodeBalancer being targeted.
    node_balancer_id:
        required: false
        type: integer
        description:
            - The id of the NodeBalancer being targeted. This is not exposed anywhere obvious (other than the api), so typically you would target via name. One of name, or node_balancer_id is required. If present, this takes precedence over the name when looking up the nodebalancer.
    state:
        required: false
        choices: ['present', 'absent']
        default: present
        type: string
        description:
            - The desired state of the node
    config_id:
        required: false
        type: integer
        description:
            - The id of the NodeBalancer Config being targeted. This is not exposed anywhere obvious (other than the api) so typically you would target the config via a port and protocol. If present this takes precedence over the port / protocol when looking up the config.
    port:
        required: false
        type: integer
        default: 80
        description:
            - The port of the config we are targeting.
    protocol:
        required: false
        type: string
        default: http
        choices: ['http', 'tcp']
        description:
            - The protocol of the config we are targeting. NB, https is not currently supported (pull requests welcomed).
    node_id:
        required: false
        type: integer
        description:
            - The id of the Node being targeted. This is not exposed anywhere obvious (other than the api) so typically you would target the node via it's name (node_name). If present this takes precedence over the name when looking up the node.
    name:
        required: false
        type: string
        description:
            - The name of the Node being targeted. Typically this would be the hostname of the target server
    address:
        required: false
        type: string
        description:
            - The address:port combination used to communicate with this Node. Linode requires that this is a private IP address. This is typically exposed in the following way "{{hostvars[inventory_hostname]['ansible_eth0_1']['ipv4']['address']}}:80"
    weight:
        required: false
        type: integer
        default: 100
        description:
            - Load balancing weight, 1-255. Higher means more connections
    mode:
        required: false
        type: string
        default: 'accept'
        choices: ['accept', 'reject', 'drain']
        description:
            - The connections mode for this node. One of 'accept', 'reject', or 'drain'
'''

EXAMPLES = '''

NB: This module could be used as a pre / post task as part of a rolling upgrade (e.g. using serial to take 1 server out of the node balancer, upgrading it, before putting it back in play). See http://docs.ansible.com/guide_rolling_upgrade.html for further details.

- name: Ensure the current node is set to accept connections
  local_action:
    module: linode_nodebalancer_node
    api_key: "{{ linode_api_key }}"
    name: "NodeBalancer Name"
    port: 80
    protocol: http
    node_name: "{{ inventory_hostname }}"
    address: "{{hostvars[inventory_hostname]['ansible_eth0_1']['ipv4']['address']}}:80"
    mode: accept
    weight: 100
'''


def handle_api_error(func):
    """A decorator that catches and api errors from the linode api and
    returns ansible module fail_json.

    An ansible module instance must be the first argument to the func
    """
    def handle(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except linode_api.ApiError as e:
            code = e.value[0]['ERRORCODE']
            err = e.value[0]['ERRORMESSAGE']
            msg = "FATAL: Code [{code}] - {err}".format(code=code,
                                                        err=err)
            return args[0].fail_json(msg=msg)
    return handle


def nodebalancer_find(api, node_balancer_id, name):
    """Lookup and return a nodebalancer from the api.
    If node_balancer_id is present, lookup based on that.
    If not, lookup based on the name
    """

    if node_balancer_id:
        return api.nodebalancer_list(NodeBalancerID=node_balancer_id)

    if name:
        nodebalancers = api.nodebalancer_list()
        for nb in nodebalancers:
            if nb['LABEL'] == name:
                return nb

    return None


def nodebalancer_config_find(api, nodebalancer, config_id, port, protocol):
    """Lookup and return a nodebalancer config from the api.
    If config_id is present, lookup based on that.
    If not, lookup based on the port and protocol
    """

    if config_id:
        return api.nodebalancer_config_list(
            NodeBalancerID=nodebalancer['NODEBALANCERID'],
            ConfigID=config_id
        )

    all_configs = api.nodebalancer_config_list(
        NodeBalancerID=nodebalancer['NODEBALANCERID'],
    )

    for config in all_configs:
        if config['PORT'] == port and config['PROTOCOL'] == protocol:
            return config

    return None


def nodebalancer_node_find(api, nodebalancer, config, node_id, node_name):
    """Lookup and return a node from the given nodebalancer / config
    If node_id is present lookup based on that.
    If not, lookup based on the node_name
    """

    if node_id:
        return api.nodebalancer_node_list(ConfigID=config['CONFIGID'],
                                          NodeID=node_id)

    all_nodes = api.nodebalancer_node_list(ConfigID=config['CONFIGID'])

    for node in all_nodes:
        if node['LABEL'] == node_name:
            return node

    return None


@handle_api_error
def linodeNodeBalancerNodes(module, api, state, name, node_balancer_id,
                            config_id, port, protocol, node_id, node_name,
                            address, weight, mode):

    debug = {}
    changed = False

    nodebalancer = nodebalancer_find(api, node_balancer_id, name)
    if not nodebalancer:
        msg = "FATAL: {nm}/{id} Nodebalancer not found" .format(
            nm=name, id=node_balancer_id)
        module.fail_json(msg=msg)

    config = nodebalancer_config_find(api, nodebalancer, config_id,
                                      port, protocol)
    if not config:
        msg = "FATAL: {prot}:{port}/{id} Config not found" .format(
            prot=protocol, port=port, id=config_id)
        module.fail_json(msg=msg)

    debug['nodebalancer'] = nodebalancer
    debug['config'] = config

    node = nodebalancer_node_find(api, nodebalancer, config, node_id,
                                  node_name)

    debug['node'] = node

    if node:
        if state == "present":
            if node['LABEL'] != node_name or node['ADDRESS'] != address or \
               node['WEIGHT'] != weight or node['MODE'] != mode:

                new = api.nodebalancer_node_update(NodeID=node['NODEID'],
                                                   Label=node_name,
                                                   Address=address,
                                                   Weight=weight,
                                                   Mode=mode)
                changed = True
                node = nodebalancer_node_find(api, nodebalancer, config,
                                              new['NodeID'], node_name)
        elif state == "absent":
            api.nodebalancer_node_delete(
                ConfigID=config['CONFIGID'],
                NodeID=node['NODEID']
            )
            changed = True
            config = None
    else:
        if state == "present":
            new = api.nodebalancer_node_create(
                ConfigID=config['CONFIGID'],
                Label=node_name,
                Address=address,
                Weight=weight,
                Mode=mode
            )
            changed = True
            node = nodebalancer_node_find(api, nodebalancer, config,
                                          new['NodeID'], node_name)

        elif state == "absent":
            pass

    module.exit_json(changed=changed, instances=config, debug=debug)


# ===========================================
def main():
    module = AnsibleModule(
        argument_spec=dict(
            api_key=dict(required=False,
                         aliases=['linode_api_id'],
                         type='str'),
            name=dict(required=False,
                      type='str'),
            node_balancer_id=dict(required=False,
                                  type='int'),
            state=dict(required=False,
                       default='present',
                       choices=['present', 'absent'],
                       type='str'),
            config_id=dict(required=False,
                           type='int'),
            port=dict(required=False,
                      default=80,
                      type='int'),
            protocol=dict(required=False,
                          default='http',
                          choices=['http', 'tcp'],
                          type='str'),
            node_id=dict(required=False,
                         type='int'),
            node_name=dict(required=False,
                           type='str'),
            address=dict(required=False,
                         type='str'),
            weight=dict(required=False,
                        default=100,
                        type='int'),
            mode=dict(required=False,
                      default='accept',
                      choices=['accept', 'reject', 'drain'],
                      type='str'),
        ),
        required_one_of=[
            ['name', 'node_balancer_id'],
            ['port', 'protocol', 'config_id'],
            ['node_name', 'node_id']
        ],
        supports_check_mode=False
    )

    if not HAS_LINODE:
        module.fail_json(msg=LINODE_IMPORT_ERROR + " (pip install linode-python)")

    api_key = module.params.get('api_key')
    name = module.params.get('name')
    node_balancer_id = module.params.get('node_balancer_id')
    state = module.params.get('state')
    config_id = module.params.get('config_id')
    port = module.params.get('port')
    protocol = module.params.get('protocol')
    node_id = module.params.get('node_id')
    node_name = module.params.get('node_name')
    address = module.params.get('address')
    weight = module.params.get('weight')
    mode = module.params.get('mode')

    # Setup the api_key
    if not api_key:
        try:
            api_key = os.environ['LINODE_API_KEY']
        except KeyError, e:
            module.fail_json(msg='Unable to load %s' % e.message)

    # setup the auth
    try:
        api = linode_api.Api(api_key)
        api.test_echo()
    except Exception, e:
        module.fail_json(msg='%s' % e.value[0]['ERRORMESSAGE'])

    linodeNodeBalancerNodes(module, api, state, name, node_balancer_id,
                            config_id, port, protocol, node_id, node_name,
                            address, weight, mode)

from ansible.module_utils.basic import *

if __name__ == '__main__':
    main()
