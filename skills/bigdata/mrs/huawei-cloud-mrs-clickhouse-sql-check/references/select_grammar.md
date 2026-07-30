# ClickHouse 24.8 SELECT 语句语法

Source: `ClickHouse_Kernel/src/Parsers/`

## 一、SELECT 语句完整语法模板

```sql
WITH [RECURSIVE] cte_name AS (subquery) | expr AS alias, ...
[FROM table_expr [FINAL] [SAMPLE ratio [OFFSET ratio]]
     [[GLOBAL|LOCAL] [ANY|ALL|ASOF|SEMI|ANTI]
      [INNER|LEFT|RIGHT|FULL|CROSS|PASTE]
      [ANY|ALL|ASOF|SEMI|ANTI] [OUTER] JOIN table_expr
      [USING (cols) | ON condition]]
     [[LEFT|INNER] ARRAY JOIN expr, ...]
     , ...]
]
SELECT [ALL | DISTINCT | DISTINCT ON (expr, ...)]
       [TOP N [WITH TIES]]
       expr [, ...]
[FROM table_expr ...]                           -- FROM 也可在此处
[PREWHERE expr]
[WHERE expr]
[GROUP BY [ROLLUP|CUBE|GROUPING_SETS] (expr, ...) | ALL | expr, ...]
[WITH [ROLLUP | CUBE | TOTALS]]
[HAVING expr]
[WINDOW window_def, ...]
[QUALIFY expr]
[ORDER BY expr [ASC|DESC] [COLLATE 'locale'], ... | ALL]
[INTERPOLATE (expr = default, ...)]
[LIMIT [offset,] length [WITH TIES]
  | LIMIT length BY expr, ...
  | OFFSET offset [ROW|ROWS]]
[FETCH {FIRST|NEXT} n {ROW|ROWS} {WITH TIES|ONLY}]
[SETTINGS key = value, ...]
[(UNION|EXCEPT|INTERSECT) [ALL|DISTINCT] select ...]
```

## 二、SELECT 子句顺序（严格）

| 顺序 | 子句 | 必填 | 说明 |
|------|------|------|------|
| 1 | WITH | 可选 | CTE / 表达式别名 |
| 2 | FROM | 可选 | 表来源（也可在 SELECT 之后） |
| 3 | SELECT | 必填 | 选择列 |
| 4 | FROM | 可选 | 表来源（也可在 SELECT 之前） |
| 5 | PREWHERE | 可选 | 预过滤 |
| 6 | WHERE | 可选 | 行过滤 |
| 7 | GROUP BY | 可选 | 分组 |
| 8 | WITH ROLLUP/CUBE/TOTALS | 可选 | 聚合修饰 |
| 9 | HAVING | 可选 | 聚合后过滤 |
| 10 | WINDOW | 可选 | 窗口函数定义 |
| 11 | QUALIFY | 可选 | 窗口函数结果过滤 |
| 12 | ORDER BY | 可选 | 排序 |
| 13 | INTERPOLATE | 可选 | WITH FILL 填充默认值 |
| 14 | LIMIT | 可选 | 限制行数 |
| 15 | OFFSET | 可选 | 跳过行数 |
| 16 | FETCH | 可选 | SQL 标准分页 |
| 17 | SETTINGS | 可选 | 查询级设置 |
| 18 | UNION/EXCEPT/INTERSECT | 可选 | 集合操作 |

## 三、SELECT 子句详细语法

### 3.1 WITH 子句

```sql
WITH [RECURSIVE]
  cte_name AS (subquery) | expr AS alias, ...
```

- `WITH RECURSIVE`: 支持递归 CTE
- 多个元素以逗号分隔

### 3.2 SELECT 修饰符

```sql
SELECT [ALL | DISTINCT | DISTINCT ON (expr, ...)]
       [TOP N [WITH TIES]]
       expr [, ...]
```

| 修饰符 | 说明 |
|--------|------|
| `ALL` | 保留所有行（默认） |
| `DISTINCT` | 去重 |
| `DISTINCT ON (expr, ...)` | 按表达式去重（等价于 LIMIT 1 BY） |
| `TOP N` | 取前 N 行（等价于 LIMIT N） |
| `WITH TIES` | 保留并列行 |

### 3.3 FROM 子句中的 TableExpression

```sql
(table_name | table_function(...) | (subquery)) [alias]
  [FINAL]
  [SAMPLE ratio [OFFSET ratio]]
```

- **表来源三选一**:
  1. `database.table` 或 `table`
  2. `table_function(...)`
  3. `(subquery)`
- `FINAL`: MergeTree 引擎读取最新版本数据
- `SAMPLE ratio [OFFSET ratio]`: 采样查询

### 3.4 SAMPLE Ratio 格式

```sql
12345              -- 整数
0.12345            -- 小数
.12345             -- 无前导零小数
0.                 -- 尾随小数点
1.23e-1            -- 科学计数法
123 / 456          -- 分数
```

- 解析为有理数（Rational），不转 IEEE-754 浮点数

### 3.5 PREWHERE 子句

```sql
PREWHERE expr
```

- ClickHouse 特有
- 用于 MergeTree 引擎优化扫描
- 在 WHERE 之前执行

### 3.6 WHERE 子句

```sql
WHERE expr
```

- 行过滤条件

### 3.7 GROUP BY 子句

```sql
GROUP BY [ROLLUP | CUBE | GROUPING SETS] (expr, ...) | ALL | expr, ...
```

| 修饰符 | 说明 |
|--------|------|
| `ROLLUP` | 层级汇总 |
| `CUBE` | 全组合汇总 |
| `GROUPING SETS` | 指定分组集合 |
| `ALL` | 自动选择所有分组列 |

### 3.8 HAVING 子句

```sql
HAVING expr
```

- 聚合后过滤

### 3.9 WINDOW 子句

```sql
WINDOW window_name AS (
  [PARTITION BY expr, ...]
  [ORDER BY expr [ASC|DESC] [NULLS FIRST|LAST], ...]
  [frame_clause]
)
```

- 定义命名窗口
- frame_clause: `ROWS/RANGE/GROUPS BETWEEN ... AND ...`

### 3.10 QUALIFY 子句

```sql
QUALIFY expr
```

- 窗口函数结果过滤

### 3.11 ORDER BY 子句

```sql
ORDER BY expr [ASC|DESC] [NULLS FIRST|LAST] [COLLATE 'locale']
  [WITH FILL [FROM value] [TO value] [STEP value]], ...
| ALL
```

- `ALL`: 自动选择所有排序列
- `WITH FILL`: 填充缺失值（时序数据）

### 3.12 INTERPOLATE 子句

```sql
INTERPOLATE (expr = default, ...)
```

- 配合 WITH FILL 使用
- 指定填充默认值

### 3.13 LIMIT 子句

```sql
LIMIT [offset,] length [WITH TIES]
| LIMIT length BY expr, ...
| OFFSET offset [ROW|ROWS]
```

- `LIMIT offset, length`: 跳过 offset 行，取 length 行
- `LIMIT length BY expr, ...`: 按表达式分组取前 N
- `OFFSET offset`: 跳过 offset 行
- `WITH TIES`: 保留并列行

### 3.14 FETCH 子句

```sql
FETCH {FIRST|NEXT} n {ROW|ROWS} {WITH TIES|ONLY}
```

- SQL 标准分页语法

### 3.15 SETTINGS 子句

```sql
SETTINGS key = value, ...
```

- 查询级设置

## 四、JOIN 语法

### 4.1 JOIN 方向（JoinKind）

| 枚举值 | 关键字 | 说明 |
|--------|--------|------|
| `Inner` | `INNER` | 内连接（默认） |
| `Left` | `LEFT` | 左连接 |
| `Right` | `RIGHT` | 右连接 |
| `Full` | `FULL` | 全连接 |
| `Cross` | `CROSS` | 交叉连接 |
| `Paste` | `PASTE` | 粘贴连接 |

### 4.2 JOIN 严格性（JoinStrict）

| 枚举值 | 关键字 | 说明 |
|--------|--------|------|
| `Unspecified` | (默认) | 未指定 |
| `All` | `ALL` | 保留所有匹配行 |
| `Any` | `ANY` | 只保留第一个匹配行 |
| `Asof` | `ASOF` | 对最后一列取最近值（时序数据） |
| `Semi` | `SEMI` | 仅过滤，必须配合 LEFT/RIGHT |
| `Anti` | `ANTI` 或 `ONLY` | 反向过滤，必须配合 LEFT/RIGHT |

### 4.3 JOIN 位置（JoinLocality）

| 枚举值 | 关键字 | 说明 |
|--------|--------|------|
| `Unspecified` | (默认) | 本地连接 |
| `Local` | `LOCAL` | 仅使用本机数据 |
| `Global` | `GLOBAL` | 收集远程数据并广播 |

### 4.4 JOIN 完整语法结构

```sql
[GLOBAL | LOCAL]
  [ANY | ALL | ASOF | SEMI | ANTI]          -- Legacy: 严格性在方向前
  [INNER | LEFT | RIGHT | FULL | CROSS | PASTE]
  [ANY | ALL | ASOF | SEMI | ANTI]          -- Standard: 严格性在方向后
  [OUTER]                                    -- LEFT/RIGHT/FULL 后可加 OUTER
  JOIN
  table_expression
  [USING (col, ...) | USING col, ...]
  | [ON condition]
```

**约束规则**:
- CROSS JOIN 和 PASTE JOIN 不能指定 ANY/ALL
- SEMI/ANTI JOIN 必须是 LEFT 或 RIGHT
- 默认: 无方向指定时，SEMI/ANTI 默认 LEFT，其他默认 INNER

### 4.5 ARRAY JOIN

```sql
[LEFT | INNER] ARRAY JOIN expr, ...
```

- `LEFT ARRAY JOIN`: 左数组连接
- `INNER ARRAY JOIN`: 内数组连接（默认，INNER 可省略）

## 五、UNION / EXCEPT / INTERSECT

```sql
select_element
  { (UNION | EXCEPT | INTERSECT) [ALL | DISTINCT] select_element }
```

| 操作符 | 模式 | 枚举值 |
|--------|------|--------|
| UNION | (默认) | `UNION_DEFAULT` |
| UNION | ALL | `UNION_ALL` |
| UNION | DISTINCT | `UNION_DISTINCT` |
| EXCEPT | (默认) | `EXCEPT_DEFAULT` |
| EXCEPT | ALL | `EXCEPT_ALL` |
| EXCEPT | DISTINCT | `EXCEPT_DISTINCT` |
| INTERSECT | (默认) | `INTERSECT_DEFAULT` |
| INTERSECT | ALL | `INTERSECT_ALL` |
| INTERSECT | DISTINCT | `INTERSECT_DISTINCT` |

## 六、ClickHouse 特有语法点汇总

| 语法点 | 位置 | 说明 |
|--------|------|------|
| **SAMPLE BY / SAMPLE** | FROM 子句 | 采样查询 |
| **FINAL** | FROM 子句 | MergeTree 最新版本数据 |
| **ARRAY JOIN** | FROM 子句 | 数组展开连接 |
| **LEFT ARRAY JOIN** | FROM 子句 | 左数组连接 |
| **INNER ARRAY JOIN** | FROM 子句 | 内数组连接（默认） |
| **PREWHERE** | SELECT 之后 | 预过滤优化 |
| **GLOBAL JOIN** | JOIN 关键字前 | 分布式全局连接 |
| **LOCAL JOIN** | JOIN 关键字前 | 本地连接 |
| **ANY/ALL/ASOF/SEMI/ANTI JOIN** | JOIN 方向前后 | 连接严格性 |
| **PASTE JOIN** | JOIN 方向 | 粘贴连接 |
| **ASOF JOIN** | JOIN 严格性 | 时序数据最近值连接 |
| **WINDOW** | HAVING 之后 | 窗口函数定义 |
| **QUALIFY** | WINDOW 之后 | 窗口函数结果过滤 |
| **WITH FILL** | ORDER BY 元素 | 填充缺失值 |
| **INTERPOLATE** | ORDER BY 之后 | WITH FILL 填充默认值 |
| **WITH TIES** | LIMIT / TOP / FETCH 后 | 保留并列行 |
| **TOP N** | SELECT 之后 | 等价于 LIMIT N |
| **LIMIT ... BY** | LIMIT 子句 | 按表达式分组取前 N |
| **WITH TOTALS** | GROUP BY 之后 | 添加汇总行 |
| **WITH ROLLUP** | GROUP BY 之后 | 层级汇总 |
| **WITH CUBE** | GROUP BY 之后 | 全组合汇总 |
| **GROUP BY ROLLUP/CUBE/GROUPING SETS** | GROUP BY 内部 | 聚合修饰 |
| **GROUP BY ALL** | GROUP BY | 自动选择所有分组列 |
| **ORDER BY ALL** | ORDER BY | 自动选择所有排序列 |
| **WITH RECURSIVE** | WITH 子句 | 递归 CTE |
| **DISTINCT ON** | SELECT 修饰 | 等价于 LIMIT 1 BY |
| **FETCH FIRST/NEXT** | ORDER BY 之后 | SQL 标准分页 |
| **SETTINGS** | 语句末尾 | 查询级设置 |
| **EXCEPT / INTERSECT** | UNION 同级 | 集合操作符 |
| **FROM 在 SELECT 前** | 子句顺序 | ClickHouse 允许 FROM 先于 SELECT |

## 七、文件索引

| 文件 | 路径 |
|------|------|
| ParserSelectQuery.cpp | `src/Parsers/ParserSelectQuery.cpp` |
| ParserSelectQuery.h | `src/Parsers/ParserSelectQuery.h` |
| ParserSelectWithUnionQuery.cpp | `src/Parsers/ParserSelectWithUnionQuery.cpp` |
| ParserTablesInSelectQuery.cpp | `src/Parsers/ParserTablesInSelectQuery.cpp` |
| ParserWithElement.cpp | `src/Parsers/ParserWithElement.cpp` |
| ParserSampleRatio.cpp | `src/Parsers/ParserSampleRatio.cpp` |
| ParserProjectionSelectQuery.cpp | `src/Parsers/ParserProjectionSelectQuery.cpp` |
| ASTSelectQuery.h | `src/Parsers/ASTSelectQuery.h` |
| Core/Joins.h | `src/Core/Joins.h` |
| ExpressionListParsers.cpp | `src/Parsers/ExpressionListParsers.cpp` |
