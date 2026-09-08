[English](./README.en.md) · [Website](https://dropbrief.lei6393.com) · [GitHub](https://github.com/SuperMarioYL/dropbrief)

<picture>
  <source media="(max-width: 600px) and (prefers-color-scheme: dark)" srcset="./assets/presentation/hero-mobile-dark.svg">
  <source media="(max-width: 600px)" srcset="./assets/presentation/hero-mobile-light.svg">
  <source media="(prefers-color-scheme: dark)" srcset="./assets/presentation/hero-dark.svg">
  <img src="./assets/presentation/hero-light.svg" width="960" alt="Hero diagram">
</picture>

# dropbrief

**把发布信息与配置变化放在一起。**

dropbrief 将登记仓库状态、量化列表与选定配置字段差异组合成缓存发布简报。

## 为什么需要它

下载模型更新前，运维需要集中查看可用产物与配置差异。保存的简报也能为离线环境提供可检查的带时间快照。

- **集中输入** — 发布元数据与前版配置组合为简报。
- **检查字段变化** — 差异保留旧值与新值。
- **读取保存快照** — 离线模式可读取已有简报。

## 架构

<picture>
  <source media="(max-width: 600px) and (prefers-color-scheme: dark)" srcset="./assets/presentation/architecture-mobile-dark.svg">
  <source media="(max-width: 600px)" srcset="./assets/presentation/architecture-mobile-light.svg">
  <source media="(prefers-color-scheme: dark)" srcset="./assets/presentation/architecture-dark.svg">
  <img src="./assets/presentation/architecture-light.svg" width="960" alt="Architecture diagram">
</picture>

登记表解析模型别名和前一版本；fetch 将配置 HTTP 元数据存入缓存；archdiff 比较展开后的选定字段；briefing 组合记录与规则式切换提示，snapshot 可不联网读取保存简报。

| 组件 | 职责 |
| --- | --- |
| `Model registry` | registry.py |
| `Fetch / snapshot` | fetch.py; snapshot.py |
| `Config-field diff` | archdiff.py |
| `Cached brief` | briefing.py |

## 安装与快速上手

使用仓库清单指定的运行时版本构建，并在仓库根目录运行示例。

```bash
git clone https://github.com/SuperMarioYL/dropbrief.git
cd dropbrief
uv venv .venv
uv pip install --python .venv/bin/python -e .
source .venv/bin/activate
```

比较两份完整合成配置，其中 hidden_size 变化，记录性名称字段也被修改。

```bash
.venv/bin/python examples/presentation-demo.py
```

## 实际运行示例

<picture>
  <source media="(max-width: 600px) and (prefers-color-scheme: dark)" srcset="./assets/presentation/process-mobile-dark.svg">
  <source media="(max-width: 600px)" srcset="./assets/presentation/process-mobile-light.svg">
  <source media="(prefers-color-scheme: dark)" srcset="./assets/presentation/process-dark.svg">
  <img src="./assets/presentation/process-light.svg" width="960" alt="Process diagram">
</picture>

The production diff reports hidden_size changing from 128 to 256 while excluding _name_or_path.

```text
{
  "identical_compared_fields": false,
  "unchanged_fields": 2,
  "changes": [
    {
      "field": "hidden_size",
      "old": 128,
      "new": 256,
      "change": "changed"
    }
  ]
}
```

完整命令与输出保存在 [docs/demo-results.json](./docs/demo-results.json). 输入和复现代码均随仓提供。

![已有终端录制](./assets/demo.gif)

保留已有录制供参考；上方文字示例给出当前可复现的操作。

## 用法

CLI 提供以下操作。示例之外的命令需要替换成你的文件路径或标识。

```bash
dropbrief families
dropbrief brief --offline qwen3.8-27b
# Network access is used by online status:
dropbrief status <registered-alias>
```

## 配置

docs/model-families.yaml 定义模型别名、源和 prior_alias。DROPBRIEF_CACHE_DIR 指定缓存，DROPBRIEF_SNAPSHOT_DIR 指定保存快照。随仓离线示例应在包含 snapshots 的源码目录运行。

## 集成与职责分工

<picture>
  <source media="(max-width: 600px) and (prefers-color-scheme: dark)" srcset="./assets/presentation/integrations-mobile-dark.svg">
  <source media="(max-width: 600px)" srcset="./assets/presentation/integrations-mobile-light.svg">
  <source media="(prefers-color-scheme: dark)" srcset="./assets/presentation/integrations-dark.svg">
  <img src="./assets/presentation/integrations-light.svg" width="960" alt="Integrations diagram">
</picture>

以下路径已有源码实现。按任务选择输入，并把生成的结果与项目一起保存。

| 路径 | 已实现职责 |
| --- | --- |
| Model YAML | Aliases and source repositories |
| HF / ModelScope HTTP | Configured metadata fetch |
| Config JSON | Selected field comparison |
| Offline snapshots | Saved DropBrief JSON |

## 限制与后续方向

- 文件列表显示可用，不代表该量化能在你的硬件运行。
- 被比较字段不变，不证明架构完全相同，也不证明能力提升来自训练。diff 会排除部分记录与 token 字段。
- 切换提示是简单启发式，不是部署建议；快照反映记录时刻，不代表当前可用性。

更可靠的部署指导需要元数据之外的负载基准与目标硬件证据。

## 许可与贡献

许可见 [LICENSE](./LICENSE). 反馈问题时请提供最小输入、执行命令和实际输出。
