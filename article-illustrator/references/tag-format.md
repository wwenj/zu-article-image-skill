# Inline Prompt Tag Format

## 格式

将标签直接放在需要插图的位置：

```markdown
<!-- article-illustration id="01-agent-runtime" ratio="16:9" alt="Agent 执行流程"
创建一张用于技术文章的横向流程插图。

展示请求依次经过 Router、Planner、Executor 和 Validator。
使用从左到右的流程布局，蓝灰色技术风格，清晰箭头，保持充足留白。
-->
```

生成完成后保留标签，并在其后插入：

```markdown
![Agent 执行流程](imgs/01-agent-runtime.png)
```

## 属性

- `id`：必填且文章内唯一；只允许小写字母、数字和连字符。图片固定保存为 `imgs/{id}.png`。
- `ratio`：可选，默认 `16:9`；格式为正数 `width:height`。
- `alt`：可选；缺失时使用 `文章插图 {id}`。
- 标签正文：必填自然语言 Prompt。

标签开始和结束标记必须各自独占一行。Prompt 禁止包含 `-->`。

## 扫描状态

- `needs_generation`：图片文件不存在。
- `needs_insertion`：图片存在，但文章没有对应图片引用。
- `complete`：图片文件和图片引用均存在。
- `error`：标签非法、ID 重复或图片引用重复。

## 命令

```bash
python3 scripts/article_tags.py scan article.md
python3 scripts/article_tags.py sync article.md
```

`scan` 只读取文章并输出 JSON。`sync` 只插入已存在图片的引用，不调用生图工具。

