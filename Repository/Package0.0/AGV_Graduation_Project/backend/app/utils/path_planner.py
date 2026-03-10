import heapq

from app.utils.warehouse_map import get_blocked_cells


def _trace_simple_candidate(
    sx: int,
    sy: int,
    ex: int,
    ey: int,
    axis_order: tuple[str, str],
    blocked: set[tuple[int, int]],
):
    path = [{"x": sx, "y": sy}]
    x, y = sx, sy

    for axis in axis_order:
        if axis == "x":
            while x != ex:
                x += 1 if ex > x else -1
                if (x, y) in blocked:
                    return []
                path.append({"x": x, "y": y})
        else:
            while y != ey:
                y += 1 if ey > y else -1
                if (x, y) in blocked:
                    return []
                path.append({"x": x, "y": y})

    return path


def generate_simple_path(
    sx: int,
    sy: int,
    ex: int,
    ey: int,
    grid_cols: int,
    grid_rows: int,
    blocked: set[tuple[int, int]] | None = None,
):
    if blocked is None:
        blocked = set()

    def in_bounds(x: int, y: int):
        return 0 <= x < grid_cols and 0 <= y < grid_rows

    if not in_bounds(sx, sy) or not in_bounds(ex, ey):
        return []

    if (sx, sy) in blocked or (ex, ey) in blocked:
        return []

    if sx == ex and sy == ey:
        return [{"x": sx, "y": sy}]

    for axis_order in (("x", "y"), ("y", "x")):
        path = _trace_simple_candidate(sx, sy, ex, ey, axis_order, blocked)
        if path:
            return path

    return []


def generate_astar_path(
    sx: int,
    sy: int,
    ex: int,
    ey: int,
    grid_cols: int,
    grid_rows: int,
    blocked: set | None = None,
):
    start = (sx, sy)
    goal = (ex, ey)

    if start == goal:
        return [{"x": sx, "y": sy}]

    if blocked is None:
        blocked = set()

    def in_bounds(x: int, y: int):
        return 0 <= x < grid_cols and 0 <= y < grid_rows

    def neighbors(node: tuple[int, int]):
        x, y = node
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if in_bounds(nx, ny) and (nx, ny) not in blocked:
                yield (nx, ny)

    def heuristic(a: tuple[int, int], b: tuple[int, int]):
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    if not in_bounds(*start) or not in_bounds(*goal):
        return []

    if start in blocked or goal in blocked:
        return []

    open_heap = []
    heapq.heappush(open_heap, (0, start))
    came_from: dict[tuple[int, int], tuple[int, int]] = {}
    g_score = {start: 0}

    while open_heap:
        _, current = heapq.heappop(open_heap)
        if current == goal:
            path = [current]
            while current in came_from:
                current = came_from[current]
                path.append(current)
            path.reverse()
            return [{"x": x, "y": y} for x, y in path]

        for neighbor in neighbors(current):
            tentative = g_score[current] + 1
            if neighbor not in g_score or tentative < g_score[neighbor]:
                came_from[neighbor] = current
                g_score[neighbor] = tentative
                f_score = tentative + heuristic(neighbor, goal)
                heapq.heappush(open_heap, (f_score, neighbor))

    return []


def plan_path(
    algorithm: str,
    sx: int,
    sy: int,
    ex: int,
    ey: int,
    grid_cols: int,
    grid_rows: int,
    blocked: set[tuple[int, int]] | None = None,
):
    if blocked is None:
        blocked = get_blocked_cells(grid_cols, grid_rows)

    if algorithm == "astar":
        return generate_astar_path(sx, sy, ex, ey, grid_cols, grid_rows, blocked)

    return generate_simple_path(sx, sy, ex, ey, grid_cols, grid_rows, blocked)
