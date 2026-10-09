# DataForge AI — LinkedIn launch kit

Drop-in assets and copy for a LinkedIn launch post. Everything here was generated
from the real product UI (premium dark + gold theme) so the post is honest about
what the app actually does.

## Files

| File | Size | Where it goes on LinkedIn |
| --- | --- | --- |
| [dataforge-linkedin-promo.mp4](dataforge-linkedin-promo.mp4) | 1080×1080, 34 s, H.264, silent | **Primary post** — native video upload |
| [linkedin-post-1200x627.png](linkedin-post-1200x627.png) | 1200×627 | Link-share card / image post / OG image |
| [linkedin-square-1080x1080.png](linkedin-square-1080x1080.png) | 1080×1080 | Square image post, or reuse as the video thumbnail |
| [linkedin-cover-1584x396.png](linkedin-cover-1584x396.png) | 1584×396 | Company page / personal profile cover banner |
| [storyboard-*.png](.) | 1080×1080 | One still per scene — handy for a carousel or a slide deck |
| [linkedin-about-section.md](linkedin-about-section.md) | — | Ready-to-paste **About / Featured / Experience** profile copy |

The video is silent (LinkedIn autoplays muted). Add licensed music in LinkedIn's
editor if you want audio, or leave it silent — every scene is fully readable
without sound.

---

## Recommended post (long form)

> **Every organization sits on answers. Most never find them.**
>
> The answers are already in your databases and your documents. The problem is the
> distance between a question a person has and the data that answers it — which is
> usually a ticket, a wait, and a spreadsheet that's out of date by Friday.
>
> So we built **DataForge AI**.
>
> You ask a question in plain language. DataForge picks the right tools, writes
> **read-only SQL** against your connected databases, searches your uploaded
> documents, and answers with its sources attached.
>
> What makes it defensible rather than just convenient:
>
> → **Read-only by default.** The model never gets unrestricted database access.
> → **Grounded answers.** Every result is tied back to the tables it queried and
> the document passages it cited.
> → **Scoped to the person asking.** Role-based permissions decide which data
> sources and documents each teammate can reach — the analyst only sees what they
> are entitled to.
> → **Audited end to end.** Every AI run is recorded with the tools it used, its
> model, token usage and duration, in an append-only audit log that cannot be
> edited or deleted.
>
> That last part is the difference between a demo and something you can put in
> front of a CFO.
>
> We're opening conversations with teams who are drowning in dashboards and still
> answering the same questions by hand.
>
> 👉 **data-forge.ai** — request a conversation.
>
> #AI #DataAnalytics #BusinessIntelligence #DataGovernance #EnterpriseAI #RAG #SQL

**Characters:** ~1,450 — comfortably inside LinkedIn's 3,000 limit, and the hook
survives the "…see more" fold.

---

## Short variant (thought-leadership hook)

> Every organization sits on answers. Most never find them.
>
> The data is there. The documents are there. What's missing is a way to ask.
>
> **DataForge AI** turns plain-language questions into read-only SQL over your
> databases and cited answers from your documents — scoped to your role, and
> recorded in an audit log you can't quietly edit.
>
> Ask your data anything. Get answers you can defend.
>
> data-forge.ai
>
> #AI #DataAnalytics #DataGovernance #EnterpriseAI

---

## Video caption (pair with the MP4)

> 34 seconds on how DataForge AI answers a business question — and why you can
> trust the answer. 👇
>
> Plain-language question → read-only SQL → cited sources → an immutable audit
> trail. Ask your data anything.
>
> data-forge.ai
>
> #AI #DataAnalytics #BusinessIntelligence #DataGovernance #EnterpriseAI

---

## First-comment post (keeps the main post clean)

> The part people ask about first is always the same: *"does the model get access
> to our database?"*
>
> No. DataForge issues read-only SQL, and every query, tool call and document
> retrieval is written to an append-only audit log. You can see exactly how an
> answer was produced — including the duration, model and tokens for each run.
>
> Happy to walk through the architecture with anyone evaluating this space.

---

## Alt text (accessibility — paste into LinkedIn's "Add alt text")

- **Post card (1200×627):** Dark banner with the DataForge AI gold hexagon logo,
  the headline "Every organization sits on answers. Most never find them." and a
  gold "Request a conversation" button, next to a screenshot of the AI Analyst
  console.
- **Square (1080×1080):** DataForge AI logo above the headline "Ask your business
  data anything," with the line "Every answer is grounded in your connected
  databases and documents, scoped to your role, and recorded in a tamper-evident
  audit log."
- **Cover (1584×396):** DataForge AI wordmark and tagline beside the headline
  "Most never find them." and a gold request-a-conversation button.
- **Video:** A 34-second silent product tour in the DataForge AI dark and gold
  theme: brand intro, the problem statement, the AI Analyst console, role-based
  access control settings, audit logs, and a closing call to action at
  data-forge.ai.

---

## Posting checklist

1. Upload **dataforge-linkedin-promo.mp4** as a native video (not a YouTube link)
   — native video gets far more reach and autoplays muted.
2. Set the thumbnail to a frame from `storyboard-1-01.6s-intro.png` or the square
   image, and add the alt text above.
3. Paste the long-form caption. Keep the first two lines as the hook; everything
   after "see more" is for the people who already stopped scrolling.
4. Post the first comment immediately after publishing so it rides the same
   notification wave.
5. Refresh the **cover banner** on the company page with
   `linkedin-cover-1584x396.png`.
6. Best windows for a B2B technical audience: Tuesday–Thursday, 08:00–10:00 local
   time of your main market.
7. Optional but effective: run the square image as a **text post** 3–4 days later
   with the short variant, so the same message reaches people who missed the video.

---

## Regenerating

```bash
python docs/marketing/linkedin/build_assets.py            # everything
python docs/marketing/linkedin/build_assets.py banners    # images only
python docs/marketing/linkedin/build_assets.py stills     # storyboard only
python docs/marketing/linkedin/build_assets.py video      # MP4 only
```

Requires Python with Pillow (already available) and `imageio-ffmpeg` for the
bundled H.264 encoder: `python -m pip install --user imageio-ffmpeg`.

Source screenshots come from [docs/user-guide/screenshots](../../user-guide/screenshots).

### Copy review notes

- No metrics, customers or benchmarks are claimed anywhere — everything in the
  copy maps to a feature that exists in the app today. Add real numbers only when
  you have them.
- "Request a conversation" mirrors the CTA on the public marketing site.
- Swap `data-forge.ai` for your actual destination (or a shortened UTM link) before
  publishing.
