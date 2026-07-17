from __future__ import annotations

from app.models.tracked_model import TrackedModel


class MapTopologyNode(TrackedModel):
    key: str
    x: int
    y: int
    label: str | None = None
    node_type: str = "waypoint"
    capacity: int = 1


class MapTopologyEdge(TrackedModel):
    key: str
    source: str
    target: str
    direction: str = "bidirectional"
    lane_type: str = "main"
    weight: float = 1.0
    speed_multiplier: float = 1.0


class MapTopology(TrackedModel):
    topology_version: int = 1
    nodes: list[MapTopologyNode] = []
    edges: list[MapTopologyEdge] = []
    stations: list[str] = []
    parking_nodes: list[str] = []
    charge_nodes: list[str] = []

    def bind_on_change(self, callback):
        super().bind_on_change(callback)
        for node in self.nodes:
            if hasattr(node, "bind_on_change"):
                node.bind_on_change(self._notify_change)
        for edge in self.edges:
            if hasattr(edge, "bind_on_change"):
                edge.bind_on_change(self._notify_change)
        return self
