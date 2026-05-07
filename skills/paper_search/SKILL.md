---
name: paper_search
description: Find latest and foundational papers on any research topic, with verified arXiv links.
---

# Skill: Paper Search

Trigger when the user asks to find, search, or recommend papers on a topic.

## Input Parsing

Extract from the user's request:
- **Topic** (required): e.g., "video generation", "diffusion models", "ViT for video"
- **Category** (optional): "latest" / "foundational/introductory" / "survey" — default: both
- **Time range** (optional): e.g., "2024–2025", "past year" — default: no limit for foundational, last 2 years for latest
- **Venue filter** (optional): e.g., "only CVPR/ICLR" — default: all top venues
- **Count** (optional): how many papers — default: 5 per category

Read USER.md before searching to:
1. Understand the user's research background (avoid over-explaining basics they already know)
2. Filter out papers already in their "Already Read" list
3. Prioritize venues they follow

## Search Strategy

1. **Web search first**: Query `"[topic] arxiv 2024 2025 site:arxiv.org OR site:openreview.net"` for latest; `"[topic] survey" site:arxiv.org` for surveys.
2. **Verify each paper**: Fetch the arXiv abstract page (`https://arxiv.org/abs/[ID]`) to confirm title, authors, and that the URL resolves.
3. **Semantic Scholar**: For finding seminal works by citation count, fetch `https://api.semanticscholar.org/graph/v1/paper/search?query=[topic]&fields=title,authors,year,venue,citationCount,externalIds`.

## Venue Priority (top-tier)

**CV/Video**: CVPR, ICCV, ECCV, NeurIPS, ICML, ICLR
**NLP/Multimodal**: ACL, EMNLP, NAACL, NeurIPS, ICLR
**AI General**: NeurIPS, ICML, ICLR, AAAI, IJCAI
**Preprints**: arXiv (flag as "preprint, not peer-reviewed")

## Output Format

```
### 🔬 Latest Papers ([topic], [year range])

**1. [Paper Title]**
- **Authors**: [First Author] et al.
- **Venue**: [Conference/Journal, Year]
- **Link**: [arXiv or official URL]
- **Contribution**: [One sentence: what specific problem it solves and how]

---

### 📚 Foundational / Must-Read

**1. [Paper Title]**
- **Authors**: [First Author] et al.
- **Venue**: [Conference/Journal, Year]
- **Link**: [arXiv or official URL]
- **Why read first**: [One sentence: why this is foundational]

---

**Suggested reading order**: [Brief path for a newcomer]
```

## Quality Rules

- Never list a paper without a verified link.
- Never fabricate citation counts or venue names.
- Distinguish "published at NeurIPS 2024" from "arXiv preprint 2024" clearly.
- If fewer verified papers are found than requested, return what was verified and note the limitation.
