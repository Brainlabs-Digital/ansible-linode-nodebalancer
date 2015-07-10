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
module: linode_nodebalancer_config
short_description: Add / Delete / Update a "config" in a linode nodebalancer. Each NodeBalancer config adds another port that the NodeBalancer will listen on. For instance, if you wish to balance both port 80 and 81, you’ll need to add two configuration profiles to your NodeBalancer.
description:
    - Wrapper around the linode nodebalancer api https://www.linode.com/api/nodebalancer - or https://www.linode.com/docs/platform/nodebalancer/nodebalancer-reference-guide
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
            - The desired state of the nodebalancer
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
    algorithm:
        required: false
        type: string
        default: roundrobin
        choices: ['roundrobin', 'leastconn', 'source']
        description:
            - How initial new connections are allocated across the backend Nodes
    stickiness:
        required: false
        type: string
        default: none
        choices: ['none', 'table', 'http_cookie'],
        description:
            - NodeBalancers have the ability for Session Persistence - meaning subsequent requests from the same client will be routed to the same backend Node when possible
    check:
        required: false
        type: string
        default: 'connection'
        choices: ['connection', 'http', 'http_body']
        description:
            - NodeBalancers perform both passive and active health checks against the backend nodes. Nodes that are no longer responding are taken out of rotation. This determines the type of check to perform.
                - 'connection' - TCP Connection - requires a successful TCP handshake with a backend node.
                - 'http' - HTTP Valid Status - performs an HTTP request on the provided path and requires a 2xx or 3xx response from the backend node.
                - 'http_body' - HTTP Body Regex - performs an HTTP request on the provided path and requires the provided PCRE regular expression matches against the request’s result body.
    check_interval:
        required: false
        type: integer
        default: 5
        description:
            - Seconds between active health check probes
    check_timeout:
        required: false
        type: integer
        default: 3
        description:
            - Seconds to wait before considering the probe a failure. 1-30.
    check_attempts:
        required: false
        type: integer
        default: 2
        description:
            - Number of failed probes before taking a node out of rotation. 1-30
    check_path:
        required: false
        type: string
        description:
            - Used if 'check' is set to 'http_body' to determine the path to check
    check_body:
        required: false
        type: string
        description:
            - Used in conjuction with 'check_path'. This is the PCRE regular expression to match against the request's result body.
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
def linodeNodeBalancerConfigs(module, api, state, name, node_balancer_id,
                              config_id, port, protocol, algorithm, stickiness,
                              check, check_interval, check_timeout,
                              check_attempts, check_path, check_body):

    changed = False

    nodebalancer = nodebalancer_find(api, node_balancer_id, name)
    if not nodebalancer:
        msg = "FATAL: {nm}/{id} Nodebalancer not found" .format(
            nm=name, id=node_balancer_id)
        module.fail_json(msg=msg)

    config = nodebalancer_config_find(api, nodebalancer, config_id,
                                      port, protocol)

    if config:
        if state == "present":
            if config['PORT'] != port \
               or config['PROTOCOL'] != protocol \
               or config['ALGORITHM'] != algorithm \
               or config['STICKINESS'] != stickiness \
               or config['CHECK'] != check \
               or config['CHECK_INTERVAL'] != check_interval \
               or config['CHECK_TIMEOUT'] != check_timeout \
               or config['CHECK_ATTEMPTS'] != check_attempts \
               or config['CHECK_PATH'] != str(check_path) \
               or config['CHECK_BODY'] != str(check_body):

                new = api.nodebalancer_config_update(
                    ConfigID=config['CONFIGID'],
                    Port=port,
                    Protocol=protocol,
                    Algorithm=algorithm,
                    Stickiness=stickiness,
                    check=check,
                    check_interval=check_interval,
                    check_timeout=check_timeout,
                    check_attempts=check_attempts,
                    check_path=check_path,
                    check_body=check_body,
                )
                changed = True
                config = nodebalancer_config_find(api, nodebalancer,
                                                  new['ConfigID'],
                                                  port, protocol)
        elif state == "absent":
            api.nodebalancer_config_delete(
                NodeBalancerID=nodebalancer['NODEBALANCERID'],
                ConfigID=config['CONFIGID']
            )
            changed = True
            config = None
    else:
        if state == "present":
            new = api.nodebalancer_config_create(
                NodeBalancerID=nodebalancer['NODEBALANCERID'],
                Port=port,
                Protocol=protocol,
                Algorithm=algorithm,
                Stickiness=stickiness,
                check=check,
                check_interval=check_interval,
                check_timeout=check_timeout,
                check_attempts=check_attempts,
                check_path=check_path,
                check_body=check_body,
            )
            changed = True
            config = nodebalancer_config_find(api, nodebalancer,
                                              new['ConfigID'], port, protocol)
        elif state == "absent":
            pass

    module.exit_json(changed=changed, instances=config)


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
            algorithm=dict(required=False,
                           default='roundrobin',
                           choices=['roundrobin', 'leastconn', 'source'],
                           type='str'),
            stickiness=dict(required=False,
                            default='none',
                            choices=['none', 'table', 'http_cookie'],
                            type='str'),
            check=dict(required=False,
                       default='connection',
                       choices=['connection', 'http', 'http_body'],
                       type='str'),
            check_interval=dict(required=False,
                                default=5,
                                type='int'),
            check_timeout=dict(required=False,
                               default=3,
                               type='int'),
            check_attempts=dict(required=False,
                                default=2,
                                type='int'),
            check_path=dict(required=False,
                            type='str'),
            check_body=dict(required=False,
                            type='str'),
        ),
        required_one_of=[
            ['name', 'node_balancer_id'],
            ['port', 'protocol', 'config_id'],
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
    algorithm = module.params.get('algorithm')
    stickiness = module.params.get('stickiness')
    check = module.params.get('check')
    check_interval = module.params.get('check_interval')
    check_timeout = module.params.get('check_timeout')
    check_attempts = module.params.get('check_attempts')
    check_path = module.params.get('check_path')
    check_body = module.params.get('check_body')

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

    linodeNodeBalancerConfigs(module, api, state, name, node_balancer_id,
                              config_id, port, protocol, algorithm, stickiness,
                              check, check_interval, check_timeout,
                              check_attempts, check_path, check_body)


from ansible.module_utils.basic import *

if __name__ == '__main__':
    main()
