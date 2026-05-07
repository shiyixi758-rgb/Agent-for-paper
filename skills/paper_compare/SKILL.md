---
name: paper_compare
description: Structured side-by-side comparison of 2+ papers with trade-off analysis.
---

# Skill: Paper Comparison

Trigger when the user asks to compare, contrast, or evaluate multiple papers.

## Input Handling

The user provides 2+ papers via titles, arXiv IDs, or URLs.
If only titles are given, find and verify their arXiv pages first.

## Step 1: Collect Facts Per Paper

For each paper, fetch its arXiv abstract page and extract:
- Full title, authors, venue, year
- Core method / approach
- Datasets used for evaluation
- Key metric(s) and reported numbers
- Code availability (look for GitHub link in abstract)

Only include numbers actually read from the paper — never estimate or guess.

## Step 2: Comparison Table

**For architecture/method comparisons**:

| Dimension | Paper A | Paper B | Paper C |
|-----------|---------|---------|---------|
| **Core idea** | | | |
| **Architecture** | | | |
| **Training data** | | | |
| **Venue / Year** | | | |
| **Code** | ✅ / ❌ | | |
| **Key metric** | XX.X% | XX.X% | XX.X% |
| **Benchmark** | | | |

**For survey / chronological comparisons**:

| Paper | Role | Key contribution | Best read when |
|-------|------|-----------------|----------------|

## Step 3: Qualitative Analysis

### Key Differences
- What fundamentally separates these approaches?
- Which design choices explain the performance gap?

### Trade-offs
- Speed vs. quality?
- Complexity vs. generalizability?
- Data requirements vs. accessibility?

### Recommendation
Based on USER.md research context:
- "If your goal is X, prefer Paper A because..."
- "For understanding the field, read in order: C → A → B"

## Save to File

Save the comparison to `papers/compare-[slug].md` in the workspace.
Name the slug from the papers compared, e.g., `compare-hunyuan-vs-wan.md`.

## Quality Rules

- Use "N/A" or "not reported" when data is unavailable — never guess.
- Note when papers evaluate on different test sets (direct comparison may be unfair).
- Flag when one paper is significantly newer (may benefit from stronger base models).
