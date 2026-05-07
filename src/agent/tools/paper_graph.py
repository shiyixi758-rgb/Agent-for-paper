"""Paper evolution graph tools for AgentForPaper.

Builds and queries citation/influence graphs using NetworkX.
Saves interactive HTML visualisations to the local workspace.
"""

from __future__ import annotations

import asyncio
import json
import os
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import httpx
import networkx as nx
from langchain_core.tools import tool

# ── Workspace path ─────────────────────────────────────────────────────────────

def _graphs_dir() -> Path:
    base = Path(os.getenv("WORKSPACE_DIR", Path.home() / ".agentforpaper"))
    d = base / "graphs"
    d.mkdir(parents=True, exist_ok=True)
    return d


# ── arXiv metadata (inline, no extra import) ──────────────────────────────────

_ATOM_NS = "http://www.w3.org/2005/Atom"
_ARXIV_BASE = "https://export.arxiv.org/api/query"
_RATE_DELAY = 0.4
_last_arxiv: float = 0.0
_arxiv_lock: asyncio.Lock | None = None


def _get_arxiv_lock() -> asyncio.Lock:
    global _arxiv_lock
    if _arxiv_lock is None:
        _arxiv_lock = asyncio.Lock()
    return _arxiv_lock


async def _fetch_arxiv_meta(arxiv_ids: list[str]) -> dict[str, dict]:
    """Return metadata dict keyed by bare arXiv ID."""
    global _last_arxiv
    if not arxiv_ids:
        return {}
    async with _get_arxiv_lock():
        gap = _RATE_DELAY - (time.monotonic() - _last_arxiv)
        if gap > 0:
            await asyncio.sleep(gap)
        _last_arxiv = time.monotonic()
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(_ARXIV_BASE, params={
                "id_list": ",".join(arxiv_ids),
                "max_results": len(arxiv_ids),
            })
            resp.raise_for_status()

    root = ET.fromstring(resp.text)
    out: dict[str, dict] = {}
    for entry in root.findall(f"{{{_ATOM_NS}}}entry"):
        raw_id = entry.findtext(f"{{{_ATOM_NS}}}id") or ""
        aid = raw_id.rstrip("/").split("/")[-1].split("v")[0]
        authors = [
            a.findtext(f"{{{_ATOM_NS}}}name") or ""
            for a in entry.findall(f"{{{_ATOM_NS}}}author")
        ]
        pub = entry.findtext(f"{{{_ATOM_NS}}}published") or ""
        out[aid] = {
            "title": (entry.findtext(f"{{{_ATOM_NS}}}title") or "").strip(),
            "year": int(pub[:4]) if len(pub) >= 4 else None,
            "authors": authors[:3],
            "abstract": (entry.findtext(f"{{{_ATOM_NS}}}summary") or "").strip()[:300],
            "url": f"https://arxiv.org/abs/{aid}",
        }
    return out


# ── HTML visualisation ─────────────────────────────────────────────────────────

_YEAR_COLORS: list[tuple[int, str]] = [
    (2026, "#4fc3f7"),
    (2025, "#81d4fa"),
    (2024, "#a5d6a7"),
    (2023, "#fff176"),
    (2022, "#ffcc80"),
    (0,    "#ef9a9a"),
]

_VIS_HTML = """\
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>{title}</title>
  <script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
  <style>
    body {{ margin:0; background:#0f1117; font-family:sans-serif; color:#e0e0e0; }}
    #graph {{ width:100vw; height:90vh; }}
    #info {{ padding:8px 16px; font-size:13px; color:#888; }}
  </style>
</head>
<body>
  <div id="info">{title} | {node_count} papers | {edge_count} links
    | <a href="#" style="color:#4fc3f7" onclick="network.fit()">Reset view</a></div>
  <div id="graph"></div>
  <script>
    const nodes = new vis.DataSet({nodes_json});
    const edges = new vis.DataSet({edges_json});
    const network = new vis.Network(document.getElementById("graph"), {{nodes, edges}}, {{
      nodes:{{ shape:"dot", font:{{color:"#e0e0e0",size:12}}, borderWidth:1 }},
      edges:{{ arrows:{{to:{{enabled:true,scaleFactor:0.5}}}},
               color:{{color:"#555",highlight:"#4fc3f7"}},
               smooth:{{type:"curvedCW",roundness:0.15}} }},
      physics:{{ barnesHut:{{gravitationalConstant:-8000,springLength:120}} }},
      interaction:{{ hover:true, tooltipDelay:100 }},
    }});
  </script>
</body>
</html>
"""


def _year_color(year: int | None) -> str:
    y = year or 0
    for threshold, color in _YEAR_COLORS:
        if y >= threshold:
            return color
    return _YEAR_COLORS[-1][1]


def _graph_to_html(G: nx.DiGraph, title: str) -> str:
    vis_nodes = []
    for nid, data in G.nodes(data=True):
        label = data.get("title", nid)
        if len(label) > 40:
            label = label[:37] + "…"
        tooltip = (
            f"<b>{data.get('title','')}</b><br>"
            f"{', '.join(data.get('authors', []))}<br>"
            f"arXiv {data.get('arxiv_id','')} ({data.get('year','?')})<br>"
            f"<a href='{data.get('url','')}' target='_blank'>Open ↗</a>"
        )
        vis_nodes.append({
            "id": nid, "label": label, "title": tooltip,
            "color": _year_color(data.get("year")),
            "size": 10,
        })
    vis_edges = [{"from": u, "to": v, "id": f"{u}__{v}"} for u, v in G.edges()]
    return _VIS_HTML.format(
        title=title,
        node_count=G.number_of_nodes(),
        edge_count=G.number_of_edges(),
        nodes_json=json.dumps(vis_nodes, ensure_ascii=False),
        edges_json=json.dumps(vis_edges, ensure_ascii=False),
    )


# ── Graph persistence ──────────────────────────────────────────────────────────

def _save_graph(G: nx.DiGraph, name: str) -> dict[str, str]:
    base = _graphs_dir() / name
    json_path = base.with_suffix(".json")
    html_path = base.with_suffix(".html")
    json_path.write_text(
        json.dumps(nx.node_link_data(G), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    html_path.write_text(_graph_to_html(G, name), encoding="utf-8")
    return {"json": str(json_path), "html": str(html_path)}


def _load_graph(name: str) -> nx.DiGraph | None:
    p = (_graphs_dir() / name).with_suffix(".json")
    if not p.exists():
        return None
    return nx.node_link_graph(json.loads(p.read_text(encoding="utf-8")), directed=True)


# ── LangChain Tools ────────────────────────────────────────────────────────────

@tool
async def build_graph_from_knowledge(
    paper_ids: list[str],
    edges: list[list[str]],
    graph_name: str,
) -> str:
    """Build a research paper evolution graph from known paper relationships.

    PREFERRED method — uses arXiv for metadata, no external citation API needed.

    Args:
        paper_ids: List of arXiv IDs, e.g. ['2412.03603', '2212.09748'].
        edges: List of [from_id, to_id] pairs where from CITES/BUILDS ON to.
               Example: [['2412.03603', '2212.09748']] means HunyuanVideo builds on DiT.
        graph_name: Name for the saved graph (no extension), e.g. 'video-gen-2025'.

    Returns:
        Summary of the built graph with file paths for viewing.
    """
    clean_ids = [p.lower().removeprefix("arxiv:").strip() for p in paper_ids]

    try:
        meta = await _fetch_arxiv_meta(clean_ids)
    except Exception as exc:
        meta = {}
        # continue without metadata — nodes will show arXiv IDs

    G: nx.DiGraph = nx.DiGraph()

    for pid in clean_ids:
        info = meta.get(pid, {})
        nid = f"arxiv:{pid}"
        G.add_node(nid,
            id=nid, arxiv_id=pid,
            title=info.get("title") or pid,
            year=info.get("year"),
            authors=info.get("authors") or [],
            abstract=info.get("abstract") or "",
            url=info.get("url") or f"https://arxiv.org/abs/{pid}",
        )

    for edge in edges:
        if len(edge) < 2:
            continue
        from_raw, to_raw = edge[0], edge[1]
        label = edge[2] if len(edge) > 2 else "cites"
        from_id = "arxiv:" + from_raw.lower().removeprefix("arxiv:")
        to_id   = "arxiv:" + to_raw.lower().removeprefix("arxiv:")
        for nid, raw in [(from_id, from_raw), (to_id, to_raw)]:
            if nid not in G:
                bare = raw.lower().removeprefix("arxiv:")
                info = meta.get(bare, {})
                G.add_node(nid,
                    id=nid, arxiv_id=bare,
                    title=info.get("title") or bare,
                    year=info.get("year"),
                    authors=info.get("authors") or [],
                    abstract=info.get("abstract") or "",
                    url=f"https://arxiv.org/abs/{bare}",
                )
        G.add_edge(from_id, to_id, type=label)

    if G.number_of_nodes() == 0:
        return "Error: no papers added to graph."

    paths = _save_graph(G, graph_name)

    lines = [
        f"Graph '{graph_name}' built successfully.",
        f"  Papers (nodes): {G.number_of_nodes()}",
        f"  Citation links (edges): {G.number_of_edges()}",
        f"  HTML visualization: {paths['html']}",
        f"  JSON data: {paths['json']}",
        "",
        "Papers in graph (oldest → newest):",
    ]
    for nid, data in sorted(G.nodes(data=True), key=lambda x: x[1].get("year") or 0):
        lines.append(f"  [{data.get('year','?')}] {data.get('title', nid)[:65]}")
    if not meta:
        lines.append("\nWarning: arXiv metadata fetch failed — nodes show arXiv IDs only.")
    return "\n".join(lines)


@tool
def query_graph(
    graph_name: str,
    query_type: str,
    source_id: str = "",
    target_id: str = "",
) -> str:
    """Query a saved paper graph for analysis.

    Args:
        graph_name: Name of the saved graph to query.
        query_type: One of: 'summary' | 'influential' | 'ancestors' | 'descendants' | 'path'.
        source_id: arXiv node ID (e.g. 'arxiv:2412.03603') for ancestors/descendants/path.
        target_id: Target arXiv node ID for 'path' query type.

    Returns:
        Analysis results as formatted text.
    """
    G = _load_graph(graph_name)
    if G is None:
        return f"Graph '{graph_name}' not found. Build it first with build_graph_from_knowledge."

    if query_type == "summary":
        years = [d.get("year") for _, d in G.nodes(data=True) if d.get("year")]
        wccs = list(nx.weakly_connected_components(G))
        return "\n".join([
            f"Graph: {graph_name}",
            f"Papers (nodes): {G.number_of_nodes()}",
            f"Citation links (edges): {G.number_of_edges()}",
            f"Year range: {min(years) if years else '?'} – {max(years) if years else '?'}",
            f"Connected components: {len(wccs)}",
            f"Density: {nx.density(G):.4f}",
        ])

    if query_type == "influential":
        scores = nx.pagerank(G, alpha=0.85)
        top = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:10]
        lines = [f"Top 10 most influential papers in '{graph_name}' (PageRank):"]
        for nid, score in top:
            data = G.nodes[nid]
            lines.append(
                f"  [{data.get('year','?')}] {data.get('title', nid)[:60]}"
                f"  score={score:.4f}  {data.get('url','')}"
            )
        return "\n".join(lines)

    if query_type == "ancestors" and source_id:
        if source_id not in G:
            return f"Node '{source_id}' not in graph '{graph_name}'."
        ancestors = nx.ancestors(G, source_id)
        lines = [f"Papers that '{source_id}' builds on:"]
        for nid in sorted(ancestors, key=lambda n: G.nodes[n].get("year") or 0):
            data = G.nodes[nid]
            lines.append(f"  [{data.get('year','?')}] {data.get('title', nid)[:70]}")
        return "\n".join(lines)

    if query_type == "descendants" and source_id:
        if source_id not in G:
            return f"Node '{source_id}' not in graph '{graph_name}'."
        descs = nx.descendants(G, source_id)
        lines = [f"Papers citing '{source_id}':"]
        for nid in sorted(descs, key=lambda n: G.nodes[n].get("year") or 0, reverse=True):
            data = G.nodes[nid]
            lines.append(f"  [{data.get('year','?')}] {data.get('title', nid)[:70]}")
        return "\n".join(lines)

    if query_type == "path" and source_id and target_id:
        if source_id not in G:
            return f"Node '{source_id}' not in graph."
        if target_id not in G:
            return f"Node '{target_id}' not in graph."
        try:
            path = nx.shortest_path(G, source_id, target_id)
            lines = [f"Shortest citation path ({len(path)-1} hops):"]
            for i, nid in enumerate(path):
                data = G.nodes[nid]
                prefix = "→ " if i > 0 else "  "
                lines.append(f"{prefix}[{data.get('year','?')}] {data.get('title', nid)[:70]}")
            return "\n".join(lines)
        except nx.NetworkXNoPath:
            return f"No path found between '{source_id}' and '{target_id}'."

    return f"Unknown query_type '{query_type}'. Use: summary | influential | ancestors | descendants | path."


@tool
def list_graphs() -> str:
    """List all saved paper evolution graphs.

    Returns:
        Names and sizes of all saved graphs.
    """
    graphs = sorted(_graphs_dir().glob("*.json"))
    if not graphs:
        return "No saved graphs yet. Use build_graph_from_knowledge to create one."
    lines = [f"Saved graphs in {_graphs_dir()}:"]
    for g in graphs:
        size_kb = g.stat().st_size // 1024
        lines.append(f"  - {g.stem}  ({size_kb} KB)  HTML: {g.with_suffix('.html')}")
    return "\n".join(lines)
