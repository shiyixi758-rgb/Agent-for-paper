---
name: evolution_graph
description: Build and visualize a research paper evolution graph showing citation/influence relationships between papers.
---

# Skill: Research Evolution Graph

Use the `mcp_paper_graph_paper_graph` tool to build citation graphs that show
how research ideas evolved over time.

## When to use

- User asks: "show how these papers are related", "build a citation graph for X"
- User wants to understand a research lineage or identify seminal works
- User wants to visualize the influence structure of a field

## Tool name

`mcp_paper_graph_paper_graph`

---

## PREFERRED: build_from_knowledge (always works, no rate limits)

Use this when you know (or can infer from your training knowledge) the key papers
and their relationships. This uses arXiv for metadata and requires NO external
citation API — so it **never hits rate limits**.

```
mcp_paper_graph_paper_graph(
    action="build_from_knowledge",
    graph_name="video-gen-2025",
    paper_ids=[
        "1503.03585",   # NCSN (score-based)
        "2006.11239",   # DDPM
        "2112.10752",   # LDM (Stable Diffusion)
        "2212.09748",   # DiT
        "2403.03206",   # SD3 / Rectified Flow
        "2412.03603",   # HunyuanVideo
        "2503.20314",   # Wan2.1
    ],
    edges=[
        ["2006.11239", "1503.03585"],   # DDPM builds on NCSN
        ["2112.10752", "2006.11239"],   # LDM builds on DDPM
        ["2212.09748", "2112.10752"],   # DiT builds on LDM
        ["2403.03206", "2212.09748"],   # SD3 builds on DiT
        ["2403.03206", "2112.10752"],   # SD3 also on LDM
        ["2412.03603", "2212.09748"],   # HunyuanVideo on DiT
        ["2412.03603", "2403.03206"],   # HunyuanVideo on SD3
        ["2503.20314", "2412.03603"],   # Wan2.1 on HunyuanVideo
        ["2503.20314", "2212.09748"],   # Wan2.1 on DiT
    ]
)
```

**Edge direction**: `[from_id, to_id]` means `from` CITES or BUILDS ON `to`
(from = newer paper, to = older/foundational paper).

**How to determine edges**: Use your training knowledge of the field.
Check each paper's abstract/introduction for "based on", "following", "building on",
or explicit citations to identify which papers directly influenced others.

---

## Fallback: build (auto-fetches citations, may hit rate limits)

Only use if you don't know the paper relationships and need to discover them automatically.

```
mcp_paper_graph_paper_graph(
    action="build",
    paper_ids=["2412.03603", "2503.20314"],
    graph_name="video-gen-2025",
    depth=1,
    direction="references",
    max_neighbors=5
)
```

⚠️ This fetches from external citation APIs and **may hit rate limits** for recent arXiv papers.
If it fails, switch to `build_from_knowledge` instead.

---

## Explore and query the graph

After building, run queries on the saved graph:

```
# Graph statistics
mcp_paper_graph_paper_graph(action="query", graph_name="video-gen-2025", query_type="summary")

# Most influential papers (PageRank)
mcp_paper_graph_paper_graph(action="query", graph_name="video-gen-2025", query_type="influential")

# What does HunyuanVideo build on?
mcp_paper_graph_paper_graph(action="query", graph_name="video-gen-2025",
    query_type="ancestors", source_id="arxiv:2412.03603")

# Citation path between two papers
mcp_paper_graph_paper_graph(action="query", graph_name="video-gen-2025",
    query_type="path", source_id="arxiv:2503.20314", target_id="arxiv:1503.03585")
```

## Add more papers

```
mcp_paper_graph_paper_graph(
    action="build_from_knowledge",
    graph_name="video-gen-2025",
    paper_ids=["2302.05543"],   # new paper to add
    edges=[["2412.03603", "2302.05543"]]
)
```

## List saved graphs

```
mcp_paper_graph_paper_graph(action="list")
```

---

## After building

1. Report stats: number of papers (nodes), edges, year range.
2. Tell the user: "Open `~/.nanobot/workspace/papers/graphs/<name>.html` in your browser to see the interactive visualization. Node color = year (blue=newest, red=oldest). Node size = citation count."
3. Show top influential papers from `query_type="influential"`.
4. Offer to find citation paths between specific papers.

## Error handling

- "Paper not found" → wrong arXiv ID, search with `web_search` first.
- Rate limit error on `build` → switch to `build_from_knowledge` with your knowledge of the paper relationships.
- arXiv fetch failed → graph is still built, but nodes show IDs instead of titles.
