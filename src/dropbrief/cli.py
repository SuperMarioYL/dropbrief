"""dropbrief CLI — three subcommands over the four-question gauntlet.

* ``dropbrief status <model>``  — m1: is-it-live + which-quant-exists (cached 15 min).
* ``dropbrief diff <model>``    — m2: config.json arch-delta vs the prior drop.
* ``dropbrief brief <model>``  — m3: one-screen decision briefing; ``--offline``
  reads a shipped snapshot for air-gapped 信创 use.

Run ``dropbrief --help`` for the surface; each subcommand has its own help.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from . import registry as reg
from . import snapshot as snap
from .archdiff import compute_arch_delta, reproduce_reddit_finding, summarize
from .briefing import build_brief, render_briefing, write_briefing
from .fetch import Fetcher
from .snapshot import load_snapshot

app = typer.Typer(
    name="dropbrief",
    help="国产大模型发布决策简报 — 一条命令回答上线没/架构改没/哪个量化能用/值不值得换。",
    no_args_is_help=True,
    add_completion=False,
    pretty_exceptions_enable=False,
)
console = Console()


def _version_callback(value: bool) -> None:
    if value:
        from . import __version__

        console.print(f"dropbrief {__version__}")
        raise typer.Exit()


@app.callback()
def _root(
    version: bool = typer.Option(
        False,
        "--version",
        help="打印 dropbrief 版本并退出。",
        callback=_version_callback,
        is_eager=True,
    ),
) -> None:
    """dropbrief — 国产大模型发布决策简报工具。"""


def _resolve(name: str) -> reg.ModelRecord:
    try:
        return reg.load_default().resolve(name)
    except KeyError as exc:
        console.print(f"[red]error:[/red] {exc}")
        raise typer.Exit(code=2) from exc


@app.command(help="m1 — 打印上线状态 + 量化清单（15min 缓存）。即伪证测试：30 行 httpx 能否答上线+量化。")
def status(model: str) -> None:
    record = _resolve(model)
    fetcher = Fetcher()
    live = fetcher.fetch_live_status(record)
    table = Table(title=f"dropbrief status — {record.model_id}", show_lines=False)
    table.add_column("镜像源", style="cyan")
    table.add_column("仓库", style="white")
    table.add_column("状态", style="bold")
    table.add_column("说明", style="dim")
    for r in live.repos:
        ok = "[green]✓ live[/green]" if r.live else f"[red]✗ {r.http_status or 'down'}[/red]"
        table.add_row(r.surface, r.repo, ok, r.note)
    console.print(table)

    q = live.quant_inventory
    if q:
        qtable = Table(title="可用量化")
        qtable.add_column("类型", style="magenta")
        qtable.add_column("仓库", style="white")
        qtable.add_column("镜像", style="cyan")
        qtable.add_column("在线", style="bold")
        for a in q:
            ok = "[green]✓[/green]" if a.live else "[red]✗[/red]"
            qtable.add_row(a.kind.upper(), a.repo, a.surface, ok)
        console.print(qtable)
    else:
        console.print("[dim]注册表未声明量化产物。[/dim]")

    if live.cache_hit:
        console.print("[dim]（命中 15min 缓存，未发起网络请求）[/dim]")


@app.command(help="m2 — 打印 config.json 相对上一版本的架构变更摘要。")
def diff(model: str) -> None:
    record = _resolve(model)
    registry = reg.load_default()
    prior = registry.prior(record)
    if prior is None:
        console.print(
            f"[yellow]注意：[/yellow]{record.alias} 没有注册的前一版本（{record.prior_alias}），无法计算 arch-delta。"
        )
        raise typer.Exit(code=0)

    fetcher = Fetcher()
    try:
        cur_cfg = fetcher.fetch_config(record)
        prior_cfg = fetcher.fetch_config(prior)
    except Exception as exc:  # noqa: BLE001 — surface any fetch failure cleanly
        console.print(f"[red]抓取 config.json 失败：[/red] {exc}")
        console.print("[dim]提示：离线环境可用 `dropbrief brief --offline` 读取已打包快照。[/dim]")
        raise typer.Exit(code=1) from exc

    delta = compute_arch_delta(
        cur_cfg, prior_cfg, model_id=record.model_id, prior_model_id=prior.model_id
    )
    console.print(summarize(delta))
    citation = reproduce_reddit_finding(delta)
    if citation:
        console.print(f"[dim]{citation}[/dim]")


@app.command(help="m3 — 生成一屏决策简报 (上线/架构/量化/是否值得切换)，写入 dropbrief-<model>-<date>.md。")
def brief(
    model: str,
    offline: bool = typer.Option(
        False, "--offline", help="气隙模式：读取已打包快照，零网络出站。"
    ),
    save_snapshot: bool = typer.Option(
        False,
        "--save-snapshot",
        help="在线模式下同时把 DropBrief JSON 写入默认快照目录，供气隙机器 --offline 读取。",
    ),
    out: Path = typer.Option(Path("."), "--out", "-o", help="简报输出目录。"),
) -> None:
    if offline and save_snapshot:
        console.print(
            "[red]error:[/red]--save-snapshot 只用于在线模式；--offline 本身就在读取快照。"
        )
        raise typer.Exit(code=2)

    registry = reg.load_default()
    record = _resolve(model)
    family = registry.family_of(record)

    if offline:
        try:
            brief_obj = load_snapshot(record.alias)
        except (FileNotFoundError, ValueError) as exc:
            console.print(f"[red]error:[/red] {exc}")
            raise typer.Exit(code=1) from exc
    else:
        fetcher = Fetcher()
        prior = registry.prior(record)
        if prior is None:
            console.print(
                f"[red]error:[/red]{record.alias} 没有前一版本，无法在线生成 briefing；"
                f"试 `dropbrief brief --offline {record.alias}` 读取已打包快照。"
            )
            raise typer.Exit(code=1)
        try:
            live = fetcher.fetch_live_status(record)
            cur_cfg = fetcher.fetch_config(record)
            prior_cfg = fetcher.fetch_config(prior)
        except Exception as exc:  # noqa: BLE001
            console.print(f"[red]在线抓取失败：[/red] {exc}")
            console.print(
                f"[dim]提示：离线可用 `dropbrief brief --offline {record.alias}`。[/dim]"
            )
            raise typer.Exit(code=1) from exc
        delta = compute_arch_delta(
            cur_cfg, prior_cfg, model_id=record.model_id, prior_model_id=prior.model_id
        )
        brief_obj = build_brief(record, live, delta, family)

    if save_snapshot:
        snap_path = snap.save_snapshot(
            brief_obj, record.alias, snapshot_dir=snap.DEFAULT_SNAPSHOT_DIR
        )
        console.print(f"[green]✓[/green] 快照已写入：[bold]{snap_path}[/bold]")

    path = write_briefing(brief_obj, out_dir=out)
    console.print(f"[green]✓[/green] 简报已写入：[bold]{path}[/bold]")
    console.print()
    console.print(render_briefing(brief_obj))


@app.command(help="列出注册表支持的全部模型家族。")
def families() -> None:
    table = Table(title="dropbrief 支持的模型家族")
    table.add_column("家族", style="cyan")
    table.add_column("厂商", style="white")
    table.add_column("drop", style="magenta")
    table.add_column("前一版本", style="dim")
    for fam in reg.load_default().families():
        for m in fam.models:
            table.add_row(
                fam.family,
                fam.vendor,
                m.alias,
                m.prior_alias or "—",
            )
    console.print(table)


@app.command(help="显示 dropbrief 自身的版本与缓存目录。")
def version() -> None:
    from . import __version__
    from .fetch import DEFAULT_CACHE_DIR
    from .snapshot import DEFAULT_SNAPSHOT_DIR

    console.print(f"dropbrief {__version__}")
    console.print(f"cache:    {DEFAULT_CACHE_DIR}")
    console.print(f"snapshots: {DEFAULT_SNAPSHOT_DIR}")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
