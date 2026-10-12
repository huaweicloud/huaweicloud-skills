# IAM Policies - DWS Spec Planner

## Skill Type Declaration

This skill is a **planning advisory skill** that primarily performs DWS data warehouse configuration planning and sizing through user input survey and built-in reference documents, **without directly calling Huawei Cloud OpenAPI**.

## Required Permissions

No API permissions are required. The skill core workflow (requirement survey -> architecture mode confirmation -> CPU core calculation -> flavor selection -> storage capacity calculation -> report generation) is entirely based on user input and built-in reference documents.

## Notes

- The static DWS dedicated flavor catalog in [ECS Flavor Catalog](ecs-flavor-catalog.md) is used for flavor selection, no runtime API query needed
- If future versions add automatic flavor availability query or cluster creation capabilities, corresponding permissions will need to be added
