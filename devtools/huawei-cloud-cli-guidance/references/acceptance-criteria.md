# Skill Testing Criteria
**Overview:**
>This document explains the pass/fail criteria for testing this skill;  
> Applicable scope: skill testing

***If any of the following tests fail, it indicates that koocli status is in a partially unavailable state:***

1. **✅ KooCLI Version Check Passed**: Confirm KooCLI is correctly installed and version is sufficiently new. Version number is fundamental; if command doesn't exist or version is too old, all subsequent checks are meaningless.
2. **✅ Configuration Check Passed**: Example- Profile: default, Mode: AKSK, Region: cn-north-4. Confirm authentication configuration is valid.  
   Without valid AKSK configuration, all API calls will fail. Check profile name, authentication mode, and region to ensure configuration is complete.
3. **✅ IAM Service Connectivity Check Passed**: Successfully query user list. IAM is Huawei Cloud's core identity service; if IAM cannot be accessed, it indicates authentication or network issues. Successful user list query proves:
   >- Authentication is valid (AKSK correct)
   >- Network connectivity (can access Huawei Cloud API)
   >- Sufficient permissions (has IAM query permissions)
4. **✅ ECS Service Connectivity Check Passed**: Successfully query instance specifications. ECS is the core compute service, testing project-level API. Unlike IAM, ECS requires project_id parameter, verifying:
   >- Project permission configuration correct
   >- Cross-service API calls normal
   >- Complex parameter passing normal
5. **✅ OBS Integration Component Check Passed**: obsutil version 5.5.9. OBS is an independent component, verifying integration functionality. OBS uses independent authentication system, checking:
   >- obsutil component properly integrated
   >- OBS configuration status
   >- Component version compatibility

6. **✅ VPC Service Availability Check Passed**: Service help normal.
   Verify service discovery mechanism. Check VPC service help to confirm:
   >- Service metadata loading normal
   >- New service APIs discoverable
   >- Help system working normally

7. **✅ Help System Check Passed**: Help command normal.
   Help system is the foundation for using CLI. Confirm:
   >- Global help available
   >- Command syntax queryable
   >- Foundation for users to solve problems independently

8. **✅ Service Discovery Function Check Passed**: Available service list normal.
   Verify KooCLI can discover all Huawei Cloud services. Ensure:
   >- Metadata cache normal
   >- Service list complete
   >- New services automatically discoverable

9. **✅ Output Format Control Check Passed**: Table format output normal.
   Verify output formatting functionality. Table format is for human reading, confirm:
   >- Data formatting normal
   >- Terminal adaptation normal
   >- Output readability

10. **✅ JSON Output and JMESPath Query Check Passed**: Data filtering functionality normal.
    Verify functionality required for automation scripts. JSON output and JMESPath are:
    >- Foundation for script processing
    >- Key for data extraction
    >- Core of automated operations

11. **✅ Debug Mode Check Passed**: dry-run mode normal.
    Verify debugging and pre-check functionality. dry-run mode:
    >- Avoids accidental operations
    >- Checks parameter correctness
    >- Learns API usage

12. **✅ Skeleton Generation Function Check Passed**: JSON parameter skeleton generation normal.
    Verify complex parameter construction assistance functionality. Skeleton generation:
    >- Helps understand API parameter structure
    >- Provides parameter templates
    >- Reduces usage barrier

13. **✅ Network Connectivity Check Passed**: Huawei Cloud API endpoint accessible.
    Confirm basic network connection. Direct curl test:
    >- DNS resolution normal
    >- Network routing normal
    >- API endpoint reachable

14. **✅ OBS Connectivity Check Passed**: OBS service connection normal.
    Verify OBS independent authentication system. OBS has independent configuration:
    >- OBS authentication configuration correct
    >- OBS service endpoint reachable
    >- OBS command execution normal

15. **✅ Metadata Function Check Passed**: Metadata management functionality normal.
    Verify KooCLI core architecture. Metadata system:
    >- Is the foundation for KooCLI dynamic API loading
    >- Affects service discovery and parameter validation
    >- Requires regular updates

16. **✅ Update Function Check Passed**: Currently at latest version.
    Verify maintenance and upgrade capability. Update function:
    >- Ensures latest features can be obtained
    >- Guarantees security patches can be applied
    >- Verifies version management mechanism

## Testing Scope

#### **1. Cover All Critical Paths**
- **Authentication Path**: AKSK configuration → IAM verification
- **Service Path**: Core services (ECS/VPC) → Extended services (OBS)
- **Function Path**: Basic commands → Advanced features → Debugging tools
- **Network Path**: Local → Network → API endpoint → Service response

#### **2. Verify All Usage Scenarios**
- **Interactive Use**: Help, table output, dry-run
- **Script Automation**: JSON output, JMESPath filtering
- **Problem Troubleshooting**: Debug mode, network testing
- **Learning Exploration**: Skeleton generation, service discovery

#### **3. Test All Dependent Components**
- **CLI Core**: Version, help, command parsing
- **Authentication System**: AKSK, profile, region
- **Service Integration**: Metadata, API discovery, parameter validation
- **Network Components**: DNS, routing, endpoint connection
- **Output System**: Formatting, filtering, encoding

#### **4. Layered Progressive Verification**
```
Layer 1: CLI existence → Layer 2: Authentication validity → 
Layer 3: Core services → Layer 4: Extended services → 
Layer 5: Function features → Layer 6: Network connectivity → 
Layer 7: Maintenance capability
```