---
name: daily_digest
description: Set up and run a daily arXiv paper digest delivered via WeChat, Feishu, or Telegram.
---

# Skill: Daily Paper Digest

## Setup (One-Time)

When the user says "set up daily paper push" or "send me papers every day":

1. Ask if not already in USER.md:
   - Topics (default: Research Interests from USER.md)
   - Time (default: 9:00 AM Asia/Shanghai)
   - Count (default: 5 papers)

2. Register a cron job:
   ```
   cron(action="add", cron_expr="0 9 * * *", tz="Asia/Shanghai",
        message="Run daily paper digest")
   ```

3. Write schedule to HEARTBEAT.md:
   ```
   ## Daily Paper Digest
   - Time: 9:00 AM (Asia/Shanghai)
   - Topics: [from USER.md]
   - Count: 5
   - Channel: weixin / feishu / telegram
   ```

4. Confirm: "Daily digest set up! Sending [N] papers on [topics] at [time] via [channel]."

## Running the Digest (Triggered by Cron)

1. Read USER.md for current research interests and already-read papers.
2. Search arXiv for papers from the **last 24 hours**:
   - Web search: `site:arxiv.org "[topic]" 2025` with date filter
   - Or fetch arXiv RSS: `https://arxiv.org/rss/cs.CV` (adjust category)
3. Filter out papers already in the user's "Already Read" list.
4. Rank by relevance to Research Interests.
5. Select top N and format the digest.

## Message Format

Keep it **concise and scannable** — this is a notification, not a full analysis.

```
📰 今日论文推送 — [Date]

1️⃣ [Paper Title]
   作者: [First Author] et al. | 来源: arXiv [ID]
   亮点: [One sentence — what's new and why it matters]
   🔗 https://arxiv.org/abs/[ID]

2️⃣ ...

---
💡 回复 "分析第X篇" 获取深度解读
💡 回复 "停止推送" 取消每日推送
```

Use Chinese or English based on USER.md preference.

## Stopping the Digest

When user says "stop daily digest" or "cancel":
1. `cron(action="remove", ...)` to delete the job.
2. Remove the entry from HEARTBEAT.md.
3. Confirm cancellation.

## Quality Rules

- Only send papers with verified arXiv links.
- Never send the same paper twice (check against Already Read).
- If no new papers found: "今日没有发现新的相关论文，明日继续推送 📭"
- Max 8 papers per digest.
