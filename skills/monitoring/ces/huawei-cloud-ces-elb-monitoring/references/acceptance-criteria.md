# ELB Monitoring Skill Acceptance Criteria

## Overview

This document defines the acceptance criteria for the Huawei Cloud ELB Monitoring skill. All criteria must be met before the skill is considered production-ready.

## 1. Functional Requirements

### 1.1 ELB Instance Discovery

- [ ] Can list all ELB instances in a region
- [ ] Can identify ELB type (Dedicated vs Shared)
- [ ] Can retrieve ELB instance details
- [ ] Can list listeners for an ELB instance
- [ ] Can list backend server groups (Dedicated ELB)

### 1.2 Basic Metric Query (Both ELB Types)

- [ ] Can query concurrent connections (`m1_cps`)
- [ ] Can query active connections (`m2_act_conn`)
- [ ] Can query inactive connections (`m3_inact_conn`)
- [ ] Can query new connections per second (`m4_ncps`)
- [ ] Can query inbound packet rate (`m5_in_packets`)
- [ ] Can query outbound packet rate (`m6_out_packets`)
- [ ] Can query inbound bandwidth (`m7_in_Bps`)
- [ ] Can query outbound bandwidth (`m8_out_Bps`)
- [ ] Can query abnormal host count (`m9_abnormal_host_count`)

### 1.3 Advanced Metric Query (Dedicated ELB Only)

- [ ] Can query HTTP status codes (`elb_http_2xx`, `elb_http_4xx`, `elb_http_5xx`)
- [ ] Can query HTTP request ratios (`l7_2xx_ratio`, `l7_4xx_ratio`, `l7_5xx_ratio`)
- [ ] Can query traffic mirroring metrics
- [ ] Can query backend server group metrics
- [ ] Can query L7 bandwidth metrics

### 1.4 Multi-Dimension Query

- [ ] Can query metrics at load balancer level (`lbaas_instance_id`)
- [ ] Can query metrics at listener level (`lbaas_listener_id`)
- [ ] Can query metrics at backend server group level (`lbaas_pool_id`) - Dedicated ELB only
- [ ] Can query metrics at availability zone level (`lbaas_az`) - Dedicated ELB only

### 1.5 Time Range Support

- [ ] Supports last 1 hour query
- [ ] Supports last 6 hours query
- [ ] Supports last 24 hours query
- [ ] Supports last 7 days query
- [ ] Supports custom time range
- [ ] Properly handles Unix timestamp in milliseconds

### 1.6 Aggregation Methods

- [ ] Supports `average` filter
- [ ] Supports `max` filter
- [ ] Supports `min` filter
- [ ] Supports `sum` filter
- [ ] Supports `variance` filter

### 1.7 Multiple Metrics Query

- [ ] Can query multiple metrics in a single BatchListMetricData call
- [ ] Properly handles mixed dimension queries

### 1.8 Alarm Management

- [ ] Can list existing alarms
- [ ] Can list alarm templates
- [ ] Can create alarm rules for ELB metrics
- [ ] Can view alarm details

## 2. Non-Functional Requirements

### 2.1 Performance

- [ ] CLI command response time < 2 seconds for list operations
- [ ] Metric query response time < 5 seconds for 1-hour range
- [ ] Multiple metrics query response time < 10 seconds
- [ ] Memory usage < 100MB during typical operations

### 2.2 Reliability

- [ ] Handles network timeouts gracefully
- [ ] Handles rate limiting with appropriate retry
- [ ] Handles invalid parameters with clear error messages
- [ ] Handles missing resources without crashing

### 2.3 Security

- [ ] Never exposes AK/SK values in output
- [ ] Never logs sensitive credentials
- [ ] Uses HTTPS for all API calls
- [ ] Follows principle of least privilege for IAM

### 2.4 Usability

- [ ] Clear error messages for common issues
- [ ] Helpful suggestions when errors occur
- [ ] Consistent output format
- [ ] Proper handling of empty results

## 3. Error Handling Requirements

### 3.1 CLI Errors

- [ ] Handles CLI not installed
- [ ] Handles CLI version incompatibility
- [ ] Handles configuration missing
- [ ] Handles invalid credentials

### 3.2 Permission Errors

- [ ] Detects insufficient ELB permissions
- [ ] Detects insufficient CES permissions
- [ ] Provides clear guidance for permission resolution
- [ ] References IAM policies documentation

### 3.3 Resource Errors

- [ ] Handles ELB instance not found
- [ ] Handles listener not found
- [ ] Handles backend server group not found
- [ ] Handles metric not found

### 3.4 Data Errors

- [ ] Handles no metric data available
- [ ] Handles invalid time range
- [ ] Handles invalid dimension values
- [ ] Handles invalid metric names

## 4. ELB Type-Specific Requirements

### 4.1 Dedicated ELB

- [ ] Correctly identifies Dedicated ELB instances
- [ ] Provides access to all Dedicated ELB metrics
- [ ] Supports 4 monitoring dimensions
- [ ] Supports HTTP/HTTPS/QUIC/GRPC protocol metrics
- [ ] Supports traffic mirroring metrics
- [ ] Supports backend server group metrics

### 4.2 Shared ELB

- [ ] Correctly identifies Shared ELB instances
- [ ] Provides access to basic metrics only
- [ ] Supports 2 monitoring dimensions (load balancer, listener)
- [ ] Gracefully handles requests for unavailable advanced metrics
- [ ] Provides clear message when HTTP metrics are not available

## 5. Output Format Requirements

### 5.1 Monitoring Report

- [ ] Report includes ELB instance name and ID
- [ ] Report includes ELB type (Dedicated/Shared)
- [ ] Report includes region
- [ ] Report includes time range
- [ ] Report includes key metrics summary
- [ ] Report includes detailed metrics table
- [ ] Report includes recommendations (if applicable)

### 5.2 Metric Data Presentation

- [ ] Shows metric values with timestamps
- [ ] Shows appropriate units for each metric
- [ ] Identifies trends and anomalies
- [ ] Provides threshold-based recommendations

## 6. Documentation Requirements

### 6.1 Skill Documentation

- [ ] SKILL.md is complete and accurate
- [ ] All references are valid and accessible
- [ ] Examples are correct and runnable
- [ ] Parameter descriptions are accurate

### 6.2 Reference Documentation

- [ ] related-commands.md covers all CLI commands used
- [ ] ces-metrics-reference.md lists all supported metrics
- [ ] iam-policies.md provides correct permission policies
- [ ] cli-installation-guide.md covers all platforms
- [ ] best-practices.md provides actionable guidance
- [ ] troubleshooting-guide.md covers common issues
- [ ] verification-method.md provides test procedures

## 7. Integration Requirements

### 7.1 CLI Integration

- [ ] Uses correct hcloud command format
- [ ] Uses camelCase naming for HCloud CLI methods
- [ ] Specifies region for all commands
- [ ] Handles JSON output correctly

### 7.2 CES Integration

- [ ] Uses correct namespace (SYS.ELB)
- [ ] Uses correct dimension names
- [ ] Uses correct metric names
- [ ] Handles CES API rate limits

## 8. Test Cases

### 8.1 Basic Test Cases

| ID | Test Case | Expected Result |
|----|-----------|-----------------|
| TC-01 | List ELB instances | Returns list of ELB instances |
| TC-02 | Query concurrent connections | Returns metric data |
| TC-03 | Query active connections | Returns metric data |
| TC-04 | Query inbound bandwidth | Returns metric data |
| TC-05 | Query with 1-hour time range | Returns data for last hour |
| TC-06 | Query with 24-hour time range | Returns data for last 24 hours |
| TC-07 | Query with average filter | Returns average values |
| TC-08 | Query with max filter | Returns maximum values |

### 8.2 Advanced Test Cases (Dedicated ELB)

| ID | Test Case | Expected Result |
|----|-----------|-----------------|
| TC-09 | Query HTTP 5xx errors | Returns HTTP error data |
| TC-10 | Query 2xx request ratio | Returns ratio percentage |
| TC-11 | Query listener-level metrics | Returns per-listener data |
| TC-12 | Query backend server group metrics | Returns per-pool data |
| TC-13 | Query traffic mirroring metrics | Returns mirror data |

### 8.3 Error Handling Test Cases

| ID | Test Case | Expected Result |
|----|-----------|-----------------|
| TC-14 | Query with invalid ELB ID | Returns appropriate error |
| TC-15 | Query with invalid time range | Returns appropriate error |
| TC-16 | Query HTTP metrics for Shared ELB | Returns clear message |
| TC-17 | Query with insufficient permissions | Returns permission error |
| TC-18 | Query with invalid metric name | Returns appropriate error |

## 9. Sign-Off Criteria

All the following must be satisfied for production release:

- [ ] All functional requirements met
- [ ] All non-functional requirements met
- [ ] All error handling requirements met
- [ ] All ELB type-specific requirements met
- [ ] All output format requirements met
- [ ] All documentation requirements met
- [ ] All integration requirements met
- [ ] All basic test cases passed
- [ ] All advanced test cases passed (Dedicated ELB)
- [ ] All error handling test cases passed
- [ ] Security review completed
- [ ] Performance benchmark met
- [ ] No critical or high-severity defects
