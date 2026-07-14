# Skill Test Best Practice Guide

> Summarizes industry best practices for Skill/Plugin testing, guiding the design and usage of huawei-cloud-skill-tester.

## Reference Frameworks

| Framework/Practice | Core Concept | Applicable Point |
|--------------------|--------------|------------------|
| OpenAI Plugin Review | Tiered review: structure check → security scan → functional verification → manual review | Tiered testing strategy |
| LangChain Evals | Declarative assertions + LLM-as-Judge + comparison baseline | Output quality evaluation |
| VS Code Extension Testing | Unit tests → integration tests → API compatibility → performance benchmarks | Multi-layer test pyramid |
| Terraform Provider Testing | Acceptance Tests (real resources) + Unit Tests (Mock) | Cloud resource operation verification |
| AWS CDK Assert | Orchestration logic assertions + compliance rule checks | IaC/configuration correctness |

## Core Principles

1. **Test Pyramid**: Unit tests (many) → Integration tests (moderate) → E2E tests (few)
2. **Idempotent First**: Cloud operation tests prefer read-only/idempotent operations
3. **Isolation**: Each test case independent, no dependency on other case results
4. **Repeatability**: Same input produces same output
5. **Hallucination Defense**: Apply structured assertions to Agent output
6. **Combination Compatibility**: Same-domain multi-Skill must undergo combination testing
7. **Incremental Regression**: Auto-run affected test subset after each change

## LLM Skill Specific Test Patterns

| Pattern | Method | Purpose |
|---------|--------|---------|
| With/Without comparison | Run same task with/without Skill | Quantify value delta |
| Trigger accuracy | Construct trigger word set for verification | Prevent false/missed triggers |
| Output structure assertion | Verify output contains required fields/format | Detect hallucination and format errors |
| Boundary injection | Input invalid/boundary parameters | Verify error handling and security |
| Multi-Skill competition | When task can be handled by multiple Skills | Verify priority and routing |
| Context isolation | Execute different Skill tasks sequentially | Verify context not polluted |

## Hallucination Issues and Defense

### Hallucination Types

- **Responsibility confusion**: Agent invokes wrong Skill
- **Parameter fabrication**: Agent fabricates non-existent parameter values
- **Workflow stitching error**: Multi-Skill collaboration skips steps or reverses order
- **Context pollution**: Prior Skill output residue affects subsequent judgment
- **Format hallucination**: Output structure does not match specification

### Defense Strategies

1. Description precision to reduce false matches
2. Output Schema validation to reject format anomalies
3. Service whitelist to prevent service name fabrication
4. Context window management to prevent residue pollution
5. Manual review of key nodes

## AIShell Optimization Directions

### Short-term (1-2 weeks)
- `npx skills test <name>` command
- `npx skills validate <name>` command
- Structured test result output (JSON)
- Test case configuration file support

### Mid-term (1-2 months)
- Multi-Skill combination test command
- Hallucination detection module
- With/Without comparison mode
- Trigger accuracy evaluation
- Test report visualization

### Long-term (3-6 months)
- CI/CD integration
- Regression test suite
- Performance benchmark library
- LLM-as-Judge evaluation
- Test coverage metrics
- Cross-version compatibility testing
