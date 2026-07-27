# Acceptance Criteria

## Functional Requirements

### Instance Management
- [ ] ListNotebooks returns notebook instances with correct pagination
- [ ] ListAllNotebooks returns all notebooks across all statuses
- [ ] ShowNotebook returns detailed information for a specific instance
- [ ] CreateNotebook creates a new instance with specified parameters
- [ ] UpdateNotebook modifies instance properties successfully
- [ ] DeleteNotebook removes the instance and confirms deletion
- [ ] StartNotebook transitions instance to running state
- [ ] StopNotebook transitions instance to stopped state

### Lease Management
- [ ] ShowLease returns current lease information
- [ ] RenewLease extends the lease duration

### Tag Management
- [ ] ShowNotebookTags returns all tags
- [ ] CreateNotebookTags adds specified tags to a resource
- [ ] DeleteNotebookTags removes specified tags from a resource

### Image Management
- [ ] CreateImage saves a running instance as a container image
- [ ] ListImage returns supported images with pagination
- [ ] RegisterImage registers a custom image from SWR
- [ ] ShowImage returns image details
- [ ] DeleteImage removes an image
- [ ] SyncImage synchronizes image status
- [ ] ListImageGroup returns image groups
- [ ] DeleteImageGroup removes an image group
- [ ] UpdateImageGroup updates image group properties

### Flavor and Cluster
- [ ] ListFlavors returns available notebook flavors
- [ ] ShowSwitchableFlavors returns flavors available for switching
- [ ] ListAuthoringClusters returns resource pools
- [ ] ShowCluster returns cluster details

### Feature Query
- [ ] ListFeatures returns feature toggles and quotas

### Dynamic Storage
- [ ] ListDynamicStorages returns attached storage list
- [ ] AttachDynamicStorage attaches storage to an instance
- [ ] ShowDynamicStorage returns storage details
- [ ] DetachDynamicStorage detaches storage from an instance

## Non-Functional Requirements

- [ ] All write operations prompt for user confirmation before execution
- [ ] Region is not hardcoded — uses `{region}` placeholder
- [ ] project_id is auto-resolved when omitted
- [ ] CLI errors are handled gracefully with meaningful error messages
- [ ] SDK fallback is available when CLI encounters bugs

## Security Requirements

- [ ] No hardcoded AK/SK in any file
- [ ] No credentials in command examples
- [ ] IAM policies follow least-privilege principle
- [ ] Delete operations clearly marked as irreversible
