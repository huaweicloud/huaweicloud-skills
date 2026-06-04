# Performance Analysis SQL QueryReference

## CommonQuery

### 1. OperatorTime consumption TOP N

```sql
-- TOP 20 Time consumptionOperator
SELECT 
    op_name,
    op_type,
    total_time / 1000 as total_time_ms,
    total_time * 100.0 / (SELECT SUM(total_time) FROM op_summary) as percent,
    call_times
FROM op_summary
ORDER BY total_time DESC
LIMIT 20;
```

### 2. according toOperatortypetypestatisticscalculate

```sql
-- Group by Typestatisticscalculate
SELECT 
    op_type,
    SUM(total_time) / 1000 as total_time_ms,
    SUM(total_time) * 100.0 / (SELECT SUM(total_time) FROM op_summary) as percent,
    COUNT(*) as op_count
FROM op_summary
GROUP BY op_type
ORDER BY SUM(total_time) DESC;
```

### 3. AI_CPU Operator (potentialinBottleneck) 

```sql
-- AI_CPU Operatorcolumntable
SELECT 
    op_name,
    total_time / 1000 as total_time_ms,
    call_times
FROM op_summary
WHERE op_type = 'AI_CPU'
ORDER BY total_time DESC;
```

### 4. adjustusetimenumbermostmultipleofOperator

```sql
-- highfrequencyadjustuseOperator
SELECT 
    op_name,
    op_type,
    call_times,
    total_time / call_times / 1000 as avg_time_us
FROM op_summary
ORDER BY call_times DESC
LIMIT 20;
```

### 5. SingleTime consumptionmostlengthofOperator

```sql
-- SingleTime consumption TOP
SELECT 
    op_name,
    op_type,
    total_time / call_times / 1000 as avg_time_us,
    call_times
FROM op_summary
WHERE call_times > 0
ORDER BY total_time / call_times DESC
LIMIT 20;
```

### 6. Conv2D Operatordetailedsituation

```sql
-- Conv2D Performance Analysis
SELECT 
    op_name,
    total_time / 1000 as total_time_ms,
    call_times,
    total_time / call_times / 1000 as avg_time_us
FROM op_summary
WHERE op_name LIKE '%Conv%' OR op_name LIKE '%conv%'
ORDER BY total_time DESC;
```

### 7. MatMul/GEMM Operator

```sql
-- rulematrixmultiplyOperator
SELECT 
    op_name,
    op_type,
    total_time / 1000 as total_time_ms,
    call_times
FROM op_summary
WHERE op_name LIKE '%MatMul%' OR op_name LIKE '%GEMM%' OR op_name LIKE '%matmul%'
ORDER BY total_time DESC;
```

### 8. DatatransferoutputOperator

```sql
-- TransData/formatformulaconvertexchangeOperator
SELECT 
    op_name,
    op_type,
    total_time / 1000 as total_time_ms,
    call_times
FROM op_summary
WHERE op_name LIKE '%TransData%' OR op_name LIKE '%trans%' OR op_name LIKE '%Cast%'
ORDER BY total_time DESC;
```

---

## AnalysisReportGenerateQuery

### completeadjustPerformancegeneralview

```sql
-- Performancegeneralview
SELECT 
    'totalOperatornumber' as metric,
    COUNT(*) as value
FROM op_summary
UNION ALL
SELECT 
    'Total time(ms)' as metric,
    SUM(total_time) / 1000 as value
FROM op_summary
UNION ALL
SELECT 
    'AI_CPUOperatornumber' as metric,
    COUNT(*) as value
FROM op_summary WHERE op_type = 'AI_CPU'
UNION ALL
SELECT 
    'AI_COREOperatornumber' as metric,
    COUNT(*) as value
FROM op_summary WHERE op_type = 'AI_CORE'
UNION ALL
SELECT 
    'AI_CPUTime consumptionoccupycompare(%)' as metric,
    SUM(total_time) * 100.0 / (SELECT SUM(total_time) FROM op_summary) as value
FROM op_summary WHERE op_type = 'AI_CPU';
```

### BottleneckOperatorrecognizecategory

```sql
-- occupycompare > 5% ofOperator
SELECT 
    op_name,
    op_type,
    total_time / 1000 as total_time_ms,
    ROUND(total_time * 100.0 / (SELECT SUM(total_time) FROM op_summary), 2) as percent,
    CASE 
        WHEN op_type = 'AI_CPU' THEN 'needOptimization: AI_CPUImplementation'
        WHEN op_name LIKE '%TransData%' THEN 'needOptimization: formatformulaconvertexchangeopenconsume'
        WHEN op_name LIKE '%nms%' OR op_name LIKE '%NMS%' THEN 'needOptimization: NMSFallbackCPU'
        ELSE 'waitAnalysis'
    END as suggestion
FROM op_summary
WHERE total_time * 100.0 / (SELECT SUM(total_time) FROM op_summary) > 5
ORDER BY total_time DESC;
```

---

## tableStructureReference

### op_summary table

| characterparagraph | Description |
|------|------|
| op_name | OperatorName |
| op_type | Operatortypetype (AI_CPU/AI_CORE/AI_VECTOR_CORE)  |
| total_time | Total time (us)  |
| call_times | adjustusetimenumber |
| task_id | Task ID |
| model_id | Model ID |

### otherotherCommontable

- `task_summary` - Tasklevelstatisticscalculate
- `model_summary` - Modellevelstatisticscalculate
- `step_summary` - step levelstatisticscalculate
