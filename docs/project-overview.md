# RO 附魔分析系统 - 项目概述

## 项目简介

仙境传说RO（Ragnarok Online）附魔截图自动分析系统。通过 OCR 识别附魔截图中的属性和组合特性，根据用户预设的规则组自动判定装备是否值得保留。

## 核心功能

- **规则组配置**：创建多条规则组，组内属性 AND（全部满足），组间 OR（任一满足即保留）
- **组合特性**：每个规则组可关联14种组合特性（如斗志、尖锐、洞察等），支持等级筛选（Lv1-4）
- **OCR 识别**：基于 OnnxOCR（PP-OCRv5 ONNX）识别附魔截图，双通OCR互补检测
- **批量分析**：支持逐张选择图片进行分析，自动记录历史
- **配置方案**：保存/加载/切换多套配置方案，按装备部位管理
- **历史记录**：支持按状态、特性、属性、方案多维筛选，分页浏览

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python 3.10 + FastAPI + SQLite |
| OCR | OnnxOCR (PP-OCRv5 ONNX) + OpenCV |
| 前端 | Vue 3 (CDN) + Tailwind CSS (CDN) |
| 包管理 | uv |

## 项目结构

```
fumo_pic/
├── backend/
│   ├── main.py              # FastAPI 入口，所有 API 端点
│   ├── database.py           # SQLite CRUD 操作
│   ├── ocr_engine.py         # OnnxOCR 封装，双通 OCR + 文本解析
│   ├── matcher.py            # 规则组匹配引擎
│   ├── attribute_config.py   # 34种属性定义 + 14种组合特性
│   └── onnxocr/              # OnnxOCR 模块（含 PP-OCRv5 ONNX 模型）
├── frontend/
│   └── index.html            # Vue 3 SPA 单页面应用
├── data/
│   └── enchantment.db        # SQLite 数据库（运行时生成）
├── docs/                     # 项目文档
└── .venv/                    # Python 虚拟环境
```

## 快速启动

```bash
cd fumo_pic
.venv/Scripts/python.exe -m uvicorn backend.main:app --host 0.0.0.0 --port 60016
```

访问 `http://localhost:60016` 即可使用。

## 文档索引

- [API 接口文档](./api-reference.md) - 所有 REST API 端点详细说明
- [匹配规则说明](./matching-rules.md) - 规则组匹配逻辑和组合特性
- [OCR 引擎说明](./ocr-engine.md) - OCR 识别流程和预处理流水线
- [数据库设计](./database-schema.md) - 表结构和数据模型
- [属性与特性定义](./attribute-definitions.md) - 所有属性取值范围和组合特性
