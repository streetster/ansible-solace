from ansible.module_utils.basic import AnsibleModule
import ansible.module_utils.network.solace.solace_utils as su

def run_module():
    """Entrypoint to module"""
    module_args = dict(
        name=dict(type='str', required=True),
        msg_vpn=dict(type='str', required=True),
        host=dict(type='str', default='localhost'),
        port=dict(type='int', default=8080),
        secure_connection=dict(type='bool', default=False),
        username=dict(type='str', default='admin'),
        password=dict(type='str', default='admin', no_log=True),
        settings=dict(type='dict', require=False),
        state=dict(default="present", choices=["absent", "present"]),
        timeout=dict(default=1, require=False)
    )
    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    msg_vpn = module.params["msg_vpn"]
    client_profile = module.params["name"]
    settings = module.params["settings"]

    result = su.perform_module_actions(module,
                                       client_profile,
                                       settings,
                                       su.get_configured_client_profiles_for_vpn,
                                       [msg_vpn],
                                       su.create_client_profile,
                                       su.delete_client_profile,
                                       su.update_client_profile)
                                       #[msg_vpn, client_profile])
    module.exit_json(**result)

def main():
    run_module()

if __name__ == '__main__':
    main()