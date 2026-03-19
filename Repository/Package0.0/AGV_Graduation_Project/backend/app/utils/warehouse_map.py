from __future__ import annotations

from app.repositories.map_repository import get_layout_state as get_runtime_layout_state
from app.repositories.map_repository import set_layout_state as persist_runtime_layout_state


DEFAULT_GRID_COLS = 10
DEFAULT_GRID_ROWS = 8
DEFAULT_MAP_PROFILE_KEY = "warehouse_demo_10x8"

# Fixed shelf layout for the current warehouse demo map.
DEFAULT_BLOCKED_CELLS = {
    (3, 0),
    (3, 1),
    (3, 2),
    (3, 4),
    (3, 5),
    (3, 6),
    (3, 7),
    (6, 0),
    (6, 1),
    (6, 3),
    (6, 4),
    (6, 5),
    (6, 6),
    (6, 7),
}

DEFAULT_MAP_PRESETS = {
    "default_shelves": {
        "name": {
            "zh": "默认货架",
            "ja": "標準棚配置",
            "en": "Default Shelves",
        },
        "description": {
            "zh": "两列货架，中间保留关键通道，适合基础算法对比。",
            "ja": "2 列の棚と通路を保つ標準配置で、基本的なアルゴリズム比較に適しています。",
            "en": "Two shelf columns with corridor gaps for baseline algorithm comparison.",
        },
        "cells": DEFAULT_BLOCKED_CELLS,
    },
    "central_block": {
        "name": {
            "zh": "中心库区",
            "ja": "中央ブロック",
            "en": "Central Block",
        },
        "description": {
            "zh": "中部形成连续障碍，适合验证绕行能力。",
            "ja": "中央に連続障害を配置し、迂回性能の検証に適しています。",
            "en": "A central obstacle cluster for testing detour capability.",
        },
        "cells": {
            (4, 1),
            (4, 2),
            (4, 3),
            (4, 4),
            (4, 5),
            (5, 1),
            (5, 2),
            (5, 3),
            (5, 4),
            (5, 5),
        },
    },
    "zigzag_aisles": {
        "name": {
            "zh": "曲折通道",
            "ja": "ジグザグ通路",
            "en": "Zigzag Aisles",
        },
        "description": {
            "zh": "形成交错通道，适合测试多拐点路径规划。",
            "ja": "交差する通路を形成し、多折れ経路の計画検証に適しています。",
            "en": "Interleaved aisles suited for multi-turn path planning tests.",
        },
        "cells": {
            (2, 0),
            (2, 1),
            (2, 2),
            (2, 4),
            (2, 5),
            (2, 6),
            (4, 1),
            (4, 2),
            (4, 3),
            (4, 5),
            (4, 6),
            (4, 7),
            (7, 0),
            (7, 1),
            (7, 3),
            (7, 4),
            (7, 5),
            (7, 7),
        },
    },
}

DEFAULT_MAP_PROFILES = {
    DEFAULT_MAP_PROFILE_KEY: {
        "name": {
            "zh": "标准演示仓库",
            "ja": "標準デモ倉庫",
            "en": "Standard Demo Warehouse",
        },
        "description": {
            "zh": "当前毕业设计默认使用的 10 x 8 演示地图方案，后续模块 4 将在此基础上扩展动态地图尺寸。",
            "ja": "現行の卒業設計で既定使用している 10 x 8 のデモ用マップ構成です。後続のモジュール 4 で動的サイズ拡張を行います。",
            "en": "The default 10 x 8 demo warehouse profile used by the current project. Dynamic map sizing will build on top of this in module 4.",
        },
        "grid_cols": DEFAULT_GRID_COLS,
        "grid_rows": DEFAULT_GRID_ROWS,
        "custom": False,
    }
}


def _normalize_cells(cells, grid_cols: int, grid_rows: int) -> set[tuple[int, int]]:
    normalized = set()
    for cell in cells:
        x, y = cell
        if 0 <= x < grid_cols and 0 <= y < grid_rows:
            normalized.add((int(x), int(y)))
    return normalized


def get_default_blocked_cells(
    grid_cols: int = DEFAULT_GRID_COLS, grid_rows: int = DEFAULT_GRID_ROWS
) -> set[tuple[int, int]]:
    return _normalize_cells(DEFAULT_BLOCKED_CELLS, grid_cols, grid_rows)


def get_map_layout_state() -> dict[str, object]:
    return get_runtime_layout_state(
        DEFAULT_GRID_COLS,
        DEFAULT_GRID_ROWS,
        get_default_blocked_cells(),
    )


def get_current_grid_size() -> tuple[int, int]:
    state = get_map_layout_state()
    return int(state["grid_cols"]), int(state["grid_rows"])


def get_blocked_cells(grid_cols: int = DEFAULT_GRID_COLS, grid_rows: int = DEFAULT_GRID_ROWS) -> set[tuple[int, int]]:
    state = get_map_layout_state()
    return _normalize_cells(state["blocked_cells"], grid_cols, grid_rows)


def set_blocked_cells(
    cells: set[tuple[int, int]] | list[tuple[int, int]],
    grid_cols: int = DEFAULT_GRID_COLS,
    grid_rows: int = DEFAULT_GRID_ROWS,
) -> set[tuple[int, int]]:
    normalized = _normalize_cells(cells, grid_cols, grid_rows)
    updated = persist_runtime_layout_state(
        normalized,
        grid_cols,
        grid_rows,
        DEFAULT_GRID_COLS,
        DEFAULT_GRID_ROWS,
        get_default_blocked_cells(),
    )
    return _normalize_cells(updated["blocked_cells"], grid_cols, grid_rows)


def reset_blocked_cells(
    grid_cols: int = DEFAULT_GRID_COLS, grid_rows: int = DEFAULT_GRID_ROWS
) -> set[tuple[int, int]]:
    return set_blocked_cells(get_default_blocked_cells(grid_cols, grid_rows), grid_cols, grid_rows)


def get_map_preset_cells(
    preset_key: str,
    grid_cols: int = DEFAULT_GRID_COLS,
    grid_rows: int = DEFAULT_GRID_ROWS,
) -> set[tuple[int, int]]:
    preset = DEFAULT_MAP_PRESETS.get(preset_key)
    if not preset:
        raise KeyError(preset_key)
    return _normalize_cells(preset["cells"], grid_cols, grid_rows)


def apply_map_preset(
    preset_key: str,
    grid_cols: int = DEFAULT_GRID_COLS,
    grid_rows: int = DEFAULT_GRID_ROWS,
) -> set[tuple[int, int]]:
    return set_blocked_cells(get_map_preset_cells(preset_key, grid_cols, grid_rows), grid_cols, grid_rows)


def get_blocked_cell_payload(
    grid_cols: int = DEFAULT_GRID_COLS, grid_rows: int = DEFAULT_GRID_ROWS
) -> list[dict[str, int]]:
    return [{"x": x, "y": y} for x, y in sorted(get_blocked_cells(grid_cols, grid_rows))]


def get_map_presets_payload(
    grid_cols: int = DEFAULT_GRID_COLS, grid_rows: int = DEFAULT_GRID_ROWS
) -> list[dict]:
    payload = []
    for key, preset in DEFAULT_MAP_PRESETS.items():
        cells = _normalize_cells(preset["cells"], grid_cols, grid_rows)
        payload.append(
            build_map_preset_payload(
                key=key,
                name=preset["name"],
                description=preset["description"],
                cells=cells,
                custom=False,
                deletable=False,
                grid_cols=grid_cols,
                grid_rows=grid_rows,
                profile_key=DEFAULT_MAP_PROFILE_KEY,
            )
        )
    return payload


def build_map_profile_payload(
    key: str,
    name,
    description,
    grid_cols: int,
    grid_rows: int,
    *,
    custom: bool,
    editable: bool,
) -> dict:
    return {
        "key": key,
        "name": name,
        "description": description,
        "grid_cols": int(grid_cols),
        "grid_rows": int(grid_rows),
        "custom": custom,
        "editable": editable,
    }


def get_map_profiles_payload() -> list[dict]:
    payload = []
    for key, profile in DEFAULT_MAP_PROFILES.items():
        payload.append(
            build_map_profile_payload(
                key=key,
                name=profile["name"],
                description=profile["description"],
                grid_cols=int(profile["grid_cols"]),
                grid_rows=int(profile["grid_rows"]),
                custom=bool(profile.get("custom", False)),
                editable=False,
            )
        )
    return payload


def get_current_map_profile_payload(
    grid_cols: int = DEFAULT_GRID_COLS,
    grid_rows: int = DEFAULT_GRID_ROWS,
) -> dict:
    for key, profile in DEFAULT_MAP_PROFILES.items():
        if int(profile["grid_cols"]) == int(grid_cols) and int(profile["grid_rows"]) == int(grid_rows):
            return build_map_profile_payload(
                key=key,
                name=profile["name"],
                description=profile["description"],
                grid_cols=grid_cols,
                grid_rows=grid_rows,
                custom=bool(profile.get("custom", False)),
                editable=False,
            )

    return build_map_profile_payload(
        key=f"runtime_{int(grid_cols)}x{int(grid_rows)}",
        name={
            "zh": "运行时地图方案",
            "ja": "実行時マップ構成",
            "en": "Runtime Map Profile",
        },
        description={
            "zh": "当前运行中的地图尺寸未匹配到内置方案，后续可作为自定义地图方案的入口。",
            "ja": "現在の実行時マップサイズは組み込みプロファイルに一致しておらず、将来のカスタムマップ構成の入口として扱います。",
            "en": "The current runtime map size does not match a built-in profile and can later become the entry point for custom map schemes.",
        },
        grid_cols=grid_cols,
        grid_rows=grid_rows,
        custom=True,
        editable=False,
    )


def build_map_preset_payload(
    key: str,
    name,
    description,
    cells: set[tuple[int, int]],
    custom: bool,
    deletable: bool,
    grid_cols: int = DEFAULT_GRID_COLS,
    grid_rows: int = DEFAULT_GRID_ROWS,
    profile_key: str | None = DEFAULT_MAP_PROFILE_KEY,
) -> dict:
    return {
        "key": key,
        "name": name,
        "description": description,
        "blocked_count": len(cells),
        "blocked_cells": [{"x": x, "y": y} for x, y in sorted(cells)],
        "custom": custom,
        "deletable": deletable,
        "grid_cols": int(grid_cols),
        "grid_rows": int(grid_rows),
        "profile_key": profile_key,
    }
