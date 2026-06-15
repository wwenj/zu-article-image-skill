# Illustration Plan Schema

`imgs/illustration-plan.md` 必须只包含标题和一个 YAML 代码块：

````markdown
# Illustration Plan

```yaml
version: 1
article:
  path: "../article.md"
  sha256: "<article sha256>"
style: "technical"
aspect_ratio: "16:9"
illustrations: []
```
````

## Illustration 字段

```yaml
- id: "01"
  title: "Context Engineering 对比"
  approval: "pending"
  section: "从 Prompt Engineering 到 Context Engineering"
  source_summary: "文章说明两种工程方式的核心差异"
  visual_purpose: "帮助读者快速理解两种工程方式的不同"
  type: "comparison"
  insert_after: |
    上下文工程决定了模型最终能够看到什么。
  visual_content:
    - "左侧：Prompt Engineering"
    - "右侧：Context Engineering"
  article_terms:
    - "Prompt Engineering"
    - "Context Engineering"
  prompt_file: "imgs/prompts/01-context-engineering.md"
  output_file: "imgs/01-context-engineering.png"
  generation:
    status: "not_started"
    attempts: 0
    prompt_sha256: null
    error: null
  qa:
    status: "not_checked"
    notes: null
  insertion:
    status: "not_started"
    error: null
```

## 枚举

- `style`: `technical | editorial | sketch-note`
- `type`: `concept | process | comparison | architecture | scene`
- `approval`: `pending | approved | skip`
- `generation.status`: `not_started | generated | failed`
- `qa.status`: `not_checked | passed | needs_review`
- `insertion.status`: `not_started | inserted | already_present | failed`

## 规则

- `insert_after` 必须复制原文中的完整 Markdown 块，并且唯一匹配。
- `id`、`prompt_file` 和 `output_file` 必须唯一。
- `prompt_file` 和 `output_file` 必须是文章目录下 `imgs/` 中的相对路径。
- Prompt 文件必须使用 `.md`，图片必须使用 `.png`。
- `generated` 必须包含 `prompt_sha256`。
- `failed` 必须包含对应阶段的 `error`。
- `inserted` 和 `already_present` 仅适用于已经生成的图片。
- 插入脚本成功修改文章后会更新 `article.sha256`，以支持幂等重复执行。

