# Natural Language Prompt Guidelines

Prompt 直接写在文章的 `article-illustration` 标签正文中。不要使用 YAML、frontmatter 或独立 Prompt 文件。可以使用清晰的小标题帮助生图模型理解，但最终必须是自然语言 Prompt。

## 编写原则

- 使用自然语言完整描述图片目的、内容、构图、关系和风格。
- 先根据 [presets.md](presets.md) 选择 preset，再把 type/style/palette 展开成完整描述。
- 使用文章中的真实术语、数字、角色和关系。
- 先说清图片帮助读者理解什么，再描述如何呈现。
- 对流程、架构和对比图，明确区域、顺序、箭头和连接关系。
- 隐喻应表达文章底层观点，不机械绘制字面比喻。
- 标签只使用必要短词，要求逐字准确。
- 保持充足留白，避免无意义装饰、复杂背景和水印。
- 禁止补充文章未提供的事实、模块或数据。
- 颜色名称和十六进制值仅作为生成指导，不显示在图片中。
- 图片中文字必须短，优先关键词、模块名、数字和极短短语。
- 如果模型难以准确生成文字，Prompt 应减少文字数量，而不是写长句。

## 推荐结构

每个 Prompt 优先覆盖以下内容：

```text
创建一张[类型]，帮助读者理解[文章中的具体观点或关系]。

Layout: [构图、阅读方向、分区方式]。
Content: [真实术语、步骤、模块、数据或对比维度]。
Relationships: [箭头、依赖、层级、左右对照或时间顺序]。
Style: [style 的画面规则]。
Palette: [palette 的颜色语义]。颜色名和 hex 值仅作为渲染指导，不要显示在图片中。
Text: [图片中文字语言、长度和可读性限制]。
Aspect: [ratio]。
```

不需要机械使用所有字段名，但这些信息必须在 Prompt 中出现。

## 示例

```text
创建一张用于技术文章的横向流程图，帮助读者理解 Agent 请求从输入到输出的执行链路。

Layout: 从左到右的五段流程，整体保持充足留白，所有模块在同一水平线上。
Content: 用户输入、Router、Planner、Executor、Validator 和最终答案。
Relationships: 使用清晰箭头表达调用方向，Router 到 Planner 标注“任务识别”，Executor 到 Validator 标注“结果校验”。
Style: sketch-notes 手绘教育信息图风格，暖色纸张背景，黑色手绘线条，圆角信息框。
Palette: macaron。浅蓝表示系统模块，薄荷绿表示成功输出，珊瑚红只用于风险提示。颜色名和 hex 值不要显示在图片中。
Text: 只使用中文短标签，保持大字号和清晰可读，不写长句。
Aspect: 16:9。
```
