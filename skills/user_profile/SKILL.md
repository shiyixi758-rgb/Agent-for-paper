---
name: user_profile
description: Read and update the user's research profile (interests, read papers, preferences).
always: true
---

# Skill: User Research Profile

## When to Read USER.md

Read USER.md **before** every paper search, analysis, or recommendation.
Use it to:
- Skip papers the user has already read
- Prioritize their preferred venues
- Match explanation depth to their background
- Connect new papers to their existing knowledge

## When to Update USER.md

Update when:
1. The user says "update my profile", "add this to my reading list", "I'm now researching X"
2. The user mentions reading or finishing a paper
3. The user corrects or expands their research interests

Always confirm before writing: "Should I add [paper] to your reading list?"

## How to Update USER.md

Use the `edit_file` tool on `USER.md` in the workspace.

**Adding a read paper** (append to "Already Read Papers" section):
```
- [YEAR] Title (Venue) — one-line takeaway
```

**Updating research interests**:
```
## Research Interests
- Video generation (diffusion models, flow matching, DiT-based)
- Video understanding (temporal reasoning, video QA)
```

## Conversation Memory

At the end of a session where new papers were discussed, offer:
"Should I add the papers we discussed today to your reading list?"

When starting a new session, read USER.md first and acknowledge relevant context:
"I see you're focused on [topic] — picking up from where we left off?"

## Privacy

- USER.md is stored locally in `~/.nanobot/workspace/USER.md`.
- Never include USER.md contents verbatim when performing web searches.
