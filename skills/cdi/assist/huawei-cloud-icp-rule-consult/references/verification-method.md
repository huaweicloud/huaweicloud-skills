# Verification Method

## Overview

This document defines the success verification criteria for each phase of the ICP Filing consultation skill, ensuring correct installation, configuration, and operation.

## 1. Python Environment Verification

| Check | Method | Expected Result |
| --- | --- | --- |
| Python version | `python --version` | Output Python 3.9.x or higher |
| requests installed | `python -c "import requests; print('OK')"` | Output `OK` |
| beautifulsoup4 installed | `python -c "from bs4 import BeautifulSoup; print('OK')"` | Output `OK` |

## 2. web_fetcher Verification

```bash
python {skill_dir}/scripts/web_fetcher.py fetch https://support.huaweicloud.com/icp/index.html --mode text
```

| Check | Expected Result |
| --- | --- |
| Exit code | 0 |
| JSON success field | `true` |
| text field non-empty | Contains page text content |

## 3. web_searcher Verification (Optional)

> Requires Playwright + Chromium installed.

```bash
python {skill_dir}/scripts/web_searcher.py search "ICP备案"
```

| Check | Expected Result |
| --- | --- |
| Exit code | 0 |
| JSON success field | `true` |
| results list non-empty | At least 1 search result, each with rank/title/url |

## 4. Knowledge Base Integrity Verification

| Check | Method | Expected Result |
| --- | --- | --- |
| knowledge-base.md exists | `ls references/knowledge-base.md` | File exists and is non-empty |
| catalog.yml parseable | `python -c "import yaml; yaml.safe_load(open('references/catalog.yml'))"` | No error |
| filing-rules.yml parseable | `python -c "import yaml; yaml.safe_load(open('references/filing-rules.yml'))"` | No error |

## 5. Workflow Phase Verification

| Phase | Success Criteria | Failure Indicator |
| --- | --- | --- |
| Lock Intent | Triggers matched to entry_point, ontology_entities obtained | Returns boundary entry_point (NonFilingQuestion/VagueQuestion) |
| Gather Evidence | Embedded knowledge hit OR web_fetch returns success:true OR web_search returns non-empty results | All sources return no matching content |
| Deliver Response | Response contains: direct conclusion + supplementary details + related document links | Missing conclusion or no document links |

## 6. Constraint Verification

| Constraint | Verification Method | Expected Result |
| --- | --- | --- |
| web_search at most 1 call | Count web_searcher invocations in a single session | ≤ 1 |
| web_fetch ≤ 2 per category | Count web_fetcher invocations per category in a single session | ≤ 2 |
| web_search + web_fetch combined ≤ 3 | Count all tool invocations in a single session | ≤ 3 |
| No tool call when embedded knowledge suffices | Check tool call records after embedded knowledge hit | No tool calls |
