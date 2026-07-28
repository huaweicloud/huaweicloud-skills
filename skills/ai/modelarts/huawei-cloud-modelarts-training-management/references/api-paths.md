# API Paths (from SDK Source)

> REST API paths for all 52 ModelArts training management operations, extracted from the Huawei Cloud SDK source code.

---

## 1. Training Job Management (14 APIs)

| # | CLI Operation | HTTP Method | API Path |
|---|---------------|-------------|----------|
| 1 | CreateTrainingJob | POST | `/v2/{project_id}/training-jobs` |
| 2 | ListTrainingJobs | GET | `/v2/{project_id}/training-jobs` |
| 3 | ShowTrainingJobDetails | GET | `/v2/{project_id}/training-jobs/{training_job_id}` |
| 4 | StopTrainingJob | POST | `/v2/{project_id}/training-jobs/{training_job_id}/stop` |
| 5 | DeleteTrainingJob | DELETE | `/v2/{project_id}/training-jobs/{training_job_id}` |
| 6 | ChangeTrainingJobDescription | PUT | `/v2/{project_id}/training-jobs/{training_job_id}` |
| 7 | ShowTrainingJobLogsPreview | GET | `/v2/{project_id}/training-jobs/{training_job_id}/logs/preview` |
| 8 | ShowObsUrlOfTrainingJobLogs | GET | `/v2/{project_id}/training-jobs/{training_job_id}/logs/obs-url` |
| 9 | ShowTrainingJobMetrics | GET | `/v2/{project_id}/training-jobs/{training_job_id}/metrics` |
| 10 | ShowTrainingJobEngines | GET | `/v2/{project_id}/training-jobs/engines` |
| 11 | ShowTrainingJobFlavors | GET | `/v2/{project_id}/training-jobs/flavors` |
| 12 | ShowTrainingQuotas | GET | `/v2/{project_id}/training-jobs/quotas` |
| 13 | NotifyTrainingJobInformation | POST | `/v2/{project_id}/training-jobs/{training_job_id}/information` |
| 14 | ListJobs | GET | `/v1/{project_id}/jobs` |

## 2. Algorithm Management (7 APIs)

| # | CLI Operation | HTTP Method | API Path |
|---|---------------|-------------|----------|
| 15 | CreateAlgorithm | POST | `/v2/{project_id}/algorithms` |
| 16 | ListAlgorithms | GET | `/v2/{project_id}/algorithms` |
| 17 | ShowAlgorithmByUuid | GET | `/v2/{project_id}/algorithms/{algorithm_id}` |
| 18 | ChangeAlgorithm | PUT | `/v2/{project_id}/algorithms/{algorithm_id}` |
| 19 | DeleteAlgorithm | DELETE | `/v2/{project_id}/algorithms/{algorithm_id}` |
| 20 | ShowSearchAlgorithms | GET | `/v2/{project_id}/algorithms/search` |
| 21 | CreateAlgorithmVersionToGallery | POST | `/v2/{project_id}/algorithms/{algorithm_id}/version-to-gallery` |

## 3. Training Job Tags (3 APIs)

| # | CLI Operation | HTTP Method | API Path |
|---|---------------|-------------|----------|
| 22 | CreateTrainJobTags | POST | `/v2/{project_id}/training-jobs/{training_job_id}/tags` |
| 23 | ShowTrainJobTags | GET | `/v2/{project_id}/training-jobs/{training_job_id}/tags` |
| 24 | DeleteTrainJobTags | DELETE | `/v2/{project_id}/training-jobs/{training_job_id}/tags` |

## 4. Training Experiments (6 APIs)

| # | CLI Operation | HTTP Method | API Path |
|---|---------------|-------------|----------|
| 25 | CreateTrainingExperiment | POST | `/v2/{project_id}/training-experiments` |
| 26 | ListTrainingExperiments | GET | `/v2/{project_id}/training-experiments` |
| 27 | ShowTrainingExperimentDetails | GET | `/v2/{project_id}/training-experiments/{experiment_id}` |
| 28 | DeleteTrainingExperiment | DELETE | `/v2/{project_id}/training-experiments/{experiment_id}` |
| 29 | ChangeTrainingExperiment | PUT | `/v2/{project_id}/training-experiments/{experiment_id}` |
| 30 | CheckTrainingExperiment | GET | `/v2/{project_id}/training-experiments/check` |

## 5. Training Job Events (7 APIs)

| # | CLI Operation | HTTP Method | API Path |
|---|---------------|-------------|----------|
| 31 | ListTrainingJobEvents | GET | `/v2/{project_id}/training-jobs/{training_job_id}/events` |
| 32 | ListTrainingJobStages | GET | `/v2/{project_id}/training-jobs/{training_job_id}/stages` |
| 33 | ListTrainingJobTasks | GET | `/v2/{project_id}/training-jobs/{training_job_id}/tasks` |
| 34 | ListEvents | GET | `/v2/{project_id}/events` |
| 35 | ListEventCategories | GET | `/v2/{project_id}/events/categories` |
| 36 | ListScheduledEvents | GET | `/v2/{project_id}/scheduled-events` |
| 37 | AcceptScheduledEvent | POST | `/v2/{project_id}/scheduled-events/{event_id}/accept` |

## 6. Model Import (6 APIs)

| # | CLI Operation | HTTP Method | API Path |
|---|---------------|-------------|----------|
| 38 | CreateModel | POST | `/v1/{project_id}/models` |
| 39 | ListModels | GET | `/v1/{project_id}/models` |
| 40 | ShowModel | GET | `/v1/{project_id}/models/{model_id}` |
| 41 | DeleteModel | DELETE | `/v1/{project_id}/models/{model_id}` |
| 42 | ShowModelEngineAndRuntime | GET | `/v1/{project_id}/models/engines` |
| 43 | CreateModelArtsAgency | POST | `/v2/{project_id}/agency` |

## 7. Auto Search (7 APIs)

| # | CLI Operation | HTTP Method | API Path |
|---|---------------|-------------|----------|
| 44 | ShowAutoSearchTrials | GET | `/v2/{project_id}/training-jobs/{training_job_id}/auto-search/trials` |
| 45 | ShowAutoSearchPerTrial | GET | `/v2/{project_id}/training-jobs/{training_job_id}/auto-search/trials/{trial_id}` |
| 46 | ShowAutoSearchParamsAnalysis | GET | `/v2/{project_id}/training-jobs/{training_job_id}/auto-search/params-analysis` |
| 47 | ShowAutoSearchParamAnalysisResultPath | GET | `/v2/{project_id}/training-jobs/{training_job_id}/auto-search/params-analysis/result-path` |
| 48 | ShowAutoSearchTrialEarlyStop | POST | `/v2/{project_id}/training-jobs/{training_job_id}/auto-search/trials/{trial_id}/early-stop` |
| 49 | ShowAutoSearchYamlTemplateContent | GET | `/v2/{project_id}/auto-search/yaml-templates/{template_name}` |
| 50 | ShowAutoSearchYamlTemplatesInfo | GET | `/v2/{project_id}/auto-search/yaml-templates` |

## 8. Training Image Save (2 APIs)

| # | CLI Operation | HTTP Method | API Path |
|---|---------------|-------------|----------|
| 51 | CreateSaveImageJob | POST | `/v2/{project_id}/training-jobs/{training_job_id}/save-image` |
| 52 | ShowSaveImageJob | GET | `/v2/{project_id}/training-jobs/{training_job_id}/save-image/{job_id}` |

---

## Notes

- API paths use `{project_id}` as a path parameter — the CLI auto-resolves this from credentials
- v1 APIs (ListJobs, CreateModel, ListModels, ShowModel, DeleteModel, ShowModelEngineAndRuntime) use the older ModelArts v1 API
- v2 APIs use the newer ModelArts v2 API
- All paths are relative to the ModelArts service endpoint
