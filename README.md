<div align="right"><sub><a href="./README.en.md">English</a>&nbsp;&nbsp;⇄&nbsp;&nbsp;<b>简体中文</b></sub></div>

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="./assets/hero-dark.svg">
    <source media="(prefers-color-scheme: light)" srcset="./assets/hero-light.svg">
    <img src="./assets/hero-light.svg" width="880" alt="dropbrief — 国产大模型发布决策简报">
  </picture>
</p>

<p align="center"><sub>每次国产模型发布都要刷几小时 reddit / HuggingFace / ModelScope 才知道上线没、架构改没、哪个量化能用、值不值得换 —— dropbrief 把这四问压成一条缓存命令，信创气隙环境也能离线用。</sub></p>

<h3 align="center">下载之前先做决策 —— 一条命令看懂每一次国产模型 drop。</h3>

<p align="center">
  <a href="./LICENSE"><img src="https://img.shields.io/github/license/SuperMarioYL/dropbrief?color=0071E3&label=license" alt="license"></a>
  <a href="https://github.com/SuperMarioYL/dropbrief/releases"><img src="https://img.shields.io/github/v/release/SuperMarioYL/dropbrief?include_prereleases&label=release" alt="release"></a>
  <img src="https://img.shields.io/github/actions/workflow/status/SuperMarioYL/dropbrief/ci.yml?branch=main&label=ci" alt="ci">
  <img src="https://img.shields.io/badge/python-3.12%2B-3776AB?logo=python&logoColor=white" alt="python">
  <img src="https://img.shields.io/badge/air--gap-ready-10A37F" alt="air-gap ready">
  <img src="https://img.shields.io/badge/arch--delta-5E5CE6" alt="arch-delta">
</p>

---

每次 Qwen / GLM / DeepSeek 新版本发布，运维要跨 reddit、HuggingFace、ModelScope、hfviewer 几个小时手动 triangulate：发布页常常在 mid-release 被下架（Qwen3.8 那波就是），没人知道哪个量化真能跑、架构相对上一版到底改没改。在信创/政企气隙环境这套手动 gauntlet 是结构上不可能完成的（没有出站）。dropbrief 用一条 15 分钟缓存的命令把这套研究压成 60 秒，气隙盒子用 `--offline` 读预打包快照，零出站拿到同样的决策情报。

## <img src="https://api.iconify.design/tabler:topology-star-3.svg?color=%230071E3&width=24" height="22" align="absmiddle" alt=""> 架构

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="./assets/atlas-dark.svg">
    <source media="(prefers-color-scheme: light)" srcset="./assets/atlas-light.svg">
    <img src="./assets/atlas-light.svg" width="880" alt="dropbrief 架构：CLI→Fetch→ArchDiff→Briefing，气隙 Snapshot 离线分支">
  </picture>
</p>

单进程、单 `uvx` 入口、无服务、无数据库。`fetch.py` 抓 HF+ModelScope+reddit 并落 15 分钟 JSON 缓存；`archdiff.py` 对 `config.json` 做字段差分；`briefing.py` 合成一屏决策简报；`snapshot.py` 让气隙环境用 `--offline` 读预打包快照零出站复现同样输出。残留价值刻意压在 `archdiff` + `briefing`，而不是爬虫本身（见下方非目标与路线图）。

## <img src="https://api.iconify.design/tabler:help.svg?color=%230071E3&width=24" height="22" align="absmiddle" alt=""> 它回答的四问

| 问题 | 子命令 | 数据来源 | m1 |
| --- | --- | --- | :-: |
| 上线没 | `dropbrief status` | HF + ModelScope HTTP 探测 + 文件清单 | ✓ |
| 架构改没 | `dropbrief diff` | `config.json` 字段差分 vs 上一版 | ✓ 基础 |
| 哪个量化能用 | `dropbrief status` / `brief` | FP8 / GGUF / AWQ 跨仓库清单 | ✓ |
| 值不值得换 | `dropbrief brief` | arch×quant×reconfig 启发式 | ✓ 基础 |

## <img src="https://api.iconify.design/tabler:rocket.svg?color=%230071E3&width=24" height="22" align="absmiddle" alt=""> 安装 + 快速开始

冷启动到第一个可见结果，一条命令（首次运行即离线，读内置 Qwen3.8-27B 公共快照，零出站）：

```bash
uvx dropbrief brief --offline qwen3.8-27b
```

联网环境想看实时上线状态与量化清单：

```bash
uv tool install dropbrief
dropbrief status qwen3.8-27b
```

<details>
<summary>样例简报输出（<code>dropbrief brief --offline qwen3.8-27b</code>）</summary>

```markdown
# dropbrief 简报 — Qwen/Qwen3.8-27B

> 信创建议 [建议持有]：Qwen/Qwen3.8-27B —— 架构与 Qwen/Qwen3.6-27B 同构；
> 在线镜像 huggingface/modelscope；可用量化 FP8/GGUF；reconfig 成本 low；
> 依据 arch×quant×reconfig 启发式，可入采购备忘。

## 1. 上线没
- ✓ huggingface Qwen/Qwen3.8-27B — HTTP 200 · 34 files
- ✓ modelscope  Qwen/Qwen3.8-27B — HTTP 200 · 34 files

## 2. 架构改没
Qwen/Qwen3.8-27B 的架构与 Qwen/Qwen3.6-27B 完全一致 (9 个配置字段逐一相同，0 项变更)。
版本号变了但结构没变 —— 能力增益来自训练，而非架构。

## 3. 哪个量化能用
- ✓ FP8  · huggingface Qwen/Qwen3.8-27B-FP8
- ✓ GGUF · huggingface Qwen/Qwen3.8-27B-GGUF
- ✓ GGUF · modelscope  Qwen/Qwen3.8-27B-GGUF

## 4. 值不值得换
- 判定：hold · reconfig 成本 low
- 架构同构，能力增益源于训练；按业务需要灰度切换即可，不必抢跑。
```

</details>

## <img src="https://api.iconify.design/tabler:terminal-2.svg?color=%230071E3&width=24" height="22" align="absmiddle" alt=""> 用法

```bash
# m1 伪证：30 行 httpx 能否答上线+量化（15min 缓存）
dropbrief status qwen3.8-27b

# 架构差分 vs 上一版（config.json 字段级）
dropbrief diff qwen3.8-27b

# 一屏决策简报，写入 dropbrief-qwen3.8-27b-<date>.md
dropbrief brief qwen3.8-27b --out ./briefs

# 气隙离线：读预打包快照，零出站
dropbrief brief --offline qwen3.8-27b

# 列出注册表支持的全部家族
dropbrief families
```

别名解析宽松：`qwen3.8-27b` / `Qwen3.8-27B` / `Qwen/Qwen3.8-27B` 都指向同一条记录，照着 reddit 帖子随手敲即可。

## <img src="https://api.iconify.design/tabler:photo.svg?color=%230071E3&width=24" height="22" align="absmiddle" alt=""> Demo

![demo](assets/demo.gif)

> 上面这条由 `docs/demo.tape`（vhs 脚本）驱动真实二进制渲染，`.github/workflows/demo.yml` 在打 tag / 手动触发时刷新。本地复现：`vhs docs/demo.tape`。

## <img src="https://api.iconify.design/tabler:adjustments.svg?color=%230071E3&width=24" height="22" align="absmiddle" alt=""> 配置

唯一配置是 `docs/model-families.yaml`（随包内置，无需 clone 仓库即可用）。新增 drop 时编辑此文件即可。

| 键 | 类型 | 默认 | 含义 |
| --- | --- | --- | --- |
| `families[].family` | str | — | 家族名（qwen3 / glm4 / deepseek / kimi） |
| `families[].vendor` | str | — | 厂商 |
| `families[].models[].alias` | str | — | 用户输入的 drop 名 |
| `families[].models[].hf_repo` | str | — | HuggingFace 仓库 id |
| `families[].models[].modelscope_id` | str | — | ModelScope 仓库 id |
| `families[].models[].config_path` | str | `config.json` | arch-diff 用的配置文件 |
| `families[].models[].prior_alias` | str? | `null` | 上一版 drop（arch-delta 基线） |
| `families[].models[].quants` | list | `[]` | 量化产物清单（kind/repo/surface） |

环境变量：`DROPBRIEF_CACHE_DIR`（默认 `~/.dropbrief/cache`，15min JSON 缓存）、`DROPBRIEF_SNAPSHOT_DIR`（默认 `~/.dropbrief/snapshots`，用户离线快照）。

## <img src="https://api.iconify.design/tabler:plane.svg?color=%230071E3&width=24" height="22" align="absmiddle" alt=""> 气隙离线模式

信创/政企气隙盒子没有出站，刷不了 reddit/HF/ModelScope。dropbrief 把**预打包快照**作为漏斗：仓库内置 `snapshots/qwen3.8-27b/brief.json`（最新 Qwen drop 的免费公共快照），冷启动 `dropbrief brief --offline qwen3.8-27b` 零网络拿到与联网环境完全相同的简报。联网盒子先跑 `dropbrief brief <model>` 生成快照，再拷进气隙盒子用 `--offline` 读取 —— 气隙用户拿到的是与联网运维一致的决策情报，这是手动 gauntlet 在气隙下结构做不到的。

## <img src="https://api.iconify.design/tabler:components.svg?color=%230071E3&width=24" height="22" align="absmiddle" alt=""> 支持的模型家族

| 家族 | 厂商 | drop | 上一版本（arch 基线） |
| --- | --- | --- | --- |
| qwen3 | 阿里巴巴 | `qwen3.8-27b` / `qwen3.6-27b` | `qwen3.6-27b` |
| glm4 | 智谱 AI | `glm-4.5` / `glm-4` | `glm-4` |
| deepseek | DeepSeek | `deepseek-v3` / `deepseek-v2.5` | `deepseek-v2.5` |
| kimi | 月之暗面 | `kimi-k2` | — |

v0.1 仅 Qwen / GLM / DeepSeek / Kimi（不含 Llama / Mistral）。

## <img src="https://api.iconify.design/tabler:ban.svg?color=%230071E3&width=24" height="22" align="absmiddle" alt=""> 非目标

dropbrief 是**发布前决策简报**，只做下载之前的情报，不做下载之后的活：

- 不下载 / 不拉取模型权重 —— 预下载简报，不是发布器
- 不跑分 / 不 benchmark —— 那是 dropprobe 的活
- 不做 coding-agent 配置 diff —— 那是 dropdiff 的活
- 不做能力回放 —— 那是 regatlas 的活
- v0.1 不做 Web UI / 多用户 / 云同步 / 推送通知
- 不追踪自训练 / 微调模型

## <img src="https://api.iconify.design/tabler:building.svg?color=%230071E3&width=24" height="22" align="absmiddle" alt=""> 付费

商业分拆是显式的：**上线状态 + 量化清单是 OSS 免费**（分析报告判定 30 行爬虫即可答的层）；**arch-delta 情报 + 信创 enterprise 离线 snapshot** 是付费扩展（爬虫答不了的残留价值）。

- **谁先付费**：信创/政企采购 + 企业 MLOps 私有 Qwen/GLM 标准化团队 —— 不是 hobbyist。
- **付费内容**：预构建、预审核的离线决策包（采购级、签名 tarball 进气隙）+ arch-delta 扩展团队席位。
- **定价（估值）**：¥3,000–5,000 / enterprise drop-snapshot（每 drop），或 ¥1,000 / seat / quarter 的 arch-delta 团队版。锚点：采购团队手工搭这套决策包要数天，一次信创误采是六位数损失，<¥5k/drop 是四舍五入。
- **最小 yes path**：免费公共 Qwen snapshot（漏斗）→ 采购 lead 在气隙盒跑 `dropbrief brief --offline` → 看到 arch-delta + worth-switch 判定 → 微信群 DM → 为下一波 GLM-4.5 / DeepSeek-V3 drop 下单付费 enterprise snapshot，14 天对公转账开发票。
- **计费栈**：v0.1 = 对公转账 + 增值税发票（人工；信创/政企 B2G/B2B 不走信用卡 SaaS）。SaaS 计费（微信支付 / LemonSqueezy）留到 v0.3 量起来再说。

不为这个买家假装有 Stripe 流程。

## <img src="https://api.iconify.design/tabler:map-2.svg?color=%230071E3&width=24" height="22" align="absmiddle" alt=""> 路线图

- [x] **m1** — HF+ModelScope+reddit fetcher + 15min JSON 缓存；`dropbrief status` 输出 is-live + 量化清单（伪证测试）
- [ ] **m2** — `dropbrief diff` 架构差分 vs prior（基础 diff 已可用；完整版含 reddit `/comments/1voblcs` 同构判定自动复现）
- [ ] **m3** — `dropbrief brief` 一屏简报 + `--offline`（基础 briefing + 气隙已可用；完整版含 worth-switching 决策模型 + 信创 enterprise 签名 snapshot）
- [ ] **future** — GLM-4.5 / DeepSeek-V3 / Kimi K2 实测数据；多 drop 趋势分析；与 dropdiff 联动

> **Kill 触发器**（mvp_plan §8）：连续 2 个真实 drop 中爬虫单独答 ≥3/4 维 → 杀；下一个真实 drop 简报较手工 reddit 帖省时 <5 分钟 → 杀；30 天 GitHub <50 star 且无信创/采购用户提 issue → 杀。无 kill 触发器的计划会永远发布，这三条可证伪。

## License + Contributing

MIT，详见 [LICENSE](./LICENSE)。提 issue / PR 见 [Issues](https://github.com/SuperMarioYL/dropbrief/issues)。推送后建议设置 repo topics：`gh repo edit --add-topic llm --add-topic qwen --add-topic cli --add-topic xinchuang`。

<p align="center"><sub><a href="./LICENSE">MIT</a> © 2026 SuperMarioYL</sub></p>
