# API 接口文档

所有接口基础路径: `http://localhost:60016`

## 页面路由

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | 首页（返回 index.html） |
| GET | `/api/images/{filename}` | 获取截图图片 |

---

## 属性定义

### GET /api/attributes/definitions

获取所有属性定义（含取值范围和预设值）。

**响应示例：**
```json
{
  "力量": {"min": 4, "max": 10, "type": "integer", "presets": [5, 6, 8, 9]},
  "MaxHp%": {"min": 2, "max": 10, "type": "percent", "presets": [3.0, 5.0, 7.0, 9.0]},
  "沉默抵抗": {"min": 1, "max": 25, "type": "resistance", "presets": [5.0, 10.0, 15.0, 20.0]}
}
```

### GET /api/traits/definitions

获取所有组合特性定义。

**响应示例：**
```json
[
  {"name": "斗志", "desc": "忽视物理防御", "attrs": ["力量", "物理攻击"], "effect_base": 5, "effect_unit": "%", "max_level": 4},
  {"name": "尖锐", "desc": "暴击伤害提升", "attrs": ["敏捷", "幸运"], "effect_base": 5, "effect_unit": "%", "max_level": 4}
]
```

---

## 规则组管理

### GET /api/rules/groups

获取所有规则组（含组内规则和组合特性）。

**响应示例：**
```json
{
  "groups": [
    {
      "id": 1,
      "name": "斗志组",
      "trait_name": "斗志",
      "trait_level": 4,
      "rules": [
        {"id": 1, "group_id": 1, "attribute_name": "力量", "threshold": 8}
      ]
    }
  ]
}
```

### POST /api/rules/groups

创建新规则组。

**请求体：**
```json
{"name": "新规则组", "trait_name": null, "trait_level": 4}
```

### PUT /api/rules/groups/{group_id}

更新规则组名称。

**请求体：**
```json
{"name": "新名称"}
```

### PUT /api/rules/groups/{group_id}/trait

更新规则组的组合特性。

**请求体：**
```json
{"trait_name": "斗志", "trait_level": 4}
```

设置 `trait_name` 为 `null` 或空字符串取消关联。

### DELETE /api/rules/groups/{group_id}

删除规则组（级联删除组内所有规则）。

---

## 组内规则管理

### POST /api/rules/groups/{group_id}/rules

向规则组内添加属性规则。

**请求体：**
```json
{"attribute_name": "力量", "threshold": 8}
```

### PUT /api/rules/groups/{group_id}/rules/{rule_id}

更新规则阈值。

**请求体：**
```json
{"threshold": 9}
```

### DELETE /api/rules/groups/{group_id}/rules/{rule_id}

删除组内规则。

---

## 配置方案

### GET /api/schemes

获取所有已保存的方案列表。

### GET /api/schemes/{scheme_id}

获取方案详情（含完整规则数据）。

### POST /api/schemes

将当前配置保存为新方案。

**请求体：**
```json
{"name": "武器流"}
```

### POST /api/schemes/blank

清空当前配置并保存为空白方案。

**请求体：**
```json
{"name": "空白方案"}
```

### POST /api/schemes/{scheme_id}/load

加载方案到当前配置（替换所有现有规则组）。

### PUT /api/schemes/{scheme_id}

将当前配置更新到指定方案（覆盖方案内容）。

### DELETE /api/schemes/{scheme_id}

删除配置方案。

---

## 图片分析

### POST /api/enchantment/analyze

分析附魔截图（推荐使用 POST）。

**请求体：**
```json
{"filename": "fumo_PD23091777261903.png", "scheme_name": "武器"}
}
```

`scheme_name` 可选，不传时自动使用最近加载的方案。

**响应示例：**
```json
{
  "status": 1,
  "reason": "满足规则组「斗志组」: 斗志4 + 力量>=8",
  "attributes": [{"name": "力量", "value": 9}],
  "trait": {"name": "斗志", "level": 4},
  "matched_details": [{"name": "力量", "value": 9, "threshold": 8, "matched": true}],
  "trait_match": {"name": "斗志", "level": 4, "min_level": 4, "matched": true},
  "raw_text": "OCR原始文本...",
  "scheme_name": "武器"
}
```

`status`: 1=保留, 0=不保留, -1=识别失败

### GET /api/enchantment/analyze?filename=xxx

GET 方式分析（兼容外部程序调用）。

---

## 历史记录

### GET /api/history

获取分析历史，支持多维度筛选和分页。

**查询参数：**

| 参数 | 类型 | 说明 |
|------|------|------|
| limit | int | 每页条数（默认50） |
| offset | int | 偏移量 |
| status | int | 状态筛选：0=不保留, 1=保留 |
| trait_filter | string | 组合特性筛选 |
| attr_filters | string | 属性筛选（JSON数组，如 `["力量"]`） |
| scheme_filter | string | 方案名称筛选 |

**响应示例：**
```json
{
  "records": [...],
  "total": 120,
  "scheme_names": ["武器", "衣服"]
}
```

### DELETE /api/history/{history_id}

删除单条历史记录。

### DELETE /api/history

清空所有历史记录。

---

## 文件列表

### GET /api/files

列出截图目录下所有 PNG/JPG 文件。

**响应示例：**
```json
{"files": ["fumo_PD23091777261903.png", "fumo_PD23091777261905.png"]}
```

---

## 系统设置

### GET /api/settings

获取当前设置（截图路径）。

**响应示例：**
```json
{"image_dir": "C:\\path\\to\\screenshots", "default_image_dir": "C:\\project\\root"}
```

### PUT /api/settings

更新截图路径。

**请求体：**
```json
{"image_dir": "D:\\screenshots"}
```
