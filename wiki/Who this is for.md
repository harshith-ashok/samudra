---
tags:
  - year-3
  - sih
---
# SAMUDRA — Who It's For, What Each Part Does, and Why It Matters

This document exists to answer one question clearly: **if someone actually used this tomorrow, what would they use it for?** It covers who the platform serves, what each component does, and what it looks like in a real situation — not just a feature list.

---

## Part 1 — Who this is for

### Fisheries department officers

**Who they are:** State and central fisheries department staff responsible for monitoring catch trends and issuing advisories (fishing bans, quota warnings, seasonal restrictions).

**Today, without this:** Advisories tend to get issued after a decline is already visible in landing reports — which arrive on a delay, from multiple ports, in inconsistent formats. By the time the pattern is confirmed, the season's damage is often already done.

**What they'd use:** The stock forecast module and the map's advisory layer, plus the AI assistant to quickly check "what's driving the trend in this region" before drafting an advisory — with sourced numbers, not a guess.

**Real scenario:** An officer sees a sardine stock forecast trending downward for the Kochi region three months out. Instead of waiting for the decline to show up in landing data, they check the assistant, confirm it correlates with a real SST anomaly, and issue an early advisory — giving fishing communities time to plan rather than reacting to a bad season already underway.

### Marine researchers and biologists

**Who they are:** Scientists at institutions like CMFRI, university researchers, and independent marine biologists working on species distribution, ecosystem health, or eDNA studies.

**Today, without this:** A huge share of research time goes into simply _assembling_ data — pulling occurrence records from OBIS, cross-checking against local survey data, and manually correlating it with environmental conditions, before any actual analysis can begin.

**What they'd use:** The species explorer, the map's biodiversity layer, and natural language query to pull cross-referenced records in one step instead of stitching together multiple exports.

**Real scenario:** A researcher studying reef fish decline near Lakshadweep types a plain-language query — "vulnerable species detections near Lakshadweep since March" — and gets matched records across eDNA, survey, and catch data in seconds, with the underlying query shown transparently, instead of spending an afternoon cross-referencing spreadsheets.

### MPA managers and conservation teams

**Who they are:** Staff managing marine protected areas and coastal conservation NGOs, with limited field-verification resources and a large area to cover.

**Today, without this:** Reef health checks and patrol priorities are often set on a fixed schedule or by anecdotal reports, not by where the actual risk is highest right now.

**What they'd use:** The coral bleaching risk score, the seasonal timeline to see risk building over weeks, and the illegal fishing detection layer to know where vessels are actually active inside protected boundaries.

**Real scenario:** A manager overseeing several reef sites sees one site's bleaching risk score climbing on the timeline over two weeks. Instead of rotating through sites on a fixed schedule, they prioritize a field visit to that specific reef while risk is still classified as moderate, not severe.

### Policy makers and blue economy planners

**Who they are:** Staff at the Ministry of Earth Sciences, state planning departments, or blue economy initiatives who need a synthesized regional picture, not raw datasets.

**Today, without this:** Producing a cross-domain summary (ocean health + fisheries + biodiversity, by region) usually requires commissioning a report that takes weeks, because no single system currently holds all three together.

**What they'd use:** The dashboard's regional comparison views and the AI assistant for direct, citable answers to planning questions.

**Real scenario:** A planner preparing a coastal zone management update asks the assistant to summarize biodiversity and pollution trends for a specific stretch of coastline, and gets a grounded answer with sources in minutes rather than requesting a new study.

### Fishing communities

**Who they are:** The people whose livelihoods are most directly affected by everything this platform tracks, and who are least likely to ever open a technical dashboard.

**Today, without this:** Information about advisories, safety, or stock conditions reaches communities late, secondhand, or not at all.

**What they'd use:** A voice-enabled interface (regional languages) layered on the same AI assistant — ask a question out loud, get a spoken answer back.

**Real scenario:** A fisherman asks, in Malayalam, "is it worth going out near Kochi this week" and gets a direct spoken answer summarizing the current advisory status and stock trend — no dashboard, no English, no login required.

### Enforcement and patrol teams

**Who they are:** Coast guard, fisheries patrol units, and MPA enforcement staff responsible for catching illegal fishing activity.

**Today, without this:** Vessel tracking data exists globally, but cross-referencing it against specific Indian MPA boundaries in real time isn't something most coastal teams have tooling for — violations are often caught reactively, if at all.

**What they'd use:** The live vessel tracking layer, which automatically flags vessels inside restricted zones.

**Real scenario:** A patrol team gets an automatic flag that three vessels have entered a restricted zone during a no-fishing window, and can prioritize a response instead of relying on a routine patrol schedule to happen to catch it.

---

## Part 2 — What each component actually does

### Interactive map

**What it is:** A live map with layered data — ocean buoys, eDNA sampling sites, fishing advisory zones, coral reef risk, treatment plant locations, and tracked vessels. **What it's for:** Giving every other feature a shared, geographic anchor — nothing in the platform floats disconnected from a real place. **Real-life use:** A user toggles the pollution layer on top of the biodiversity layer and visually spots that a declining reef site sits near a non-compliant treatment plant — a connection that would otherwise require manually overlaying two separate reports.

### AI assistant (RAG chat)

**What it is:** A conversational interface that retrieves real sensor, catch, and species data before answering — grounded, cited responses instead of a model guessing from general knowledge. **What it's for:** Letting anyone ask a cross-domain question in plain language and get an answer backed by the platform's actual data. **Real-life use:** "Why is catch declining off Kerala" returns an answer built from real catch records and real temperature data, with sources — the same question that would otherwise require pulling two separate reports and comparing them by hand.

### Natural language query (NLQ)

**What it is:** A search bar that translates a plain-English question into a structured data query and shows both the translated query and the matching records. **What it's for:** Making the underlying database usable by someone who doesn't know SQL or the schema — while staying transparent about exactly what was searched. **Real-life use:** A researcher types "vulnerable species near Kerala since March" and sees both the matching records and the exact filter logic used to find them, so the result is checkable, not a black box.

### Predictive analytics (stock, bleaching, range shift)

**What it is:** Three forward-looking models — a stock trend forecast, a coral bleaching risk score (based on real thermal-stress accumulation methodology), and a species range-shift projection. **What it's for:** Shifting the platform from reporting what already happened to flagging what's likely to happen — the difference between reacting to a crisis and catching it early. **Real-life use:** A bleaching risk score crossing an alert threshold triggers a field-verification visit before visible coral damage occurs, not after.

### Seasonal timeline (scrubbable)

**What it is:** A month-long, day-by-day replay of predictions and historical trends across the map, rather than a single static number. **What it's for:** Making a trend visible and intuitive — watching a risk build over weeks communicates far more than one number does. **Real-life use:** In a briefing, a manager scrubs the timeline forward to show stakeholders exactly how a reef's bleaching risk is projected to develop over the coming month, rather than presenting an abstract percentage.

### Illegal fishing detection

**What it is:** A live layer that cross-references vessel tracking data against real marine protected area boundaries and flags vessels inside restricted zones. **What it's for:** Turning the platform from purely informational into something with actual enforcement value. **Real-life use:** A flagged vessel inside a no-fishing zone during a restricted window becomes an actionable alert for a patrol team, instead of a violation that's only discovered after the fact, if ever.

### Plain-language data explainers

**What it is:** Short, jargon-free explanations attached to every data layer, chart, and metric — what it is, and why it matters, in one or two sentences. **What it's for:** Making sure the platform is usable by someone without a marine science background, including judges, policymakers, and community members. **Real-life use:** A non-technical stakeholder hovers over "Degree Heating Weeks" and immediately understands it as accumulated heat stress on a reef, without needing it explained by a scientist in the room.

---

## Part 3 — Why this matters beyond the demo

The common thread across every persona above is the same: **the data to make a good decision usually already exists — it's just arriving too late, or in too many disconnected places, for anyone to act on it in time.** A fisheries officer, a reef manager, and a patrol team are all, in different ways, solving the same problem — noticing a pattern before it becomes a loss.

What SAMUDRA changes isn't the existence of the data. It's the time between _when a pattern is detectable_ and _when a person who can act on it actually sees it_ — and who is able to see it at all, whether that's a scientist reading a chart or a fisherman asking a question out loud in their own language.