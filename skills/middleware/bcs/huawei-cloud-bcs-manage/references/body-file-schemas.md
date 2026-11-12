# Body File Schemas

`--body-file` accepts the JSON shape expected by the BCS SDK request body.

```jsonc
// channels.json — create-channels
{"channels": [{"channel_name": "channel-1", "channel_description": "demo channel"}]}

// peers.json — add-peers (peers maps organization -> peer count)
{"channel_peers": [{"channel_name": "channel-1", "peers": {"org-1": 1}}]}

// update.json — update-instance (node_orgs is an OBJECT array)
{"node_orgs": [{"name": "org-2", "node_count": 1}], "is_delete_org": false}

// sdk_config.json — download-sdk-config
{"channel_name": "channel-1", "chaincode_name": "mycc", "cert_path": "./sdk",
 "peer_orgs": {"org-1": ["peer-0"]}}

// invite.json — invite-members
{"bcs_id": "<bcs-id>", "channel_name": "channel-1", "invitor_username": "<tenant>",
 "invited_userinfo": [{"invited_user": "<tenant-name>"}]}

// cancel_invite.json — delete-invite
{"bcs_id": "<bcs-id>", "channel_name": "channel-1",
 "invited_userinfo": [{"invited_user": "<tenant-name>", "status": "pending",
                       "invited_bcs_id": "<invitee-bcs-id>"}]}

// notification.json — handle-notification
{"channel_name": "channel-1", "status": "agree",
 "invitor_info": {"invitor_bcs_id": "<id>", "invitor_bcs_name": "<name>"},
 "invitee_info": {"invitee_bcs_id": "<id>", "invitee_bcs_name": "<name>"},
 "invited_orgs": [{"name": "org-1"}]}

// quit.json — quit-union
{"inviter_bcsid": "<id>", "inviter_projectid": "<project>", "inviter_domainid": "<domain>",
 "inviter_username": "<tenant>", "channel_name": "channel-1",
 "invitee_bcsid": "<id>", "invitee_projectid": "<project>", "invitee_domainid": "<domain>"}
```

`instance.json` for `create-instance` uses the BCS `CreateRequestBody` shape,
for example:
`{"name":"my-chain","version_type":4,"fabric_version":"2.2","blockchain_type":"private","consensus":"etcdraft","sign_algorithm":"ECDSA","volume_type":"nfs","org_disk_size":100,"database_type":"goleveldb","resource_password":"<password>","orderer_node_number":3,"use_eip":false,"cluster_type":"cce","create_new_cluster":true,"peer_orgs":[{"name":"org-1","node_count":1}],"channels":[{"channel_name":"channel-1","channel_description":"demo"}]}`.
Never write the password into the skill directory or a repository; pass it via
the body file on the local machine only.