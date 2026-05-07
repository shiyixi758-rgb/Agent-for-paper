---
name: paper_analyze
description: Deep-dive analysis of a single paper — problem, method, results, limitations — saved to a local file.
---

# Skill: Paper Analysis

Trigger when the user asks to analyze, explain, summarize, or deep-dive into a specific paper.

## Input Handling

The user may provide:
- An arXiv ID (e.g., `2412.03555`)
- An arXiv URL (`https://arxiv.org/abs/2412.03555`)
- A paper title (search for it first via web search)
- A PDF file attachment (read with `read_file`)

If only a title is given, find the arXiv ID via web search first.

## Fetching the Paper

1. Fetch the arXiv abstract page: `https://arxiv.org/abs/[ID]`
2. Extract: full title, authors, submission date, abstract, subject categories.
3. For section-level content, try the HTML version: `https://arxiv.org/html/[ID]`
   (Introduction, Method, Experiments are readable without parsing a PDF)
4. If HTML is unavailable, note that section-level details are limited to the abstract.

## Analysis Structure

Always produce this exact structure. Adapt depth to user request ("brief" vs "in-depth").

```
## 📄 [Paper Title]

**Authors**: [Author list]
**Venue**: [Conference/Journal, Year] or [arXiv preprint, Date]
**Link**: [arXiv URL]

---

### Problem & Motivation
What specific problem does this paper address? Why does it matter?
What are the limitations of prior work that motivated this paper?

### Key Idea / Method
What is the core technical contribution?
Describe the approach in plain language first, then add technical details.
Include: architecture overview, training objective, key design choices.

### Main Contributions
- Contribution 1
- Contribution 2
- ...

### Experiments & Results
Which datasets were used?
What baselines were compared against?
Key quantitative results (copy actual numbers from the paper).
What do ablation studies show?

### Limitations & Future Work
What does the paper itself acknowledge as limitations?
What open questions remain?

### My Assessment
Is this work incremental or a significant advance?
Who should read this paper (required background, use case)?
How does it relate to other papers in the field?
```

## Save to File

**After producing the analysis, always save it to a file.**

Use `write_file` to save to:
```
papers/[arxiv-id].md
```
inside the workspace (e.g., `papers/2412.03555.md`).

If the paper has no arXiv ID, use a slug of the title: `papers/hunyuan-video-2024.md`.

Tell the user: "Analysis saved to `papers/[filename]` in your workspace. You can read it anytime with `read_file`."

After saving, offer:
- "Should I add this paper to your reading list in USER.md?"
- "Would you like to find papers that cite this work?"
- "Want a comparison with a related paper?"

## Personalization

Before analyzing, read USER.md to:
- Connect this paper to papers the user has already read
- Match technical depth to their background
- Note relevance to their current research focus
