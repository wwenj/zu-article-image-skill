<div align="center">
  <h1>zu-article-image-skill</h1>
  <img src="assets/cover-no-text.png" alt="zu-article-image-skill cover" width="900">
  <p><strong>给 Markdown 文章加语义配图：1. 先生成可编辑 Prompt；2. 再生成图片并回写正文。</strong></p>
</div>

## 解决的问题

1. 在什么地方配插图
2. 配什么样的插图

这个 skill 把配图流程拆成两步：

1. 先根据文章结构，在正文里插入可检查、可修改的插图预渲染 Prompt 标签。
2. 用户确认后，再根据这些 Prompt 生成图片，保存到 `imgs/`，并把图片引用插回原位置。

文章 Markdown 是唯一数据源。不创建计划文件、Prompt 文件、任务 JSON 或额外状态文件。

## 工作方式

第一次执行只做提示词层：

1. 读取完整 Markdown 文章。
2. 梳理章节结构、上下文关系和信息密度。
3. 选择确实有助于理解的插图位置。
4. 在对应位置插入 `article-illustration` HTML 注释标签。
5. 自动选择合适的 `preset/type/style/palette`，并在标签内写入完整自然语言 Prompt。
6. 总结插图方案，等待用户确认。

确认后才进入生图层：

1. `scan` 文章内已有 Prompt 标签。
2. 对缺失图片的标签逐个调用当前运行时原生 `imagegen`。
3. 将生成结果保存为 `imgs/{id}.png`。
4. `sync` 把 `![alt](imgs/{id}.png)` 插回对应标签后方。
5. 保留 Prompt 标签，方便后续微调和重新生成。

## 技术方案

### 1. Markdown 是唯一状态源

所有配图信息都保存在原文章里，不额外创建计划文件、Prompt 文件、任务 JSON 或状态文件。

- Prompt 中间态：`article-illustration` HTML 注释标签。
- 图片输出：固定保存为 `imgs/{id}.png`。
- 图片引用：生成后插回为 `![alt](imgs/{id}.png)`。
- 后续微调：直接改文章里的 Prompt 标签即可。

### 2. 内置样式体系

Agent 不直接把文章丢给生图模型，而是先参考 `references/` 里的样式规则，把文章内容转成更稳定的插图 Prompt。

内置能力分为四层：

| 层级 | 作用 | 示例 |
| --- | --- | --- |
| `preset` | 一组常用样式组合 | `hand-drawn-edu`、`tech-blueprint`、`process-flow` |
| `type` | 决定信息结构 | `infographic`、`flowchart`、`comparison`、`framework`、`scene`、`timeline` |
| `style` | 决定画面语言 | `sketch-notes`、`blueprint`、`vector-illustration`、`ink-notes`、`editorial`、`screen-print`、`warm` |
| `palette` | 决定色彩语义 | `macaron`、`technical-blue`、`balanced`、`mono-ink`、`poster-duotone`、`warm-soft` |

当前内置 8 个 preset 场景：

- `hand-drawn-edu`：知识总结、教程、概念解释。
- `tech-blueprint`：系统架构、工程设计、模块关系。
- `process-flow`：步骤、执行链路、工作流。
- `side-by-side`：Before/After、方案差异、优劣对比。
- `ink-notes`：观点文、方法论、专业白板。
- `editorial-data`：数据、指标、报告结论。
- `poster-opinion`：强观点、社评、戏剧化隐喻。
- `warm-scene`：叙事、个人经历、温和场景表达。

### 3. 生成中间态标签

第一次执行时，Agent 会读取文章结构，选择真正需要配图的位置，并插入类似这样的标签：

```markdown
<!-- article-illustration id="01-agent-runtime" preset="process-flow" type="flowchart" style="sketch-notes" palette="macaron" ratio="16:9" alt="Agent 执行流程"
创建一张用于技术文章的横向流程图，帮助读者理解 Agent 请求从输入到输出的执行链路。

Layout: 从左到右的五段流程，整体保持充足留白。
Content: 用户输入、Router、Planner、Executor、Validator 和最终答案。
Style: sketch-notes 手绘教育信息图风格，暖色纸张背景，黑色手绘线条。
Palette: macaron。浅蓝表示系统模块，薄荷绿表示成功输出，珊瑚红只用于风险提示。颜色名和 hex 值不要显示在图片中。
Text: 只使用中文短标签，保持大字号和清晰可读。
Aspect: 16:9。
-->
```

其中 `preset/type/style/palette/ratio/alt` 是可读元数据，真正交给生图模型的是标签正文里的完整自然语言 Prompt。

### 4. 确认后生成图片

第一次只生成 Prompt，不生成图片。Agent 会总结每张图的位置、目的和样式，用户可以：

- 确认继续：进入生图阶段。
- 手动微调：直接编辑标签里的 Prompt。
- 重选样式：要求换成其他 preset 或 style 后重新生成 Prompt。

确认后，Agent 执行：

```bash
python3 zu-article-image-skill/scripts/article_tags.py scan article.md
```

然后只读取 `scan` 输出里的 `needs_generation` 项，逐张调用当前运行时原生 `imagegen`，并把结果保存到对应的 `output_path`。

### 5. 状态机与回插

`scripts/article_tags.py` 只负责确定性扫描和同步，不负责生图。

`scan` 会根据标签和图片文件计算状态：

| 状态 | 含义 |
| --- | --- |
| `needs_generation` | 标签存在，但 `imgs/{id}.png` 不存在 |
| `needs_insertion` | 图片存在，但文章里还没有 Markdown 图片引用 |
| `complete` | 图片文件和 Markdown 图片引用都存在 |
| `error` | 标签非法、ID 重复或图片引用重复 |

图片生成完成后执行：

```bash
python3 zu-article-image-skill/scripts/article_tags.py sync article.md
```

`sync` 会把图片引用插入对应标签后方，并保留原 Prompt 标签，方便以后继续调整或重新生成。

## 适合场景

- 中文技术文章、教程、观点长文和项目复盘
- 需要流程图、架构图、概念图、对比图的 Markdown 草稿
- 正文已经完成，只缺少配图规划和生成的文章
- 希望把配图 Prompt 直接维护在文章里，而不是拆到额外配置文件

## 安装到 Claude Code / Codex

Skill 来源是 [`wwenj/zu-article-image-skill`](https://github.com/wwenj/zu-article-image-skill) 仓库里的 `zu-article-image-skill/` 目录；Claude Code 放到 `~/.claude/skills/zu-article-image-skill/`，Codex 放到 `~/.agents/skills/zu-article-image-skill/`。

直接复制给 Claude Code 或 Codex：

```text
请从 https://github.com/wwenj/zu-article-image-skill 下载仓库，并把其中的 `zu-article-image-skill/` 目录安装到当前工具的个人 Skill 目录。
```

## 使用方式

直接一句话例如在 codex 中输入以下配图提示词：

```text
使用 zu-article-image-skill 为 article.md 规划配图
```

生成好中间提示词后，确认无误让 codex 继续生成图片：

```text
根据文章内已有 `article-illustration` 标签生成图片。
```
## 同类 Skill 关联推荐

文章完成后，插图前，可使用下面 Skill 做文章整理，主要针对去除 AI 味结构和语句，让文章更符合人类工程师写作习惯。

[zu-article-image-skill](https://github.com/wwenj/zu-article-image-skill)
