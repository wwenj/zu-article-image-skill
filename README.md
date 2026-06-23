<div align="center">
  <p><strong>中文</strong> | <a href="README.en.md">English</a></p>
  <h1>zu-article-image-skill</h1>
  <img src="assets/logo.png" alt="zu-article-image-skill logo" width="320">
  <p><strong>给 Markdown 文章加语义配图：先生成可编辑 Prompt，再生成图片并回写正文。</strong></p>
</div>

## 核心设计

这个 skill 只解决两件事：

1. 在什么地方配插图
2. 配什么样的插图

它把流程拆成两层：

1. **Prompt 层**：先根据文章结构，在正文里插入可检查、可修改的插图预渲染 Prompt 标签。
2. **生图层**：用户确认后，再根据这些 Prompt 生成图片，保存到 `imgs/`，并把图片引用插回原位置。

文章 Markdown 是唯一状态源。不创建计划文件、独立 Prompt 文件、任务 JSON 或额外状态文件。

## 技术方案

### 中间态标签

第一次执行只写入隐藏标签，不生成图片：

```markdown
<!-- article-illustration id="01-agent-runtime" preset="process-flow" type="flowchart" style="sketch-notes" palette="macaron" ratio="16:9" alt="Agent 执行流程"
创建一张用于技术文章的横向流程图，帮助读者理解 Agent 请求从输入到输出的执行链路。

Layout: 从左到右的五段流程，整体保持充足留白。
Content: 用户输入、Router、Planner、Executor、Validator 和最终答案。
Style: sketch-notes 手绘教育信息图风格，暖色纸张背景，黑色手绘线条。
Palette: macaron。浅蓝表示系统模块，薄荷绿表示成功输出，珊瑚红只用于风险提示。
Text: 只使用中文短标签，保持大字号和清晰可读。
Aspect: 16:9。
-->
```

`preset/type/style/palette/ratio/alt` 是可读元数据；真正用于生图的是标签正文里的完整自然语言 Prompt。

### 内置样式体系

Agent 会参考 `references/` 中的规则自动选择样式，用户也可以指定或修改。

| 层级 | 数量 | 作用 |
| --- | ---: | --- |
| `preset` | 8 | 常用场景组合，例如知识图、架构图、流程图、对比图 |
| `type` | 6 | 信息结构：`infographic`、`flowchart`、`comparison`、`framework`、`scene`、`timeline` |
| `style` | 7 | 画面语言：手绘、蓝图、矢量、白板、编辑、海报、温和场景 |
| `palette` | 6 | 色彩语义：柔和教育、技术蓝、均衡、黑白墨线、海报双色、暖色 |

当前内置 preset：

`hand-drawn-edu`、`tech-blueprint`、`process-flow`、`side-by-side`、`ink-notes`、`editorial-data`、`poster-opinion`、`warm-scene`

### 插图风格预览

示例图统一以“Markdown 文章配图 workflow”为主题，按内置 `style` 生成。

<table>
  <tr>
    <td align="center" width="50%">
      <img src="assets/style-previews/sketch-notes.jpg" alt="sketch-notes style preview" width="320"><br>
      <strong>sketch-notes</strong><br>
      手绘教育信息图，适合概念解释、教程和流程说明。
    </td>
    <td align="center" width="50%">
      <img src="assets/style-previews/blueprint.jpg" alt="blueprint style preview" width="320"><br>
      <strong>blueprint</strong><br>
      技术蓝图风格，适合架构、系统边界和数据流。
    </td>
  </tr>
  <tr>
    <td align="center" width="50%">
      <img src="assets/style-previews/vector-illustration.jpg" alt="vector-illustration style preview" width="320"><br>
      <strong>vector-illustration</strong><br>
      平面矢量风格，适合方案对比和知识卡片。
    </td>
    <td align="center" width="50%">
      <img src="assets/style-previews/ink-notes.jpg" alt="ink-notes style preview" width="320"><br>
      <strong>ink-notes</strong><br>
      白板笔记风格，适合方法论、框架和心智转变。
    </td>
  </tr>
  <tr>
    <td align="center" width="50%">
      <img src="assets/style-previews/editorial.jpg" alt="editorial style preview" width="320"><br>
      <strong>editorial</strong><br>
      杂志信息图风格，适合数据、指标和报告摘要。
    </td>
    <td align="center" width="50%">
      <img src="assets/style-previews/screen-print.jpg" alt="screen-print style preview" width="320"><br>
      <strong>screen-print</strong><br>
      丝网印刷海报风格，适合强观点和象征性主视觉。
    </td>
  </tr>
  <tr>
    <td align="center" width="50%">
      <img src="assets/style-previews/warm.jpg" alt="warm style preview" width="320"><br>
      <strong>warm</strong><br>
      温和叙事插图，适合个人经历和轻隐喻表达。
    </td>
    <td width="50%"></td>
  </tr>
</table>

### 状态机

`scripts/article_tags.py` 负责确定性扫描和回插：

| 命令 | 作用 |
| --- | --- |
| `scan` | 解析标签、校验属性、输出每张图的状态和保存路径 |
| `sync` | 在图片已存在时，把 `![alt](imgs/{id}.png)` 插回标签后方 |

状态含义：

| 状态 | 含义 |
| --- | --- |
| `needs_generation` | 标签存在，但 `imgs/{id}.png` 不存在 |
| `needs_insertion` | 图片存在，但文章里还没有图片引用 |
| `complete` | 图片文件和图片引用都存在 |
| `error` | 标签非法、ID 重复或图片引用重复 |

## 使用方式

规划配图：

```text
使用 zu-article-image-skill 为 article.md 规划配图
```

第一次执行结束后，skill 会总结每张图的位置、目的和样式。此时可以：

- 确认继续生成图片。
- 手动编辑文章里的 Prompt 标签。
- 要求换成其他 preset 或 style 后重新生成 Prompt。

确认后生成图片并回插：

```text
根据文章内已有 `article-illustration` 标签生成图片。
```

## 适合场景

- 中文技术文章、教程、观点长文、项目复盘
- 需要流程图、架构图、概念图、对比图的 Markdown 草稿
- 希望把配图 Prompt 直接维护在文章里，而不是拆到额外配置文件

## 安装到 Claude Code / Codex

Skill 来源是 [`wwenj/zu-article-image-skill`](https://github.com/wwenj/zu-article-image-skill) 仓库里的 `zu-article-image-skill/` 目录。

- Claude Code：复制到 `~/.claude/skills/zu-article-image-skill/`
- Codex：复制到 `~/.agents/skills/zu-article-image-skill/`

也可以直接让 Agent 安装：

```text
请从 https://github.com/wwenj/zu-article-image-skill 下载仓库，并把其中的 `zu-article-image-skill/` 目录安装到当前工具的个人 Skill 目录。
```

## 同类 Skill 关联推荐

文章完成后，插图前，可使用下面 Skill 做文章整理，主要针对去除 AI 味结构和语句，让文章更符合人类工程师写作习惯。

[zu-article-image-skill](https://github.com/wwenj/zu-article-image-skill)
