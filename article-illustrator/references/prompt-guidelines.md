# Prompt Guidelines

每张图的最终 Prompt 必须先保存到计划指定的 `prompt_file`。不要向 `imagegen` 传递未落盘的临时 Prompt。

`article_sha256` 记录生成 Prompt 时的源文章哈希。插图脚本更新文章后，已生成图片的 Prompt 保留原始哈希，不随计划中的当前文章哈希重写。

## 文件格式

```markdown
---
id: "01"
type: "comparison"
style: "technical"
aspect_ratio: "16:9"
output_file: "imgs/01-context-engineering.png"
article_sha256: "..."
---

USE CASE:
...
```

正文必须按以下顺序组织：

1. `USE CASE`
2. `PURPOSE`
3. `COMPOSITION`
4. 根据类型使用 `ZONES`、`STEPS` 或 `NODES`
5. `LABELS`
6. `RELATIONSHIPS`
7. `COLORS`
8. `STYLE`
9. `CONSTRAINTS`
10. `ASPECT`

## 通用规则

- 先描述信息结构，再描述视觉风格。
- 使用文章中的真实术语、数字、角色和关系。
- 按明确区域描述构图，并说明元素如何连接。
- 隐喻表达底层概念，不机械绘制字面比喻。
- 标签只保留必要关键词，要求逐字准确。
- 保持充足留白，使用简单背景，避免无意义装饰。
- 避免写实人物，除非文章明确需要。
- 禁止模型补充文章未提供的事实。
- 颜色名称和十六进制值仅用于生成指导，禁止显示为图片文字。
- 默认比例为 `16:9`。

所有 Prompt 的 `CONSTRAINTS` 至少包含：

```text
- Do not add facts, modules, metrics, or relationships not present in the article.
- Use only short, necessary labels and render them verbatim.
- Color names and hex values are rendering guidance only; do not display them.
- Keep a clean composition with generous white space and no watermark.
```

## 类型模板

### `concept`

```text
COMPOSITION: one central concept with related elements around it
NODES: central concept and each supporting element
RELATIONSHIPS: explain every connector and grouping
```

### `process`

```text
COMPOSITION: left-to-right or top-to-bottom process
STEPS: ordered steps with inputs and outputs
RELATIONSHIPS: arrow direction and key transitions
```

### `comparison`

```text
COMPOSITION: clear left/right split
ZONES: option A and option B using identical comparison dimensions
RELATIONSHIPS: visual bridge or change direction between both sides
```

### `architecture`

```text
COMPOSITION: layered architecture or relationship network
NODES: article-provided components and responsibilities
RELATIONSHIPS: calls, dependencies, and data-flow direction
```

### `scene`

```text
COMPOSITION: one symbolic focal point with supporting environment
ZONES: focal subject, context, and negative space
RELATIONSHIPS: explain how the scene conveys the article's underlying viewpoint
```
