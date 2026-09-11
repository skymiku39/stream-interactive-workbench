"""Build the static interactive showcase for GitHub Pages."""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil

from stream_interactive.overlays import (
    render_game_overlay_html,
    render_preview_dashboard_html,
)


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "src" / "stream_interactive" / "assets"


def rewrite_asset_paths(html: str, prefix: str) -> str:
    target = f"{prefix.rstrip('/')}/"
    return (
        html.replace('"/assets/', f'"{target}')
        .replace("'/assets/", f"'{target}")
        .replace("url(/assets/", f"url({target}")
    )


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def build(output: Path) -> None:
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    shutil.copytree(ASSETS, output / "assets")

    dashboard = render_preview_dashboard_html(
        static_demo=True,
        asset_prefix="/assets",
        overlay_path="overlay/games/",
    )
    write_text(output / "index.html", rewrite_asset_paths(dashboard, "assets"))

    routes = {
        "overlay/games": "all",
        "overlay/game/bwei": "bwei",
        "overlay/game/slot": "slot",
        "overlay/game/gashapon": "gashapon",
        "overlay/game/card-gacha": "card-gacha",
        "overlay/game/gacha": "card-gacha",
        "overlay/game/wheel": "wheel",
        "overlay/game/coin": "coin",
        "overlay/game/dice": "dice",
        "overlay/game/gamble": "gamble",
        "overlay/hud/counter": "counter",
        "overlay/hud/subathon": "subathon",
        "overlay/hud/cover": "cover",
        "overlay/hud/picker": "picker",
        "overlay/hud/bet": "bet",
        "overlay/hud/music": "music",
        "overlay/hud/trans": "trans",
        "overlay/hud/donation": "donation",
    }
    for route, mode in routes.items():
        html = render_game_overlay_html(
            mode=mode,
            static_demo=True,
            asset_prefix="/assets",
        )
        write_text(output / route / "index.html", rewrite_asset_paths(html, "../../assets"))

    alias = render_preview_dashboard_html(
        static_demo=True,
        asset_prefix="/assets",
        overlay_path="../../overlay/games/",
    )
    for route in ("preview", "overlay/preview", "games/preview"):
        write_text(output / route / "index.html", rewrite_asset_paths(alias, "../../assets"))

    write_text(
        output / "404.html",
        "<!doctype html><meta charset='utf-8'><meta http-equiv='refresh' content='0; url=./'>",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "site")
    args = parser.parse_args()
    build(args.output.resolve())
    print(f"Built GitHub Pages showcase: {args.output.resolve()}")


if __name__ == "__main__":
    main()
