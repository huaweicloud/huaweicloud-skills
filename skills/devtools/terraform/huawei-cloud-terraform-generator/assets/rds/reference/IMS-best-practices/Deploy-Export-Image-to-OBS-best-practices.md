# Deploy Export Image to OBS

## Application Scenario

Image Management Service (IMS) is an image management service provided by Huawei Cloud, supporting image creation, sharing, copying, exporting, and other functions. By exporting images to OBS, you can export private images as image files and store them in OBS buckets, achieving image backup, migration, and offline storage. This best practice will introduce how to use Terraform to automatically deploy export images to OBS, including querying private images, creating OBS buckets, and exporting images to OBS buckets.

## Related Resources/Data Sources

This best practice involves the following main resources and data sources:

### Data Sources

- [Images Data Source (huaweicloud\_images\_images)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/images_images)

### Resources

- [OBS Bucket Resource (huaweicloud\_obs\_bucket)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/obs_bucket)
- [Image Export Resource (huaweicloud\_ims\_image\_export)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/ims_image_export)

### Resource/Data Source Dependencies

```
data.huaweicloud_images_images
    └── huaweicloud_obs_bucket
        └── huaweicloud_ims_image_export
```

> Note: Image export requires creating an OBS bucket first. The exported image files will be stored in the specified OBS bucket, supporting multiple file formats including vhd, zvhd, vmdk, raw, qcow2, zvhd2, vdi, etc.

## Operation Steps

### 1. Script Preparation

Prepare the TF file (e.g., main.tf) in the specified workspace for writing the current best practice script, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. Refer to the "Preparation Before Deploying Huawei Cloud Resources" document for configuration introduction.

### 2. Query Private Images

Add the following script to the TF file (e.g., main.tf) to query private images:

```hcl
variable "region_name" {
  description = "The region where the CDN domain is located"
  type        = string
}

variable "image_type" {
  description = "The type of images to filter (ECS, BMS, etc.)"
  type        = string
  default     = ""
}

variable "image_os" {
  description = "The OS of images to filter (Ubuntu, CentOS, etc.)"
  type        = string
  default     = ""
}

variable "image_name_regex" {
  description = "The regex pattern to filter images by name"
  type        = string
  default     = ""
}

# Query all private images owned by the current user in the specified region
data "huaweicloud_images_images" "test" {
  visibility = "private"
  image_type = var.image_type != "" ? var.image_type : null
  os         = var.image_os != "" ? var.image_os : null
  name_regex = var.image_name_regex != "" ? var.image_name_regex : null
}

# Filter images with status "active"
locals {
  active_images = [
    for image in data.huaweicloud_images_images.test.images : image if image.status == "active"
  ]
}
```

**Parameter Description**:

- **visibility**: Image visibility, set to "private" to query private images
- **image\_type**: Image type, assigned by referencing input variable image\_type, optional parameter, used to filter images of specific types (such as ECS, BMS, etc.)
- **os**: Operating system type, assigned by referencing input variable image\_os, optional parameter, used to filter images of specific operating systems (such as Ubuntu, CentOS, etc.)
- **name\_regex**: Image name regular expression, assigned by referencing input variable image\_name\_regex, optional parameter, used to filter images by name
- **active\_images**: Local variable, used to filter images with status "active", only images with status "active" can be exported

> Note: Only images with status "active" can be exported. You can filter images to be exported by setting parameters such as image\_type, image\_os, name\_regex, etc.

### 3. Create OBS Bucket

Add the following script to the TF file (e.g., main.tf) to create OBS bucket:

```hcl
variable "obs_bucket_name" {
  description = "The name of the OBS bucket for storing exported images"
  type        = string
}

variable "obs_bucket_tags" {
  description = "The tags of the OBS bucket"
  type        = map(string)
  default     = {}
}

# Create OBS bucket resource in the specified region for storing exported image files
resource "huaweicloud_obs_bucket" "test" {
  bucket        = var.obs_bucket_name
  storage_class = "STANDARD"
  region        = var.region_name

  tags = var.obs_bucket_tags
}
```

**Parameter Description**:

- **bucket**: OBS bucket name, assigned by referencing input variable obs\_bucket\_name, globally unique
- **storage\_class**: Storage class, set to "STANDARD" for standard storage
- **region**: Region, assigned by referencing input variable region\_name
- **tags**: Tags, assigned by referencing input variable obs\_bucket\_tags, optional parameter

> Note: OBS bucket name needs to be globally unique. It is recommended to use meaningful naming rules. Storage class can be selected according to actual needs. Standard storage is suitable for frequently accessed scenarios.

### 4. Export Images to OBS

Add the following script to the TF file (e.g., main.tf) to export images to OBS:

```hcl
variable "file_format" {
  description = "The file format of the exported image (vhd, zvhd, vmdk, raw, qcow2, zvhd2, vdi)"
  type        = string
  default     = "zvhd2"
}

# Create image export resource in the specified region, exporting each image to OBS bucket
resource "huaweicloud_ims_image_export" "test" {
  count = length(local.active_images)

  region      = var.region_name
  image_id    = local.active_images[count.index].id
  bucket_url  = "${huaweicloud_obs_bucket.test.bucket}:${local.active_images[count.index].name}-${local.active_images[count.index].id}.${var.file_format}"
  file_format = var.file_format

  depends_on = [huaweicloud_obs_bucket.test]
}
```

**Parameter Description**:

- **count**: Number of resource creations, assigned by referencing the length of local variable active\_images, creating one export task for each active image
- **region**: Region, assigned by referencing input variable region\_name
- **image\_id**: Image ID, assigned by referencing local variable active\_images
- **bucket\_url**: OBS bucket URL, format is "bucket:object\_key", generated by combining OBS bucket name, image name, image ID, and file format
- **file\_format**: File format, assigned by referencing input variable file\_format, supporting formats such as vhd, zvhd, vmdk, raw, qcow2, zvhd2, vdi, default value is "zvhd2"
- **depends\_on**: Explicit dependency relationship, ensuring to export images after OBS bucket is created

> Note: Image export may take a long time, please be patient. The exported image files will be stored in the specified OBS bucket, with file name format as "image-name-image-id.file-format". Supported file formats include vhd, zvhd, vmdk, raw, qcow2, zvhd2, vdi, etc. It is recommended to select an appropriate format according to actual needs.

### 5. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources and data sources use input variables to assign configuration content. These input parameters need to be manually entered during subsequent deployment. At the same time, Terraform provides a method to preset these configurations through `tfvars` files, which can avoid repeated input during each execution.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# OBS Bucket Configuration
obs_bucket_name = "my-image-backup-bucket-test"

# Image Export Configuration
file_format = "zvhd2"
```

**Usage**:

1. Save the above content as a `terraform.tfvars` file in the working directory (this filename allows users to automatically import the content of this `tfvars` file when executing terraform commands. For other naming, you need to add `.auto` before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values according to actual needs, especially:
   - `region_name` needs to be set to the region where resources are located
   - `obs_bucket_name` needs to be set to OBS bucket name, which needs to be globally unique
   - `file_format` can be set to exported file format, supporting formats such as vhd, zvhd, vmdk, raw, qcow2, zvhd2, vdi, default value is "zvhd2"
   - `image_type` can be set to image type filter condition, optional parameter
   - `image_os` can be set to operating system type filter condition, optional parameter
   - `image_name_regex` can be set to image name regular expression filter condition, optional parameter
   - `obs_bucket_tags` can be set to OBS bucket tags, optional parameter
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values in this file

In addition to using the `terraform.tfvars` file, you can also set variable values in the following ways:

1. Command line parameters: `terraform apply -var="obs_bucket_name=my-bucket" -var="file_format=zvhd2"`
2. Environment variables: `export TF_VAR_obs_bucket_name=my-bucket` and `export TF_VAR_file_format=zvhd2`
3. Custom named variable file: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set through multiple methods, Terraform will use variable values according to the following priority: command line parameters > variable file > environment variables > default values. Image export may take a long time, please be patient. The exported image files will be stored in the specified OBS bucket and can be downloaded and used through OBS console or API.

### 6. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create export images to OBS:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming that the resource plan is correct, run `terraform apply` to start creating OBS bucket and exporting images
4. Run `terraform show` to view the details of the created export images to OBS

> Note: Image export may take a long time, please be patient. The exported image files will be stored in the specified OBS bucket and can be downloaded and used through OBS console or API. Only images with status "active" can be exported. Please ensure the image status is correct.

## Reference Information

- [Huawei Cloud IMS Product Documentation](https://support.huaweicloud.com/ims/index.html)
- [Huawei Cloud OBS Product Documentation](https://support.huaweicloud.com/obs/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For Export Image to OBS](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/ims/export-image-to-obs)
