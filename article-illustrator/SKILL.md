---
name: article-illustrator
description: 分析已完成的 Markdown 文章，基于文章语义识别配图机会，生成可人工调整的插图计划和独立图片 Prompt，调用当前运行时原生 imagegen 生成插图，并使用唯一原文锚点精确插入文章。用于用户要求为文章配图、生成正文插图、分析文章插图位置或批量生成文章图片时。
---

# Article Illustrator

只为已经完成的 Markdown 文章规划、生成和插入语义配图。不要写作、润色、改写、发布文章，也不要修改正文内容。

`{baseDir}` 表示本 `SKILL.md` 所在目录。调用脚本时使用 `{baseDir}/scripts/...`，并向 `--plan` 传入目标文章目录中的实际计划路径。

## 硬约束

- 不按字数、段落数或标题数量强行配图；没有明确视觉价值时输出无需配图。
- 默认只生成 `imgs/illustration-plan.md`，然后停止并等待用户确认。
- 只有用户当前请求明确要求直接生成或跳过确认时，才能自动批准任务。
- 每个 Prompt 必须先保存到 `imgs/prompts/`，再调用生图工具。
- 只使用当前运行时原生 `imagegen`。不可用时停止，不切换 CLI、API Provider、SVG、HTML 或 Canvas。
- 不修补生成图片中的错误文字。文字、关系或构图存在风险时，将 `qa.status` 标记为 `needs_review`。
- 所有插入位置必须使用原文中唯一存在的完整 Markdown 块。
- 只插入经过 PNG 验证且 `generation.status: generated` 的图片。

## 工作流

1. **分析文章**
   - 读取完整文章并计算 SHA-256。
   - 识别核心观点、流程、架构、对比和视觉隐喻。
   - 读取 [illustration-types.md](references/illustration-types.md) 和 [visual-styles.md](references/visual-styles.md)。

2. **创建计划**
   - 读取 [plan-schema.md](references/plan-schema.md)。
   - 创建 `imgs/illustration-plan.md`，所有候选默认使用 `approval: pending`。
   - 从文章复制完整且唯一的 Markdown 块作为 `insert_after`。
     - 运行：
     ```bash
     python3 {baseDir}/scripts/validate_plan.py \
       --plan <article-dir>/imgs/illustration-plan.md \
       --stage plan
     ```
   - 未明确跳过确认时停止并等待用户修改计划。

3. **保存 Prompt**
   - 仅处理 `approval: approved` 的任务。
   - 读取 [prompt-guidelines.md](references/prompt-guidelines.md)。
   - 将每张图片的完整最终 Prompt 保存到计划指定的 `prompt_file`。

4. **准备生成任务**
     - 运行：
     ```bash
     python3 {baseDir}/scripts/prepare_generation.py \
       --plan <article-dir>/imgs/illustration-plan.md \
       --output <article-dir>/imgs/generation-tasks.json
     ```

5. **调用原生 imagegen**
   - 读取 [generation-workflow.md](references/generation-workflow.md)。
   - 每张图读取对应 Prompt 文件并单独调用一次原生 `imagegen`，每批最多 4 张。
   - 将生成结果从运行时默认目录复制到任务的 `output_file`。
   - 使用 `record_generation.py` 记录每项成功、失败和 QA 结果。

6. **插入文章**
     - 运行：
     ```bash
     python3 {baseDir}/scripts/insert_images.py \
       --plan <article-dir>/imgs/illustration-plan.md
     ```
   - 脚本会重新检查文章哈希、唯一锚点、PNG 和重复图片引用。

7. **报告**
   - 分别报告 pending、approved、skip、生成成功、生成失败、needs_review、插入成功、已存在和插入失败数量。
   - 对每个失败项报告阶段和原因。

## 脚本约定

脚本 stdout 输出 JSON，非零退出码表示存在错误。安装依赖：

```bash
python3 -m pip install -r {baseDir}/requirements.txt
```
