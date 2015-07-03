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
module: linode_nodebalancer
short_description: Add / Delete / Update a linode nodebalancer
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


def handle_api_error(func):
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


@handle_api_error
def linodeNodeBalancers(module, api, state, name, node_balancer_id,
                        datacenter_id, paymentterm, client_conn_throttle):

    changed = False

    nodebalancer = nodebalancer_find(api, node_balancer_id, name)
    if nodebalancer:
        if state == "present":
            if nodebalancer['LABEL'] != name or \
               nodebalancer['CLIENTCONNTHROTTLE'] != client_conn_throttle:

                new = api.nodebalancer_update(
                    NodeBalancerID=nodebalancer['NODEBALANCERID'],
                    Label=name,
                    ClientConnThrottle=client_conn_throttle)
                changed = True
                nodebalancer = nodebalancer_find(api,
                                                 new['NodeBalancerID'],
                                                 name)
        elif state == "absent":
            api.nodebalancer_delete(
                NodeBalancerId=nodebalancer['NODEBALANCERID']
            )
            nodebalancer = None
            changed = True

    else:
        if state == "present":
            api.nodebalancer_create(DatacenterID=datacenter_id,
                                    PaymentTerm=paymentterm,
                                    Label=name)
            changed = True

        elif state == "absent":
            pass

    module.exit_json(changed=changed, instances=nodebalancer)


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
            datacenter_id=dict(required=False,
                               default=7,
                               type='int'),
            paymentterm=dict(required=False,
                             default=1,
                             type='int'),
            client_conn_throttle=dict(required=False,
                                      default=0,
                                      type='int')
        ),
        required_one_of=[
            ['name', 'node_balancer_id']
        ],
        supports_check_mode=False
    )

    if not HAS_LINODE:
        module.fail_json(msg=LINODE_IMPORT_ERROR + " (pip install linode-python)")

    api_key = module.params.get('api_key')
    name = module.params.get('name')
    node_balancer_id = module.params.get('node_balancer_id')
    state = module.params.get('state')
    datacenter_id = module.params.get('datacenter_id')
    paymentterm = module.params.get('paymentterm')
    client_conn_throttle = module.params.get('client_conn_throttle')

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

    linodeNodeBalancers(module, api, state, name, node_balancer_id,
                        datacenter_id, paymentterm, client_conn_throttle)


from ansible.module_utils.basic import *

if __name__ == '__main__':
    main()
