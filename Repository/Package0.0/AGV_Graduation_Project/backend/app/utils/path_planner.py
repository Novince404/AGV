import heapq


def generate_simple_path(sx: int, sy: int, ex: int, ey: int):
    path = []
    x, y = sx, sy

    while x != ex or y != ey:
        path.append({"x": x, "y": y})

        if x < ex:
            x += 1
        elif x > ex:
            x -= 1
        elif y < ey:
            y += 1
        elif y > ey:
            y -= 1

    path.append({"x": ex, "y": ey})
    return path


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
):
    if algorithm == "astar":
        return generate_astar_path(sx, sy, ex, ey, grid_cols, grid_rows)

    return generate_simple_path(sx, sy, ex, ey)
