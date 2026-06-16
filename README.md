<div align="center">
  <h1>Article Illustrator Skill</h1>
  <img src="assets/cover-no-text.png" alt="Article Illustrator cover" width="900">
  <p><strong>把 Markdown 文章里的配图意图，直接变成可编辑、可生成、可同步的文章内 Prompt。</strong></p>
</div>

> 说明：这个 skill 的一部分设计参考了 [JimLiu/baoyu-skills](https://github.com/JimLiu/baoyu-skills) 中语义配图的思路。当前版本已经按我的 Codex 写作工作流做了简化，更适合中文技术文章、观点稿、项目复盘和教程类 Markdown 的正文配图。

Article Illustrator 是一个面向中文技术文章配图的 Codex skill。它不负责改写正文，也不维护额外配置层，而是在 Markdown 文章的插图位置保存可编辑的自然语言生图 Prompt。用户确认后，再扫描这些标签，调用当前运行时原生 `imagegen` 生成图片并插回文章。

它适合处理：

- 中文技术文章、观点长文、教程和项目复盘
- 需要流程图、架构图、概念图、对比图的 Markdown 草稿
- 已经写完正文，只缺少语义配图规划和生成的文章
- 想直接在文章里维护插图 Prompt，而不是维护额外计划文件的写作流程

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
