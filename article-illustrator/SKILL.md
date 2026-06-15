---
name: article-illustrator
description: 为已完成的 Markdown 文章设计语义配图位置，将可直接编辑的自然语言生图 Prompt 作为隐藏标签插入文章；用户确认后扫描标签，调用当前运行时原生 imagegen 生成图片并插回文章。用于用户要求为文章配图、规划正文插图或根据文章内 Prompt 标签生成图片时。
---

# Article Illustrator

只负责为已经完成的 Markdown 文章设计、生成和插入配图。不要改写正文，不创建计划文件、Prompt 文件、任务 JSON 或状态文件。

`{baseDir}` 表示本 `SKILL.md` 所在目录。

## 硬约束

- 文章 Markdown 是唯一数据源。
- Prompt 直接使用自然语言，保存在文章内的 `article-illustration` HTML 注释标签中。
- 默认第一次执行只插入 Prompt 标签并总结方案，然后停止等待用户确认。
- 用户确认后的下一次执行只读取现有标签，不重新分析或调整插图位置。
- 只使用当前运行时原生 `imagegen`；不可用时停止，不切换 Provider、CLI、SVG、HTML 或 Canvas。
- 默认只生成缺失图片。已有图片不会因 Prompt 修改自动重新生成。
- 生成后保留 Prompt 标签，方便用户直接修改。

## 第一次执行：设计插图

1. 读取完整文章，理解核心观点、流程、架构、对比和视觉隐喻。
2. 读取 [illustration-types.md](references/illustration-types.md)、[visual-styles.md](references/visual-styles.md) 和 [prompt-guidelines.md](references/prompt-guidelines.md)。
3. 只选择确实有助于理解的配图位置。
4. 在对应正文位置后直接插入 [tag-format.md](references/tag-format.md) 定义的标签。
5. 运行：

   ```bash
   python3 {baseDir}/scripts/article_tags.py scan <article.md>
   ```

6. 向用户总结插图数量、章节、插入位置和图片目的，然后停止。不要调用 `imagegen`。

用户当前请求明确说“直接生成”“跳过确认”或同等含义时，可以继续执行生成阶段。

## 确认后执行：生成并插入

1. 运行 `scan`，以文章现有标签为唯一任务来源：

   ```bash
   python3 {baseDir}/scripts/article_tags.py scan <article.md>
   ```

2. 如果存在 `error`，先报告并停止，不猜测修复。
3. 对每个 `needs_generation` 项：
   - 读取 JSON 中的自然语言 `prompt` 和 `ratio`。
   - 每张图单独调用一次原生 `imagegen`。
   - 将结果复制到 JSON 中的绝对 `output_path`。
   - 单张失败只报告该项，继续其他项。
4. 生成完成后运行：

   ```bash
   python3 {baseDir}/scripts/article_tags.py sync <article.md>
   ```

5. 报告生成成功、失败、插入成功和已完成项。

## 重新生成

- 用户明确指定重新生成某个 `id` 时，可以覆盖对应 `imgs/{id}.png`。
- 否则用户删除对应图片文件后，再次执行即可重新生成。
- 仅修改 Prompt 不会自动覆盖已有图片。
