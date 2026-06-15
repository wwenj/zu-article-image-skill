# zu-article-image-skill

`article-illustrator` 是一个极简 Codex Skill：直接在 Markdown 文章的插图位置保存可编辑的自然语言生图 Prompt，用户确认后调用原生 `imagegen` 生成图片并插回文章。

## 核心流程

```text
第一次执行：
分析文章 → 插入 Prompt 标签 → 总结方案 → 等待确认

确认后执行：
扫描 Prompt 标签 → 原生 imagegen 生图 → 保存到 imgs/ → 插入图片引用
```

文章本身是唯一数据源，不创建计划文件、Prompt 文件、任务 JSON 或状态文件。

## 标签示例

```markdown
<!-- article-illustration id="01-agent-runtime" ratio="16:9" alt="Agent 执行流程"
创建一张用于技术文章的横向流程插图。

展示请求依次经过 Router、Planner、Executor 和 Validator。
使用从左到右的流程布局，蓝灰色技术风格，清晰箭头，保持充足留白。
-->
```

生成后标签永久保留，并在后方插入：

```markdown
![Agent 执行流程](imgs/01-agent-runtime.png)
```

## 脚本

```bash
python3 article-illustrator/scripts/article_tags.py scan article.md
python3 article-illustrator/scripts/article_tags.py sync article.md
```

- `scan`：解析标签，输出待生成、待插入、已完成和错误项。
- `sync`：将已经存在的图片引用插入对应标签后方。

脚本只使用 Python 标准库，无额外依赖。

## 验证

```bash
python3 -m unittest discover -s tests -v
python3 /Users/zu/.codex/skills/.system/skill-creator/scripts/quick_validate.py article-illustrator
git diff --check
```

不默认执行真实生图测试。

## 开源借鉴

项目保留 [JimLiu/baoyu-skills](https://github.com/JimLiu/baoyu-skills) 中有价值的语义配图设计：Type/Style 分离思路、真实术语驱动、自然语言 Prompt 的结构化表达，以及原生生图工具优先原则；不引入其多 Provider、配置系统和复杂状态管理。
