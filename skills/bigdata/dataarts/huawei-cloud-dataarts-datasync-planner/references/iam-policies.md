# IAM Policies - DataArts DataSync Planner

## Skill Type Declaration

This skill is a **planning advisory skill** that primarily performs data sync pipeline planning and product selection through user input survey and built-in reference documents, **without directly calling Huawei Cloud OpenAPI**.

## Required Permissions

No API permissions are required. The skill core workflow (pipeline identification -> real-time/offline classification -> product matching -> solution design -> report generation) is entirely based on user input and built-in reference documents.

## Notes

- The static product capability matrix and instance spec constraints in the reference documents are used for product matching and spec selection, no runtime API query needed
- If future versions add automatic pipeline survey or sync job creation capabilities, corresponding permissions will need to be added
