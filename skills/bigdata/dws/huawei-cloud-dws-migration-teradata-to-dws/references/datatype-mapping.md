# Teradata 到 DWS 数据类型映射参考

> 参考文档: https://support.huaweicloud.com/migration-dws/dws_15_0131.html

## 1. 数值类型映射

| Teradata 类型 | DWS 类型 | 说明 |
|---|---|---|
| BIGINT | BIGINT | 8字节整数 |
| BYTEINT | SMALLINT | 1字节整数 → 2字节整数 |
| DECIMAL[(n[,m])] | DECIMAL[(n[,m])] | 十进制数，精度和标度保持不变 |
| DOUBLE PRECISION | DOUBLE PRECISION | 双精度浮点数 |
| FLOAT | DOUBLE PRECISION | 浮点数 → 双精度 |
| INT / INTEGER | INTEGER | 4字节整数 |
| NUMBER / NUMERIC | NUMERIC | 任意精度数值 |
| NUMBER(n[,m]) | NUMERIC(n[,m]) | 指定精度的数值 |
| REAL | REAL | 单精度浮点数 |
| SMALLINT | SMALLINT | 2字节整数 |

## 2. 字符类型映射

| Teradata 类型 | DWS 类型 | 说明 |
|---|---|---|
| CHAR[(n)] / CHARACTER[(n)] | CHAR(n) | 定长字符 |
| CLOB | CLOB | 大字符对象 |
| LONG VARCHAR | TEXT | 变长字符串 → 文本类型 |
| VARCHAR(n) | VARCHAR(n) | 变长字符 |
| CHAR VARYING(n) | VARCHAR(n) | 变长字符 |
| CHARACTER VARYING(n) | VARCHAR(n) | 变长字符 |

## 3. 时间日期类型映射

| Teradata 类型 | DWS 类型 | 说明 |
|---|---|---|
| DATE | DATE | 日期 |
| TIME[(n)] | TIME[(n)] | 时间，可带精度 |
| TIME[(n)] WITH TIME ZONE | TIME[(n)] WITH TIME ZONE | 带时区的时间 |
| TIMESTAMP[(n)] | TIMESTAMP[(n)] | 时间戳，可带精度 |
| TIMESTAMP[(n)] WITH TIME ZONE | TIMESTAMP[(n)] WITH TIME ZONE | 带时区的时间戳 |

## 4. Period 类型映射

| Teradata 类型 | DWS 类型 | 说明 |
|---|---|---|
| PERIOD(DATE) | daterange | 日期范围 |
| PERIOD(TIME[(n)]) | tsrange[(n)] | 时间范围 |
| PERIOD(TIME WITH TIME ZONE) | tstzrange | 带时区的时间范围 |
| PERIOD(TIMESTAMP[(n)]) | tsrange[(n)] | 时间戳范围 |
| PERIOD(TIMESTAMP WITH TIME ZONE) | tstzrange | 带时区的时间戳范围 |

## 5. 二进制类型映射

| Teradata 类型 | DWS 类型 | 说明 |
|---|---|---|
| BLOB[(n)] | blob | 二进制大对象 |
| BYTE[(n)] | bytea | 定长二进制 → 变长二进制 |
| VARBYTE[(n)] | bytea | 变长二进制 |

## 6. Teradata ColumnType 代码映射

DWS 元数据表 DBC.ColumnsV 中的 ColumnType 代码与类型名称的对应关系：

| 代码 | 类型名称 | 说明 |
|---|---|---|
| I | INTEGER | 4字节整数 |
| I1 | BYTEINT | 1字节整数 |
| I2 | SMALLINT | 2字节整数 |
| I8 | BIGINT | 8字节整数 |
| D | DECIMAL | 十进制数 |
| N | NUMBER | 任意精度数值 |
| F | FLOAT | 浮点数 |
| CV | VARCHAR | 变长字符 |
| CF | CHAR | 定长字符 |
| CLO | CLOB | 大字符对象 |
| DA | DATE | 日期 |
| TI | TIME | 时间 |
| TS | TIMESTAMP | 时间戳 |
| BF | BYTE | 定长二进制 |
| BV | VARBYTE | 变长二进制 |
| BO | BLOB | 二进制大对象 |

## 7. 注意事项

1. **FLOAT → DOUBLE PRECISION**: Teradata 的 FLOAT 默认为双精度，映射到 DWS 的 DOUBLE PRECISION
2. **LONG VARCHAR → TEXT**: DWS 不支持 LONG VARCHAR，使用 TEXT 替代
3. **BYTE/VARBYTE → bytea**: Teradata 二进制类型映射到 PostgreSQL 的 bytea
4. **PERIOD 类型**: DWS 使用范围类型（range types）替代 Teradata 的 PERIOD 类型
5. **NUMBER → NUMERIC**: Teradata 的 NUMBER 类型映射到 DWS 的 NUMERIC
6. **Teradata 兼容模式**: DWS 在 Teradata 兼容模式下，外表不支持 DATE 类型，需注意
