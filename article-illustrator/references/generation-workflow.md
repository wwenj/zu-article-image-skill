# Native Imagegen Workflow

只使用当前运行时原生 `imagegen`。不可用时保留计划和 Prompt 并停止；不要切换 API、CLI 或其他 Provider。

## 准备

1. 确保所有 approved 项的 Prompt 已保存。
2. 运行 `prepare_generation.py` 创建 `imgs/generation-tasks.json`。
3. 只执行输出中的 `tasks`；不要执行 `skipped` 项。

## 调用规则

- 每张不同图片单独调用一次原生 `imagegen`。
- 每批最多并行 4 张；`prepare_generation.py --batch-size` 只接受 `1` 到 `4`。
- 调用前读取任务的 `prompt_file` 全文。
- 不依赖原生工具的目标路径参数。
- 将选定结果从运行时默认生成目录复制到任务的 `output_file`。
- 不覆盖已经存在的输出文件。
- 工具错误、输出缺失或无效 PNG 最多重试一次。
- 单项失败不删除其他成功图片，也不阻塞下一项。
- 不使用 SVG、HTML、Canvas 或脚本生成图片替代结果。

## 结果验证与记录

成功结果必须：

- 文件存在。
- 大小至少 1000 字节。
- PNG magic bytes 正确。
- 输出路径与任务一致。
- Prompt SHA-256 与任务一致。
- 插入前 Prompt 文件不得在图片生成后发生变化。

记录成功：

```bash
python3 {baseDir}/scripts/record_generation.py \
  --plan <article-dir>/imgs/illustration-plan.md \
  --id 01 \
  --success \
  --prompt-sha256 "<generation task prompt_sha256>" \
  --qa passed
```

技术图、流程图或任何包含文字与关系的图片必须视觉检查。存在错字、乱码、错误箭头、缺失组件或关系不准确时，不修补图片，记录：

```bash
python3 {baseDir}/scripts/record_generation.py \
  --plan <article-dir>/imgs/illustration-plan.md \
  --id 01 \
  --success \
  --prompt-sha256 "<generation task prompt_sha256>" \
  --qa needs_review \
  --qa-notes "标签文字和数据流方向需要人工确认"
```

记录失败：

```bash
python3 {baseDir}/scripts/record_generation.py \
  --plan <article-dir>/imgs/illustration-plan.md \
  --id 01 \
  --failure \
  --error "imagegen output missing"
```

## 最终报告

分别报告：

- 识别机会数。
- pending、approved、skip 数。
- 生成成功、生成失败和 `needs_review` 数。
- 插入成功、已存在和插入失败数。
- 每个失败项的阶段与错误原因。
