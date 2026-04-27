# 数据库设计

数据库文件：`data/enchantment.db`（SQLite）

## 表结构

### rule_groups - 规则组

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增主键 |
| name | TEXT | 规则组名称 |
| trait_name | TEXT | 关联的组合特性名称（NULL=无特性） |
| trait_level | INTEGER | 特性最低等级（默认4） |
| created_at | TEXT | 创建时间 |

### group_rules - 组内属性规则

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增主键 |
| group_id | INTEGER FK | 所属规则组（级联删除） |
| attribute_name | TEXT | 属性名称（如"力量"） |
| threshold | REAL | 阈值（属性值 >= 此值才满足） |
| created_at | TEXT | 创建时间 |

### config_schemes - 配置方案

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增主键 |
| name | TEXT UNIQUE | 方案名称 |
| data | TEXT | 方案数据（JSON 快照） |
| created_at | TEXT | 创建时间 |

**data 字段格式：**
```json
{
  "groups": [
    {
      "name": "斗志组",
      "trait_name": "斗志",
      "trait_level": 4,
      "rules": [
        {"attribute_name": "力量", "threshold": 8}
      ]
    }
  ]
}
```

### analysis_history - 分析历史

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增主键 |
| filename | TEXT | 截图文件名 |
| attributes | TEXT | 识别到的属性列表（JSON） |
| trait | TEXT | 组合特性（JSON，可为空） |
| status | INTEGER | 判定结果：1=保留, 0=不保留 |
| reason | TEXT | 判定原因文字 |
| matched_rules | TEXT | 匹配详情（JSON） |
| config_snapshot | TEXT | 分析时的配置快照（JSON） |
| scheme_name | TEXT | 使用的方案名称 |
| created_at | TEXT | 创建时间 |

### settings - 系统设置

| 字段 | 类型 | 说明 |
|------|------|------|
| key | TEXT PK | 设置键名 |
| value | TEXT | 设置值 |

当前使用的设置键：
- `image_dir` - 自定义截图路径（空字符串使用默认路径）

### trait_rules - 组合特性规则（旧版遗留）

此表为旧版遗留，当前版本中组合特性已统一到规则组内管理。

## 数据关系

```
config_schemes (1) ──保存/加载──→ rule_groups (N)
                                       │
                                       ├── group_rules (N)
                                       │
analysis_history ←──记录── 分析结果
```

方案操作流程：
1. **保存方案**：将当前 `rule_groups` + `group_rules` 序列化为 JSON 存入 `config_schemes.data`
2. **加载方案**：清空 `rule_groups` 和 `group_rules`，从 `config_schemes.data` 反序列化写入
3. **分析记录**：每次分析时快照当前配置写入 `analysis_history.config_snapshot`

## 数据库配置

- **WAL 模式**：启用 Write-Ahead Logging，提升并发读写性能
- **外键约束**：启用，`group_rules.group_id` 级联删除
- **连接超时**：10 秒
