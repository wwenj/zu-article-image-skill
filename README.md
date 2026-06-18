<div align="center">
  <h1>zu-article-image-skill</h1>
  <img src="assets/cover-no-text.png" alt="zu-article-image-skill cover" width="900">
  <p><strong>给 Markdown 文章加语义配图：先生成可编辑 Prompt，再生成图片并回写正文。</strong></p>
</div>

## 解决的问题

给文章配图，难点通常不是调用生图工具，而是准确表达“这里应该配什么图”。

直接把整篇文章丢给模型生图，不确定性高：模型可能选错重点、忽略上下文，生成结果一旦偏离预期，通常只能反复重试。手写 Prompt 可控性更强，但需要理解画面构图、视觉风格、比例和生图模型偏好，成本也高。

这个 skill 把流程拆成两步：

1. 先根据文章结构，在正文里插入可检查、可修改的配图 Prompt。
2. 用户确认后，再根据这些 Prompt 生成图片，保存到 `imgs/`，并把图片引用插回原位置。

文章 Markdown 是唯一数据源。不创建计划文件、Prompt 文件、任务 JSON 或额外状态文件。

## 工作方式

第一次执行只做提示词层：

1. 读取完整 Markdown 文章。
2. 梳理章节结构、上下文关系和信息密度。
3. 选择确实有助于理解的插图位置。
4. 在对应位置插入 `article-illustration` HTML 注释标签。
5. 在标签内写入自然语言 Prompt。
6. 总结插图方案，等待用户确认。

确认后才进入生图层：

1. `scan` 文章内已有 Prompt 标签。
2. 对缺失图片的标签逐个调用当前运行时原生 `imagegen`。
3. 将生成结果保存为 `imgs/{id}.png`。
4. `sync` 把 `![alt](imgs/{id}.png)` 插回对应标签后方。
5. 保留 Prompt 标签，方便后续微调和重新生成。

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

规划配图时，只让 skill 插入 Prompt 标签，不直接生成图片：

```text
使用 zu-article-image-skill 为 path/to/article.md 规划配图，只插入 Prompt 标签，不生成图片。
```

确认 Prompt 后，再继续要求：

```text
根据文章内已有 `article-illustration` 标签生成图片，并 sync 回正文。
```

## 标签示例

```markdown
<!-- article-illustration id="01-agent-runtime" ratio="16:9" alt="Agent 执行流程"
创建一张用于技术文章的横向流程插图。

展示请求依次经过 Router、Planner、Executor 和 Validator。
使用从左到右的流程布局，蓝灰色技术风格，清晰箭头，保持充足留白。
-->

![Agent 执行流程](imgs/01-agent-runtime.png)
```
