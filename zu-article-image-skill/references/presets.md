# Illustration Presets

Preset 是给 Agent 选择样式的快捷组合。它只用于帮助写完整自然语言 Prompt，不是生图工具参数。

默认由 Agent 根据文章内容选择；用户明确指定 preset、风格或 palette 时，以用户指定为准。

## 选择规则

| 内容信号 | 默认 preset | 展开 |
| --- | --- | --- |
| 没有强信号、知识总结、概念解释 | `hand-drawn-edu` | `infographic` + `sketch-notes` + `macaron` |
| 系统架构、工程设计、技术模块关系 | `tech-blueprint` | `framework` + `blueprint` + `technical-blue` |
| 步骤、执行链路、工作流、生命周期 | `process-flow` | `flowchart` + `sketch-notes` + `macaron` |
| Before/After、方案差异、优劣对比 | `side-by-side` | `comparison` + `vector-illustration` + `balanced` |
| 观点文、方法论、专业白板、心智转变 | `ink-notes` | `framework` + `ink-notes` + `mono-ink` |
| 数据、指标、报告、调研发现 | `editorial-data` | `infographic` + `editorial` + `balanced` |
| 强观点、社评、文化评论、戏剧化隐喻 | `poster-opinion` | `scene` + `screen-print` + `poster-duotone` |
| 叙事、个人经历、温和场景表达 | `warm-scene` | `scene` + `warm` + `warm-soft` |

## Preset 细则

### hand-drawn-edu

- type: `infographic`
- style: `sketch-notes`
- palette: `macaron`
- 用于：知识解释、教程、概念总结、一般技术文章。
- Prompt 重点：2-6 个信息块、手绘线条、短标签、底部一句 takeaway。

### tech-blueprint

- type: `framework`
- style: `blueprint`
- palette: `technical-blue`
- 用于：架构、模块关系、系统边界、工程流程。
- Prompt 重点：网格背景、精确线条、分层模块、连接方向、数据流。

### process-flow

- type: `flowchart`
- style: `sketch-notes`
- palette: `macaron`
- 用于：步骤、链路、生命周期、操作流程。
- Prompt 重点：清晰步骤、从左到右或自上而下、箭头方向、每步输入输出。

### side-by-side

- type: `comparison`
- style: `vector-illustration`
- palette: `balanced`
- 用于：Before/After、传统方案 vs 新方案、优缺点比较。
- Prompt 重点：左右对称维度、清晰分隔、相同对比项、避免偏装饰。

### ink-notes

- type: `framework`
- style: `ink-notes`
- palette: `mono-ink`
- 用于：方法论、专业白板、观点框架、心智转变。
- Prompt 重点：白底黑线、少量语义强调色、手写标注、框架关系。

### editorial-data

- type: `infographic`
- style: `editorial`
- palette: `balanced`
- 用于：数据、指标、报告结论、调研摘要。
- Prompt 重点：杂志信息图、数据分区、真实术语和数字、清晰层级。

### poster-opinion

- type: `scene`
- style: `screen-print`
- palette: `poster-duotone`
- 用于：强观点、社评、文化评论、戏剧化主题。
- Prompt 重点：象征性主视觉、有限色块、负空间、不要直画表面比喻。

### warm-scene

- type: `scene`
- style: `warm`
- palette: `warm-soft`
- 用于：个人叙事、体验、温和隐喻、成长故事。
- Prompt 重点：单一焦点、柔和氛围、低复杂度、避免泛泛装饰图。

