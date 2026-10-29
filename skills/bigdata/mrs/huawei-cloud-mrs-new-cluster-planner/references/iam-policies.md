# IAM Policies - MRS New Cluster Planner

## Skill Type Declaration

This skill is a **planning advisory skill** that primarily performs MRS new cluster planning and sizing through user input investigation and built-in reference documents, **without directly calling Huawei Cloud OpenAPI**.

## Required Permissions

No API permissions are required. The skill core workflow (component investigation -> cluster type matching -> node spec planning -> storage disk planning -> report generation) is entirely based on user input and built-in reference documents.

## Notes

- The static ECS flavor catalog in [ECS Flavor Catalog](ecs-flavor-catalog.md) is used for flavor selection, no runtime API query needed
- If future versions add automatic MRS cluster query or creation capabilities, corresponding permissions will need to be added
