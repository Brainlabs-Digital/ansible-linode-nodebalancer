# ansible-linode-nodebalancer
Ansible module to create / update / delete Linode Nodebalancers

To enable this module to be read by Ansible you must place it in a 'library' folder and let ansible know where this is by editing your ansible.cfg - ([docs](http://docs.ansible.com/intro_configuration.html#library))

## Example Installation

Choose where you will save your custom ansible modules

    mkdir ~/custom-ansible-modules
    cd ~/custom-ansible-modules

Clone this repository

    git clone git@github.com:DistilledLtd/ansible-linode-nodebalancer.git

Symlink the new module into the shared ansible folder

    sudo mkdir -p /usr/share/ansible
    sudo ln -s ~/custom-ansible-modules/ansible-linode-nodebalancer /usr/share/ansible/linode_nodebalancer

Add library to the defaults section of your ansible.cfg

    [defaults]
    library = /usr/share/ansible

# Dependencies

This module makes use of the [linode-python library](https://github.com/tjfontaine/linode-python). Since this is a local task (ie it runs on the machine triggering the playbook, rather than the remote servers) you will need to install this into (virtual) environment that is running the playbook.

    pip install linode-python

# Usage

## Create a NodeBalancer

    - name: Setup Nodebalancer 
      sudo: false
      run_once: true
      local_action:
        module: linode_nodebalancer
        api_key: "{{ linode_api_key }}"
        name: "My Nodebalancer"

## Create a NodeBalancer Configuration

    - name: ensure http:80 config is present
      sudo: false
      run_once: true
      local_action:
        module: linode_nodebalancer_config
        api_key: "{{ linode_api_key }}"
        name: "My Nodebalancer"
        port: 80
        protocol: http
        algorithm: roundrobin

## Add a node to the NodeBalancer Configuration

NB, The node balancer will only work on private ip addresses ([docs](https://www.linode.com/docs/networking/linux-static-ip-configuration/)). On Ubuntu 14, with linode's [network helper](https://www.linode.com/docs/platform/network-helper) the private ip address is exposed as an ansible variable at 'ansible_eth0_1'. You can combine this with the current host name via 'inventory_hostname' to add a node for the current remote server.

    - name: Ensure the current remote is a node on the node balancer
      sudo: false
      local_action:
        module: linode_nodebalancer_node
        api_key: "{{ linode_api_key }}"
        name: "My Nodebalancer"
        port: 80
        protocol: http
        node_name: "{{ inventory_hostname }}"
        address: "{{hostvars[inventory_hostname]['ansible_eth0_1']['ipv4']['address']}}:80"


# Todo:

    - Move repeating functions (e.g. `nodebalancer_find` and `handle_api_error`) into a file that can be imported.
    - Allow https / SSH as a protocol

# License

This code is provided under an MIT-style license. Please refer to the LICENSE file in the root of the project for specifics.
