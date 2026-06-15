# zu-article-image-skill

`article-illustrator` 是一个轻量 Codex Skill，用于分析已经完成的 Markdown 文章，规划有语义价值的插图，调用当前运行时原生 `imagegen` 生成图片，并使用唯一原文锚点稳定插入文章。

## 设计边界

- 只负责文章配图，不写作、不润色、不发布文章。
- 默认先生成人工可编辑的 `imgs/illustration-plan.md`。
- Agent 负责语义分析、Prompt 设计和原生生图调用。
- Python 脚本负责计划校验、锚点定位、PNG 验证、状态回写和幂等插入。
- 不内置图片 API Provider、API Key 配置、CLI fallback、SVG 或 HTML 渲染。

## 安装依赖

```bash
python3 -m pip install -r article-illustrator/requirements.txt
```

将 `article-illustrator/` 安装或链接到 Codex Skills 目录后，可使用：

```text
Use $article-illustrator to create an illustration plan for article.md.
```

默认流程：

```text
读取文章
→ 生成计划
→ 等待确认
→ 保存独立 Prompt
→ 调用原生 imagegen
→ 验证 PNG
→ 精确插入文章
→ 输出报告
```

## 验证

```bash
python3 -m unittest discover -s tests -v
python3 /Users/zu/.codex/skills/.system/skill-creator/scripts/quick_validate.py article-illustrator
git diff --check
```

测试只覆盖确定性脚本和虚拟 PNG，不默认执行真实生图。

## 开源借鉴

项目借鉴 [JimLiu/baoyu-skills](https://github.com/JimLiu/baoyu-skills) 中以下有价值的设计：

- `baoyu-article-illustrator` 的 Type/Style 分离、确认门禁、Prompt 先落盘和真实术语驱动。
- `prompt-construction.md` 的结构化区域、标签、关系、风格和比例描述。
- `baoyu-image-gen` 的独立任务、失败隔离、重试边界和结构化结果。
- `codex-imagegen/validator.ts` 的真实 PNG 文件验证。

本项目不复制其多 Provider、EXTEND.md、Palette、水印、参考图库和复杂并发配置。
