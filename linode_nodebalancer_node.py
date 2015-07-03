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
notes:
    - Other things consumers of your module should know
requirements:
    - list of required things
    - like the factor package
    - or a specic platform
options:
    name:
        required: true
        aliases: [ "node_id" ]
        description:
            - Name / NodeID of the nodebalancer to create, delete or update.
'''

EXAMPLES = '''

# Set the weight of node 'web01' to 0 on nodebalancer 'ambassador'
 - linode_nodebalancer: name=web01 weight=0 node=ambassador

'''


def nodebalancer_find(api, node_balancer_id, name):

    if node_balancer_id:
        return api.nodebalancer_list(NodeBalancerID=node_balancer_id)

    if name:
        nodebalancers = api.nodebalancer_list()
        for nb in nodebalancers:
            if nb['LABEL'] == name:
                return nb

    return None


def nodebalancer_config_find(api, nodebalancer, config_id, port, protocol):

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

    if node_id:
        return api.nodebalancer_node_list(ConfigID=config['CONFIGID'],
                                          NodeID=node_id)

    all_nodes = api.nodebalancer_node_list(ConfigID=config['CONFIGID'])

    for node in all_nodes:
        if node['LABEL'] == node_name:
            return node

    return None


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
