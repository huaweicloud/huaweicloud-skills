# Deploy CTS Trigger

## Application Scenario

FunctionGraph's CTS trigger (Cloud Trace Service Trigger) is a trigger type based on the Cloud Trace Service (CTS) that can monitor and respond to Huawei Cloud resource operation events. Through CTS triggers, you can implement security auditing, compliance monitoring, automated response, event notification, and other functions.

CTS triggers are particularly suitable for scenarios that require real-time monitoring of cloud resource operations, security auditing, and automated operations, such as resource change monitoring, security event response, compliance checks, operation log analysis, etc. This best practice will introduce how to use Terraform to automatically deploy a FunctionGraph function with a CTS trigger.

## Related Resources/Data Sources

This best practice involves the following main resources and data sources:

### Data Sources

This best practice does not use data sources.

### Resources

- [FunctionGraph Function Resource (huaweicloud\_fgs\_function)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/fgs_function)
- [FunctionGraph Function Trigger Resource (huaweicloud\_fgs\_function\_trigger)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/fgs_function_trigger)

### Resource/Data Source Dependencies

```
huaweicloud_fgs_function
    └── huaweicloud_fgs_function_trigger
```

## Operation Steps

### 1. Script Preparation

Prepare the TF file (e.g., main.tf) in the specified workspace for writing the current best practice script, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. Refer to the "Preparation Before Deploying Huawei Cloud Resources" document for configuration introduction.

### 2. Create FunctionGraph Function

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a FunctionGraph function resource:

```hcl
# Variable definitions for FunctionGraph resources
variable "function_name" {
  description = "The name of the FunctionGraph function"
  type        = string
}

variable "function_agency_name" {
  description = "The agency name of the FunctionGraph function"
  type        = string
}

variable "function_memory_size" {
  description = "The memory size of the function in MB"
  type        = number
  default     = 128
}

variable "function_timeout" {
  description = "The timeout of the function in seconds"
  type        = number
  default     = 10
}

variable "function_runtime" {
  description = "The runtime of the function"
  type        = string
  default     = "Python2.7"
}

variable "function_code" {
  description = "The source code of the function"
  type        = string
  default     = <<EOT
# -*- coding:utf-8 -*-
'''
CTS trigger event:
{
  "cts":  {
        "time": "",
        "user": {
            "name": "userName",
            "id": "",
            "domain": {
                "name": "domainName",
                "id": ""
            }
        },
        "request": {},
        "response": {},
        "code": 204,
        "service_type": "FunctionGraph",
        "resource_type": "",
        "resource_name": "",
        "resource_id": {},
        "trace_name": "",
        "trace_type": "ConsoleAction",
        "record_time": "",
        "trace_id": "",
        "trace_status": "normal"
    }
}
'''
def handler (event, context):
    trace_name = event["cts"]["resource_name"]
    timeinfo = event["cts"]["time"]
    print(timeinfo+' '+trace_name)
EOT
}

variable "function_description" {
  description = "The description of the function"
  type        = string
  default     = ""
}

# Create a FunctionGraph function resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_fgs_function" "test" {
  name        = var.function_name
  app         = "default"
  handler     = "index.handler"
  agency      = var.function_agency_name
  memory_size = var.function_memory_size
  timeout     = var.function_timeout
  runtime     = var.function_runtime
  code_type   = "inline"
  func_code   = base64encode(var.function_code)
  description = var.function_description
}
```

**Parameter Description**:

- **name**: FunctionGraph function name, assigned by referencing the input variable function\_name
- **app**: Application name the function belongs to, set to "default" to use the default application
- **handler**: Function entry point, set to "index.handler" indicating the handler method is in the index.py file
- **agency**: Function agency name, assigned by referencing the input variable function\_agency\_name, used for function permissions to access other Huawei Cloud services
- **memory\_size**: Function memory size (MB), assigned by referencing the input variable function\_memory\_size, default value is 128MB
- **timeout**: Function timeout (seconds), assigned by referencing the input variable function\_timeout, default value is 10 seconds
- **runtime**: Function runtime environment, assigned by referencing the input variable function\_runtime, default value is Python2.7
- **code\_type**: Code type, set to "inline" for inline code
- **func\_code**: Function source code, assigned by base64 encoding the input variable function\_code
- **description**: Function description information, assigned by referencing the input variable function\_description

### 3. Create FunctionGraph CTS Trigger

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a FunctionGraph CTS trigger resource:

```hcl
# Variable definitions for CTS trigger
variable "trigger_status" {
  description = "The status of the FunctionGraph CTS trigger"
  type        = string
  default     = "ACTIVE"
}

variable "trigger_name" {
  description = "The name of the FunctionGraph CTS trigger"
  type        = string
}

variable "trigger_operations" {
  description = "The operations to monitor for the FunctionGraph CTS trigger"
  type        = list(string)
  nullable    = false
}

# Create a FunctionGraph CTS trigger resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_fgs_function_trigger" "test" {
  function_urn = huaweicloud_fgs_function.test.urn
  type         = "CTS"
  status       = var.trigger_status
  event_data   = jsonencode({
    "name"       = var.trigger_name
    "operations" = var.trigger_operations
  })
}
```

**Parameter Description**:

- **function\_urn**: URN of the FunctionGraph function associated with the trigger, assigned by referencing huaweicloud\_fgs\_function.test.urn
- **type**: Trigger type, set to "CTS" for CTS trigger
- **status**: Trigger status, assigned by referencing the input variable trigger\_status, default value is "ACTIVE" for active status
- **event\_data**: Trigger event data, in JSON format containing the following parameters:
  - **name**: Trigger name, assigned by referencing the input variable trigger\_name
  - **operations**: List of operations to monitor, assigned by referencing the input variable trigger\_operations, supports monitoring specific cloud service operations

### 4. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources and data sources use input variables to assign values to configuration content. These input parameters need to be manually entered during subsequent deployments. At the same time, Terraform provides a method to preset these configurations through `tfvars` files, which can avoid repeated input during each execution.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# Function basic information
function_name        = "tf_test_cts_function"
function_agency_name = "function_all_trust"

# Trigger configuration
trigger_name         = "tf_test_cts_trigger"
trigger_operations   = [
  "FunctionGraph:Functions:createFunction"
]
```

**Usage**:

1. Save the above content as `terraform.tfvars` file in the working directory (this file name allows users to automatically import the content of this `tfvars` file when executing terraform commands; for other names, `.auto` needs to be added before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values as needed
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values from this file

In addition to using `terraform.tfvars` file, variable values can also be set in the following ways:

1. Command line parameters: `terraform apply -var="function_name=my-function" -var="trigger_name=my-trigger"`
2. Environment variables: `export TF_VAR_function_name=my-function`
3. Custom named variable files: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set in multiple ways, Terraform will use the variable value according to the following priority: command line parameters > variable files > environment variables > default values.

### 5. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create resources:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming the resource plan is correct, run `terraform apply` to start creating FunctionGraph function and CTS trigger
4. Run `terraform show` to view the created FunctionGraph function and CTS trigger

## Reference Information

- [Huawei Cloud FunctionGraph Product Documentation](https://support.huaweicloud.com/functiongraph/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For FunctionGraph CTS Trigger](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/fgs/triggers/cts)

# Deploy EG Trigger

## Application Scenario

FunctionGraph's EG trigger (EventGrid Trigger) is a trigger type based on the EventGrid service that can monitor and respond to Huawei Cloud resource operation events. Through EG triggers, you can implement event-driven image processing, file conversion, data synchronization, real-time response, and other functions.

EG triggers are particularly suitable for scenarios that require real-time monitoring of OBS object storage events, image processing, and automated workflows, such as image thumbnail generation, file format conversion, data backup, event notification, etc. This best practice will introduce how to use Terraform to automatically deploy a FunctionGraph function with an EG trigger, implementing automatic thumbnail generation when OBS files are uploaded.

## Related Resources/Data Sources

This best practice involves the following main resources and data sources:

### Data Sources

- [FunctionGraph Dependencies Query Data Source (data.huaweicloud\_fgs\_dependencies)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/fgs_dependencies)
- [FunctionGraph Dependency Versions Query Data Source (data.huaweicloud\_fgs\_dependency\_versions)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/fgs_dependency_versions)
- [EventGrid Event Channels Query Data Source (data.huaweicloud\_eg\_event\_channels)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/eg_event_channels)

### Resources

- [OBS Bucket Resource (huaweicloud\_obs\_bucket)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/obs_bucket)
- [FunctionGraph Function Resource (huaweicloud\_fgs\_function)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/fgs_function)
- [FunctionGraph Function Trigger Resource (huaweicloud\_fgs\_function\_trigger)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/fgs_function_trigger)

### Resource/Data Source Dependencies

```
data.huaweicloud_fgs_dependencies
    └── data.huaweicloud_fgs_dependency_versions
            └── huaweicloud_fgs_function

data.huaweicloud_eg_event_channels
    └── huaweicloud_fgs_function_trigger

huaweicloud_obs_bucket
    └── huaweicloud_fgs_function_trigger

huaweicloud_fgs_function
    └── huaweicloud_fgs_function_trigger
```

## Operation Steps

### 1. Script Preparation

Prepare the TF file (e.g., main.tf) in the specified workspace for writing the current best practice script, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. Refer to the "Preparation Before Deploying Huawei Cloud Resources" document for configuration introduction.

### 2. Create OBS Buckets

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create OBS bucket resources:

```hcl
# Variable definitions for OBS buckets
variable "source_bucket_name" {
  description = "The source bucket name of the OBS service"
  type        = string
}

variable "target_bucket_name" {
  description = "The target bucket name of the OBS service"
  type        = string
}

# Create a source OBS bucket resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_obs_bucket" "source" {
  bucket        = var.source_bucket_name
  acl           = "private"
  force_destroy = true
}

# Create a target OBS bucket resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_obs_bucket" "target" {
  bucket        = var.target_bucket_name
  acl           = "private"
  force_destroy = true
}
```

**Parameter Description**:

- **bucket**: OBS bucket name, assigned by referencing the input variables source\_bucket\_name and target\_bucket\_name
- **acl**: Bucket access control list, set to "private" for private access
- **force\_destroy**: Whether to force delete the bucket, set to true to allow deletion of non-empty buckets

### 3. Query FunctionGraph Dependencies Information Through Data Source

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to perform a data source query, the results of which are used to create FunctionGraph functions:

```hcl
# Get all FunctionGraph public dependency information under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block), used to create FunctionGraph function resources
data "huaweicloud_fgs_dependencies" "test" {
  type = "public"
  name = "pillow-7.1.2"
}

# Get version information for the specified dependency, used to create FunctionGraph function resources
data "huaweicloud_fgs_dependency_versions" "test" {
  dependency_id = try(data.huaweicloud_fgs_dependencies.test.packages[0].id, "NOT_FOUND")
  version       = 1
}
```

**Parameter Description**:

- **type**: Dependency type, set to "public" to query public dependencies
- **name**: Dependency name, set to "pillow-7.1.2" to query the Pillow image processing library
- **dependency\_id**: Dependency ID, assigned by referencing the return result from data source huaweicloud\_fgs\_dependencies
- **version**: Dependency version, set to 1 to query the first version

### 4. Query EventGrid Event Channels Information Through Data Source

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to perform a data source query, the results of which are used to create FunctionGraph EG triggers:

```hcl
# Get all EventGrid event channel information under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block), used to create FunctionGraph EG trigger resources
data "huaweicloud_eg_event_channels" "test" {
  provider_type = "OFFICIAL"
  name          = "default"
}
```

**Parameter Description**:

- **provider\_type**: Event channel provider type, set to "OFFICIAL" to query official event channels
- **name**: Event channel name, set to "default" to query the default event channel

### 5. Create FunctionGraph Function

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a FunctionGraph function resource:

```hcl
# Variable definitions for FunctionGraph resources
variable "function_name" {
  description = "The name of the FunctionGraph function"
  type        = string
}

variable "function_agency_name" {
  description = "The agency name that the FunctionGraph function uses"
  type        = string
}

variable "function_memory_size" {
  description = "The memory size of the function in MB"
  type        = number
  default     = 256
}

variable "function_timeout" {
  description = "The timeout of the function in seconds"
  type        = number
  default     = 40
}

variable "function_runtime" {
  description = "The runtime of the function"
  type        = string
  default     = "Python3.6"
}

variable "function_code" {
  description = "The source code of the function"
  type        = string
  default     = <<EOT
# -*-coding:utf-8 -*-
import os
import string
import random
import urllib.parse
import shutil
import contextlib
from PIL import Image
from obs import ObsClient

LOCAL_MOUNT_PATH = '/tmp/'

def handler(event, context):
    ak = context.getSecurityAccessKey()
    sk = context.getSecuritySecretKey()
    st = context.getSecurityToken()
    if ak == "" or sk == "" or st == "":
        context.getLogger().error('Failed to access OBS because no temporary '
                                  'AK, SK, or token has been obtained. Please '
                                  'set an agency.')
        return 'Failed to access OBS because no temporary AK, SK, or token ' \
               'has been obtained. Please set an agency. '

    obs_endpoint = context.getUserData('obs_endpoint')
    if not obs_endpoint:
        return 'obs_endpoint is not configured'

    output_bucket = context.getUserData('output_bucket')
    if not output_bucket:
        return 'output_bucket is not configured'

    compress_handler = ThumbnailHandler(context)
    with contextlib.ExitStack() as stack:
        # After upload the thumbnail image to obs, remove the local image
        stack.callback(shutil.rmtree,compress_handler.download_dir)
        data = event.get("data", None)
        return compress_handler.run(data)

class ThumbnailHandler:
    def __init__(self, context):
        self.logger = context.getLogger()
        obs_endpoint = context.getUserData("obs_endpoint")
        self.obs_client = new_obs_client(context, obs_endpoint)
        self.download_dir = gen_local_download_path()
        self.image_local_path = None
        self.src_bucket = None
        self.src_object_key = None
        self.output_bucket = context.getUserData("output_bucket")

    def parse_record(self, record):
        # parses the record to get src_bucket and input_object_key
        (src_bucket, src_object_key) = get_obs_obj_info(record)
        src_object_key = urllib.parse.unquote_plus(src_object_key)
        self.logger.info("src bucket name: %s", src_bucket)
        self.logger.info("src object key: %s", src_object_key)
        self.src_bucket = src_bucket
        self.src_object_key = src_object_key
        self.image_local_path = self.download_dir + src_object_key

    def run(self, record):
        self.parse_record(record)
        # Download the original image from obs to local tmp dir.
        if not self.download_from_obs():
            return "ERROR"
        # Thumbnail original image
        thumbnail_object_key, thumbnail_file_path = self.thumbnail()
        self.logger.info("thumbnail_object_key: %s, thumbnail_file_path: %s",
                        thumbnail_object_key, thumbnail_file_path)
        # Upload thumbnail image to obs
        if not self.upload_file_to_obs(thumbnail_object_key,
                                    thumbnail_file_path):
            return "ERROR"
        return "OK"

    def download_from_obs(self):
        resp = self.obs_client. \
            getObject(self.src_bucket, self.src_object_key,
                      downloadPath=self.image_local_path)
        if resp.status < 300:
            return True
        else:
            self.logger.error('failed to download from obs, '
                              'errorCode: %s, errorMessage: %s' % (
                                  resp.errorCode, resp.errorMessage))
            return False

    def upload_file_to_obs(self, object_key, local_file):
        resp = self.obs_client.putFile(self.output_bucket,
                                       object_key, local_file)
        if resp.status < 300:
            return True
        else:
            self.logger.error('failed to upload file to obs, errorCode: %s, '
                              'errorMessage: %s' % (resp.errorCode,
                                                    resp.errorMessage))
            return False

    def thumbnail(self):
        image = Image.open(self.image_local_path)
        image_w, image_h = image.size
        new_image_w, new_image_h = (int(image_w / 2), int(image_h / 2))

        image.thumbnail((new_image_w, new_image_h), resample=Image.LANCZOS)

        (path, filename) = os.path.split(self.src_object_key)
        if path != "" and not path.endswith("/"):
            path = path + "/"
        (filename, ext) = os.path.splitext(filename)
        ext_lower = ext.lower()

        thumbnail_object_key = path + filename + \
                           "_thumbnail_h_" + str(new_image_h) + \
                           "_w_" + str(new_image_w) + ext

        if hasattr(image, '_getexif'):
            image.info.pop('exif', None)

        if new_image_w * new_image_h < 500000:
            webp_ext = '.webp'
            thumbnail_object_key = path + filename + \
                                  "_thumbnail_h_" + str(new_image_h) + \
                                  "_w_" + str(new_image_w) + webp_ext
            thumbnail_file_path = self.download_dir + path + filename + \
                                 "_thumbnail_h_" + str(new_image_h) + \
                                 "_w_" + str(new_image_w) + webp_ext
            image.save(thumbnail_file_path, format='WEBP', quality=80, method=6)
        elif ext_lower in ['.jpg', '.jpeg']:
            thumbnail_file_path = self.download_dir + path + filename + \
                                 "_thumbnail_h_" + str(new_image_h) + \
                                 "_w_" + str(new_image_w) + ext
            image.save(thumbnail_file_path, quality=85, optimize=True, progressive=True)
        elif ext_lower == '.png':
            thumbnail_file_path = self.download_dir + path + filename + \
                                 "_thumbnail_h_" + str(new_image_h) + \
                                 "_w_" + str(new_image_w) + ext
            image.save(thumbnail_file_path, optimize=True, compress_level=6)
        else:
            thumbnail_file_path = self.download_dir + path + filename + \
                                 "_thumbnail_h_" + str(new_image_h) + \
                                 "_w_" + str(new_image_w) + ext
            image.save(thumbnail_file_path, quality=85, optimize=True)

        return thumbnail_object_key, thumbnail_file_path

# generate a temporary directory for downloading things
# from OBS and compress them.
def gen_local_download_path():
    letters = string.ascii_letters
    download_dir = LOCAL_MOUNT_PATH + ''.join(
        random.choice(letters) for i in range(16)) + '/'
    os.makedirs(download_dir)
    return download_dir

def new_obs_client(context, obs_server):
    ak = context.getSecurityAccessKey()
    sk = context.getSecuritySecretKey()
    st = context.getSecurityToken()
    return ObsClient(access_key_id=ak, secret_access_key=sk, security_token=st, server=obs_server)

def get_obs_obj_info(record):
    if 's3' in record:
        s3 = record['s3']
        return s3['bucket']['name'], s3['object']['key']
    else:
        obs_info = record['obs']
        return obs_info['bucket']['name'], obs_info['object']['key']
EOT
}

variable "function_description" {
  description = "The description of the function"
  type        = string
  default     = ""
}

# Create a FunctionGraph function resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_fgs_function" "test" {
  name        = var.function_name
  agency      = var.function_agency_name
  app         = "default"
  handler     = "index.handler"
  memory_size = var.function_memory_size
  timeout     = var.function_timeout
  runtime     = var.function_runtime
  code_type   = "inline"
  func_code   = base64encode(var.function_code)
  description = var.function_description
  depend_list = data.huaweicloud_fgs_dependency_versions.test.versions[*].id

  user_data = jsonencode({
    "output_bucket" = var.target_bucket_name
    "obs_endpoint"  = format("obs.%s.myhuaweicloud.com", var.region_name)
  })
}
```

**Parameter Description**:

- **name**: FunctionGraph function name, assigned by referencing the input variable function\_name
- **agency**: Function agency name, assigned by referencing the input variable function\_agency\_name, used for function permissions to access other Huawei Cloud services
- **app**: Application name the function belongs to, set to "default" to use the default application
- **handler**: Function entry point, set to "index.handler" indicating the handler method is in the index.py file
- **memory\_size**: Function memory size (MB), assigned by referencing the input variable function\_memory\_size, default value is 256MB
- **timeout**: Function timeout (seconds), assigned by referencing the input variable function\_timeout, default value is 40 seconds
- **runtime**: Function runtime environment, assigned by referencing the input variable function\_runtime, default value is Python3.6
- **code\_type**: Code type, set to "inline" for inline code
- **func\_code**: Function source code (for automatic image compression), assigned by base64 encoding the input variable function\_code
- **description**: Function description information, assigned by referencing the input variable function\_description
- **depend\_list**: Function dependency list, assigned by referencing the return result from data source huaweicloud\_fgs\_dependency\_versions
- **user\_data**: User custom data, in JSON format containing output bucket name and OBS endpoint information

### 6. Create FunctionGraph EG Trigger

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a FunctionGraph EG trigger resource:

```hcl
# Variable definitions for EG trigger
variable "trigger_status" {
  description = "The status of the timer trigger"
  type        = string
  default     = "ACTIVE"
}

variable "trigger_name_suffix" {
  description = "The suffix name of the OBS trigger"
  type        = string
}

variable "trigger_agency_name" {
  description = "The agency name that the OBS trigger uses"
  type        = string
  default     = "fgs_to_eg"
}

# Create a FunctionGraph EG trigger resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_fgs_function_trigger" "test" {
  depends_on = [huaweicloud_obs_bucket.source]

  function_urn                   = huaweicloud_fgs_function.test.urn
  type                           = "EVENTGRID"
  cascade_delete_eg_subscription = true
  status                         = var.trigger_status
  event_data                     = jsonencode({
    "channel_id"           = try(data.huaweicloud_eg_event_channels.test.channels[0].id, "")
    "channel_name"         = try(data.huaweicloud_eg_event_channels.test.channels[0].name, "")
    "source_name"          = "HC.OBS.DWR"
    "trigger_name"         = var.trigger_name_suffix
    "agency"               = var.trigger_agency_name
    "bucket"               = var.source_bucket_name
    "event_types"          = ["OBS:DWR:ObjectCreated:PUT", "OBS:DWR:ObjectCreated:POST"]
    "Key_encode"           = true
  })

  lifecycle {
    ignore_changes = [
      event_data,
    ]
  }
}
```

**Parameter Description**:

- **depends\_on**: Explicit dependency relationship, ensuring the source OBS bucket exists before trigger creation
- **function\_urn**: URN of the FunctionGraph function associated with the trigger, assigned by referencing huaweicloud\_fgs\_function.test.urn
- **type**: Trigger type, set to "EVENTGRID" for EG trigger
- **cascade\_delete\_eg\_subscription**: Whether to cascade delete EG subscription, set to true to delete EG subscription when function is deleted
- **status**: Trigger status, assigned by referencing the input variable trigger\_status, default value is "ACTIVE" for active status
- **event\_data**: Trigger event data, in JSON format containing the following parameters:
  - **channel\_id**: Event channel ID, assigned by referencing the return result from data source huaweicloud\_eg\_event\_channels
  - **channel\_name**: Event channel name, assigned by referencing the return result from data source huaweicloud\_eg\_event\_channels
  - **source\_name**: Event source name, set to "HC.OBS.DWR" for OBS data workflow event source
  - **trigger\_name**: Trigger name suffix, assigned by referencing the input variable trigger\_name\_suffix
  - **agency**: Agency name used by the trigger, assigned by referencing the input variable trigger\_agency\_name
  - **bucket**: OBS bucket name to monitor, assigned by referencing the input variable source\_bucket\_name
  - **event\_types**: Event types to monitor, set to monitor OBS object creation events
  - **Key\_encode**: Whether to encode object keys, set to true to enable encoding

### 7. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources and data sources use input variables to assign values to configuration content. These input parameters need to be manually entered during subsequent deployments. At the same time, Terraform provides a method to preset these configurations through `tfvars` files, which can avoid repeated input during each execution.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# OBS bucket configuration
source_bucket_name   = "tf-test-bucket-source"
target_bucket_name   = "tf-test-bucket-target"

# Function basic information
function_name        = "tf-test-function-image-thumbnail"
function_agency_name = "function_all_trust"

# Trigger configuration
trigger_name_suffix  = "demo"
```

**Usage**:

1. Save the above content as `terraform.tfvars` file in the working directory (this file name allows users to automatically import the content of this `tfvars` file when executing terraform commands; for other names, `.auto` needs to be added before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values as needed
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values from this file

In addition to using `terraform.tfvars` file, variable values can also be set in the following ways:

1. Command line parameters: `terraform apply -var="function_name=my-function" -var="source_bucket_name=my-bucket"`
2. Environment variables: `export TF_VAR_function_name=my-function`
3. Custom named variable files: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set in multiple ways, Terraform will use the variable value according to the following priority: command line parameters > variable files > environment variables > default values.

### 8. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create resources:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming the resource plan is correct, run `terraform apply` to start creating OBS buckets, FunctionGraph function, and EG trigger
4. Run `terraform show` to view the created OBS buckets, FunctionGraph function, and EG trigger

## Reference Information

- [Huawei Cloud FunctionGraph Product Documentation](https://support.huaweicloud.com/functiongraph/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For FunctionGraph EG Trigger](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/fgs/triggers/eg)

# Deploy Timer Trigger

## Application Scenario

FunctionGraph's timer trigger (Timer Trigger) is a trigger type based on time scheduling that supports both Cron expression and fixed interval scheduling methods. Through timer triggers, you can implement scheduled tasks, periodic data processing, scheduled backups, scheduled monitoring, and other functions.

Timer triggers are particularly suitable for tasks that need to be executed at fixed time intervals or specific time points, such as data cleanup, report generation, system monitoring, scheduled notifications, etc. This best practice will introduce how to use Terraform to automatically deploy a FunctionGraph function with a timer trigger.

## Related Resources/Data Sources

This best practice involves the following main resources and data sources:

### Data Sources

This best practice does not use data sources.

### Resources

- [FunctionGraph Function Resource (huaweicloud\_fgs\_function)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/fgs_function)
- [FunctionGraph Function Trigger Resource (huaweicloud\_fgs\_function\_trigger)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/fgs_function_trigger)

### Resource/Data Source Dependencies

```
huaweicloud_fgs_function
    └── huaweicloud_fgs_function_trigger
```

## Operation Steps

### 1. Script Preparation

Prepare the TF file (e.g., main.tf) in the specified workspace for writing the current best practice script, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. Refer to the "Preparation Before Deploying Huawei Cloud Resources" document for configuration introduction.

### 2. Create FunctionGraph Function

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a FunctionGraph function resource:

```hcl
# Variable definitions for FunctionGraph resources
variable "function_name" {
  description = "The name of the FunctionGraph function"
  type        = string
}

variable "function_memory_size" {
  description = "The memory size of the function in MB"
  type        = number
  default     = 128
}

variable "function_timeout" {
  description = "The timeout of the function in seconds"
  type        = number
  default     = 10
}

variable "function_runtime" {
  description = "The runtime of the function"
  type        = string
  default     = "Python2.7"
}

variable "function_code" {
  description = "The source code of the function"
  type        = string
  default     = <<EOT
import json

def handler(event, context):
    print("FunctionGraph timer trigger executed!")
    print("Event:", json.dumps(event))
    print("Context:", json.dumps(context))
    return {
        'statusCode': 200,
        'body': json.dumps('Hello, FunctionGraph!')
    }
EOT
}

variable "function_description" {
  description = "The description of the function"
  type        = string
  default     = ""
}

# Create a FunctionGraph function resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_fgs_function" "test" {
  name        = var.function_name
  app         = "default"
  handler     = "index.handler"
  memory_size = var.function_memory_size
  timeout     = var.function_timeout
  runtime     = var.function_runtime
  code_type   = "inline"
  func_code   = base64encode(var.function_code)
  description = var.function_description
}
```

**Parameter Description**:

- **name**: FunctionGraph function name, assigned by referencing the input variable function\_name
- **app**: Application name the function belongs to, set to "default" to use the default application
- **handler**: Function entry point, set to "index.handler" indicating the handler method is in the index.py file
- **memory\_size**: Function memory size (MB), assigned by referencing the input variable function\_memory\_size, default value is 128MB
- **timeout**: Function timeout (seconds), assigned by referencing the input variable function\_timeout, default value is 10 seconds
- **runtime**: Function runtime environment, assigned by referencing the input variable function\_runtime, default value is Python2.7
- **code\_type**: Code type, set to "inline" for inline code
- **func\_code**: Function source code, assigned by base64 encoding the input variable function\_code
- **description**: Function description information, assigned by referencing the input variable function\_description

### 3. Create FunctionGraph Timer Trigger

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a FunctionGraph timer trigger resource:

```hcl
# Variable definitions for timer trigger
variable "trigger_status" {
  description = "The status of the FunctionGraph timer trigger"
  type        = string
  default     = "ACTIVE"
}

variable "trigger_name" {
  description = "The name of the FunctionGraph timer trigger"
  type        = string
}

variable "trigger_schedule_type" {
  description = "The schedule type of the FunctionGraph timer trigger"
  type        = string
  default     = "Cron"
}

variable "trigger_sync_execution" {
  description = "Whether to execute the function synchronously"
  type        = bool
  default     = false
}

variable "trigger_user_event" {
  description = "The user event description for the FunctionGraph timer trigger"
  type        = string
  default     = ""
}

variable "trigger_schedule" {
  description = "The schedule expression for the FunctionGraph timer trigger"
  type        = string
  default     = "@every 1h30m"
}

# Create a FunctionGraph timer trigger resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_fgs_function_trigger" "test" {
  function_urn = huaweicloud_fgs_function.test.urn
  type         = "TIMER"
  status       = var.trigger_status
  event_data   = jsonencode({
    "name"           = var.trigger_name
    "schedule_type"  = var.trigger_schedule_type
    "sync_execution" = var.trigger_sync_execution
    "user_event"     = var.trigger_user_event
    "schedule"       = var.trigger_schedule
  })
}
```

**Parameter Description**:

- **function\_urn**: URN of the FunctionGraph function associated with the trigger, assigned by referencing huaweicloud\_fgs\_function.test.urn
- **type**: Trigger type, set to "TIMER" for timer trigger
- **status**: Trigger status, assigned by referencing the input variable trigger\_status, default value is "ACTIVE" for active status
- **event\_data**: Trigger event data, in JSON format containing the following parameters:
  - **name**: Trigger name, assigned by referencing the input variable trigger\_name
  - **schedule\_type**: Schedule type, assigned by referencing the input variable trigger\_schedule\_type, default value is "Cron" for Cron expression
  - **sync\_execution**: Whether to execute synchronously, assigned by referencing the input variable trigger\_sync\_execution, default value is false for asynchronous execution
  - **user\_event**: User event description, assigned by referencing the input variable trigger\_user\_event
  - **schedule**: Schedule expression, assigned by referencing the input variable trigger\_schedule, supports Cron expression and fixed interval formats

### 4. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources and data sources use input variables to assign values to configuration content. These input parameters need to be manually entered during subsequent deployments. At the same time, Terraform provides a method to preset these configurations through `tfvars` files, which can avoid repeated input during each execution.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# Function basic information
function_name        = "tf_test_timer_function"
function_description = "Created by Terraform for timer trigger example"

# Trigger configuration
trigger_name       = "tf_test_timer_cron"
trigger_user_event = "Timer trigger with Cron schedule type, triggered every three days"
trigger_schedule   = "@every 3d"
```

**Usage**:

1. Save the above content as `terraform.tfvars` file in the working directory (this file name allows users to automatically import the content of this `tfvars` file when executing terraform commands; for other names, `.auto` needs to be added before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values as needed
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values from this file

In addition to using `terraform.tfvars` file, variable values can also be set in the following ways:

1. Command line parameters: `terraform apply -var="function_name=my-function" -var="trigger_name=my-trigger"`
2. Environment variables: `export TF_VAR_function_name=my-function`
3. Custom named variable files: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set in multiple ways, Terraform will use the variable value according to the following priority: command line parameters > variable files > environment variables > default values.

### 5. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create resources:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming the resource plan is correct, run `terraform apply` to start creating FunctionGraph function and timer trigger
4. Run `terraform show` to view the created FunctionGraph function and timer trigger

## Reference Information

- [Huawei Cloud FunctionGraph Product Documentation](https://support.huaweicloud.com/functiongraph/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For FunctionGraph Timer Trigger](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/fgs/triggers/timer)
