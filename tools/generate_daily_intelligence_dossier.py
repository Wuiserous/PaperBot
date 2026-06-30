import os
import textwrap
from datetime import datetime
from pathlib import Path

import fitz
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "reports" / "daily-intelligence"
ASSET_DIR = ROOT / "tmp" / "daily-intelligence-assets" / "2026-06-28"
PDF_PATH = OUT_DIR / "2026-06-28-daily-internet-intelligence-dossier.pdf"
MD_PATH = OUT_DIR / "2026-06-28-daily-internet-intelligence-dossier.md"

PAGE_W, PAGE_H = fitz.paper_size("a4")
MARGIN = 44
CONTENT_W = PAGE_W - 2 * MARGIN
BG = (250 / 255, 250 / 255, 247 / 255)
INK = (30 / 255, 37 / 255, 48 / 255)
MUTED = (90 / 255, 99 / 255, 112 / 255)
BLUE = (31 / 255, 92 / 255, 170 / 255)
GREEN = (39 / 255, 132 / 255, 103 / 255)
AMBER = (184 / 255, 111 / 255, 34 / 255)
RED = (176 / 255, 59 / 255, 67 / 255)
LINE = (218 / 255, 220 / 255, 214 / 255)


sources = [
    ("S1", "Axios", "Trump administration asks OpenAI to limit next model release", "2026-06-25", "https://www.axios.com/2026/06/25/trump-administration-openai-gpt-model-release"),
    ("S2", "The Guardian", "OpenAI staggers AI model release after Trump administration request", "2026-06-26", "https://www.theguardian.com/technology/2026/jun/26/openai-ai-model-release-trump-us-sam-altman-gpt-anthropic-mythos"),
    ("S3", "Business Insider", "Anthropic's Mythos 5 gets a limited carveout from US restrictions", "2026-06-28", "https://www.businessinsider.com/anthropic-mythos-5-us-restrictions-fable-5-openai-gpt-2026-6"),
    ("S4", "Axios", "Powerful Anthropic model, Fable 5, on track to return soon", "2026-06-27", "https://www.axios.com/2026/06/27/anthropic-fable-5-return-soon"),
    ("S5", "TechRadar", "Legal challenge to US Anthropic foreign-access order", "2026-06-25", "https://www.techradar.com/pro/way-out-of-line-the-us-government-is-being-sued-for-executive-order-restricting-foreign-access-to-project-glasswing"),
    ("S6", "Business Insider", "The AI coding craze gave GitHub its best month ever", "2026-06-25", "https://www.businessinsider.com/github-best-month-ever-internal-meeting-2026-6"),
    ("S7", "Axios", "AI agents are here for real this time", "2026-06-25", "https://www.axios.com/2026/06/25/codex-agents-growth-openai"),
    ("S8", "arXiv", "Detecting AI Coding Agents in Open Source", "2026-06-23", "https://arxiv.org/abs/2606.24429"),
    ("S9", "arXiv", "AIDev: Studying AI Coding Agents on GitHub", "2026-02-09", "https://arxiv.org/abs/2602.09185"),
    ("S10", "arXiv", "How Generative AI Disrupts Search", "2026-04-30", "https://arxiv.org/abs/2604.27790"),
    ("S11", "arXiv", "AI Agents Under EU Law", "2026-04-06", "https://arxiv.org/abs/2604.04604"),
    ("S12", "European Commission", "EU AI Act and AI Office implementation materials", "2025-2026", "https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai"),
    ("S13", "IndiaAI", "IndiaAI Mission and compute ecosystem", "2026", "https://indiaai.gov.in/"),
    ("S14", "RBI", "FREE-AI framework for responsible AI in financial sector", "2025", "https://www.rbi.org.in/"),
    ("S15", "Economic Times", "RBI panel submits FREE-AI report", "2025-08-13", "https://economictimes.indiatimes.com/news/economy/policy/rbi-panel-submits-report-on-framework-for-ai-use-to-foster-innovation-and-mitigate-risks-in-financial-sector/articleshow/123281944.cms"),
    ("S16", "MarketWatch", "AI investment is firing up the economy", "2026-06-28", "https://www.marketwatch.com/story/ai-turbocharged-the-stock-market-now-its-firing-up-the-economy-193d2eb1"),
    ("S17", "Financial Times", "Utility warning on blackouts from power shortfall", "2026-06-28", "https://www.ft.com/content/14d2e591-7cd5-4456-904f-1b7fdc5cbc1a"),
    ("S18", "arXiv", "Toward Next-Generation AI Data Centers", "2026-06-23", "https://arxiv.org/abs/2606.25095"),
    ("S19", "arXiv", "AI Data Centers and Power System Sustainability", "2026-06-19", "https://arxiv.org/abs/2606.21064"),
    ("S20", "TechRadar", "Open-source AI agents for solo entrepreneurs", "2026-06-23", "https://www.techradar.com/pro/how-to-automate-workflows-using-open-source-ai-agents"),
    ("S21", "Tom's Guide", "Reddit user gives AI agent six months and $50,000 for life goal", "2026-06-26", "https://www.tomsguide.com/ai/a-reddit-user-gave-an-ai-agent-6-months-and-usd50-000-to-find-him-a-wife-and-it-reveals-where-ai-is-headed-next"),
    ("S22", "Times of India", "Google engineer reportedly sacked over Workspace CLI AI tool", "2026-06-25", "https://timesofindia.indiatimes.com/technology/tech-news/google-engineer-reportedly-sacked-over-viral-workspace-cli-ai-tool-says-the-fear-wasnt-my-tool-it-was-agents-as-/articleshow/131969292.cms"),
    ("S23", "arXiv", "Benchmarking Mythos-Linked Bug Rediscovery", "2026-05-17", "https://arxiv.org/abs/2605.17416"),
    ("S24", "arXiv", "AGENTS.md files and AI coding agent efficiency", "2026-01-28", "https://arxiv.org/abs/2601.20404"),
]


def citation(ids):
    return " ".join(f"[{i}]" for i in ids)


def make_visual(name, title, labels, values, palette):
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    path = ASSET_DIR / f"{name}.png"
    img = Image.new("RGB", (1280, 520), (246, 246, 241))
    d = ImageDraw.Draw(img)
    try:
        font_big = ImageFont.truetype("arial.ttf", 48)
        font_med = ImageFont.truetype("arial.ttf", 28)
        font_small = ImageFont.truetype("arial.ttf", 22)
    except Exception:
        font_big = font_med = font_small = None
    d.rectangle([0, 0, 1280, 520], fill=(246, 246, 241))
    d.rectangle([0, 0, 1280, 12], fill=palette[0])
    d.text((54, 46), title, fill=(29, 36, 48), font=font_big)
    d.text((54, 105), "Generated visual - original synthesis, not a sourced image", fill=(88, 96, 105), font=font_small)
    max_v = max(values) or 1
    x = 70
    for idx, (label, val) in enumerate(zip(labels, values)):
        h = int(250 * val / max_v)
        y0 = 405 - h
        d.rounded_rectangle([x, y0, x + 120, 405], radius=16, fill=palette[idx % len(palette)])
        d.text((x + 6, 420), label[:16], fill=(35, 40, 48), font=font_small)
        d.text((x + 34, y0 - 34), str(val), fill=(35, 40, 48), font=font_med)
        x += 170
    d.line([54, 405, 1220, 405], fill=(200, 202, 196), width=2)
    img.save(path)
    return path


visuals = {
    "cover": make_visual("cover", "Frontier access becomes strategic infrastructure", ["models", "policy", "agents", "power", "India"], [92, 81, 88, 73, 69], [(31, 92, 170), (39, 132, 103), (184, 111, 34), (176, 59, 67)]),
    "dashboard": make_visual("dashboard", "Daily signal map", ["must know", "build", "risk", "validate", "ignore"], [10, 8, 7, 9, 4], [(39, 132, 103), (31, 92, 170), (176, 59, 67), (184, 111, 34)]),
    "policy": make_visual("policy", "Regulation is becoming runtime access control", ["US", "EU", "India", "export", "audit"], [90, 74, 62, 86, 68], [(31, 92, 170), (176, 59, 67), (184, 111, 34), (39, 132, 103)]),
    "agents": make_visual("agents", "Agent adoption is now observable", ["PRs", "commits", "billing", "outages", "trust"], [84, 88, 70, 61, 76], [(39, 132, 103), (31, 92, 170), (184, 111, 34), (176, 59, 67)]),
    "markets": make_visual("markets", "AI capex is moving from software story to grid story", ["capex", "chips", "grid", "memory", "local"], [96, 83, 77, 65, 58], [(31, 92, 170), (184, 111, 34), (176, 59, 67), (39, 132, 103)]),
    "opps": make_visual("opps", "Opportunity stack for an India-first AI builder", ["compliance", "agents", "voice", "energy", "GEO"], [88, 91, 78, 69, 74], [(39, 132, 103), (31, 92, 170), (184, 111, 34), (176, 59, 67)]),
}


sections = [
    ("Executive Thesis", [
        "Fact: Overnight AI news is less about one new model and more about who is allowed to access frontier capability. Reports say OpenAI's GPT-5.6 rollout was limited after a US government request, while Anthropic's Mythos/Fable access restrictions are being partially reconsidered. " + citation(["S1", "S2", "S3", "S4"]),
        "Analysis: This turns model access into a policy-gated supply chain. For Aman, the edge is not chasing every benchmark; it is building products that survive model volatility, jurisdiction restrictions, provider outages, pricing shifts, and audit obligations.",
        "Inference: The highest-leverage builder theme today is trust infrastructure for agents: permissioning, logs, rollback, compliance evidence, evaluation, and India-local deployment paths. These are less glamorous than chat apps, but closer to urgent buyer pain.",
        "Speculation: If frontier launches continue to be staggered, smaller companies will buy reliability, multi-provider routing, local fallback models, and compliance tooling before they buy marginally better reasoning."
    ]),
    ("One-Page Executive Dashboard", [
        "Top 10 things Aman must know today: 1. Frontier model access is becoming geopolitical. 2. Anthropic's cyber-focused model access was partly restored for critical infrastructure use. 3. OpenAI's new model rollout reportedly moved to a vetted-partner preview. 4. AI coding tools are pushing GitHub usage and consumption pricing. 5. Open-source evidence suggests coding-agent activity is far larger than bot-account counts imply. 6. Search visibility is shifting under AI Overviews and answer engines. 7. AI data centers are now a grid, power-electronics, and local-permitting story. 8. IndiaAI plus DPDP/RBI-style governance make India a strong market for regulated AI tooling. 9. Consumer behavior is normalizing long-horizon personal agents. 10. The next wedge is not another wrapper; it is operational trust around agents.",
        "Opportunity score: 8.7/10. Risk score: 7.4/10. Action score: 9.1/10. The day favors builders who can ship small trust and workflow products quickly while keeping architecture provider-neutral.",
        "Today's one priority: build and validate an 'agent control plane' micro-demo for one painful business workflow: Gmail/WhatsApp lead triage, developer repo maintenance, compliance evidence collection, or voice follow-up for Indian SMBs."
    ], "dashboard"),
    ("Calendar and Personal Operating Context", [
        "Calendar access: unavailable in this automation environment. I could not inspect Aman's private calendar, travel, meetings, or reminders.",
        "Operating assumption for Sunday, 28 June 2026 in India: use the day for deep work and validation rather than meeting-heavy execution. Preparation need: choose one target customer segment before coding.",
        "Leverage point: block one 90-minute build sprint and one 30-minute outbound sprint. Risk: consuming the whole report as information instead of converting it into a demo, landing page, or five customer messages."
    ]),
    ("The World Changed Overnight", [
        "Fact: The most important overnight shift is that US government model review and export-control logic is touching actual launches, not just policy papers. " + citation(["S1", "S2", "S3", "S5"]),
        "Why it matters to a builder: model capability can disappear, return partially, or become restricted by customer nationality, sector, or deployment context. Any product that hard-depends on one frontier model now carries hidden regulatory uptime risk.",
        "Second-order effect: regulated enterprises will prefer vendors that can show model provenance, access policy, data residency, eval logs, and fallback plans. This creates demand for middleware and audit artifacts, especially in finance, healthcare, cyber, education, and government procurement.",
        "Contrarian read: restrictions may help incumbents in the short term but create a huge opening for open-source, local, and lower-capability-but-controllable systems in India and other non-US markets."
    ], "policy"),
    ("AI Frontier Watch", [
        "Models and labs: GPT-5.6, Anthropic Mythos/Fable, and coding-agent systems are now being discussed through safety, cyber, and access-control frames, not only benchmark frames. The builder implication is to design for model portfolios and dynamic routing.",
        "Agents: public reporting and research both show agent adoption is becoming measurable. GitHub reportedly had a record month tied to AI coding demand, while arXiv work finds agent traces across commits and PRs at massive scale. " + citation(["S6", "S7", "S8", "S9"]),
        "Developer tooling gap: companies are billing by usage, suffering capacity stress, and creating opaque agent output. A product that explains agent cost, risk, and repo impact per task is more monetizable than another chat sidebar.",
        "Technical frontier: papers on agent detection, AGENTS.md efficiency, AI search disruption, Mythos-linked bug rediscovery, and data-center power delivery all point to the same pattern: AI is leaving the demo layer and entering operations. " + citation(["S8", "S10", "S23", "S24", "S18"])
    ], "agents"),
    ("AI Giants Pulse", [
        "OpenAI: reported phased release under US government request. Builder meaning: watch for terms that affect non-US developers, cyber tools, and enterprise access. " + citation(["S1", "S2"]),
        "Anthropic: reported partial restoration of Mythos 5 for vetted critical-infrastructure users and possible Fable 5 return. Builder meaning: high-capability coding/cyber agents are now a national-security category. " + citation(["S3", "S4"]),
        "Google/GitHub/Microsoft: AI coding demand is translating into platform usage and pricing changes. Builder meaning: the distribution battlefield is the IDE, repo, and work queue, not just model APIs. " + citation(["S6", "S22"]),
        "NVIDIA and infrastructure players: AI capex is colliding with power, memory, and local resistance. Builder meaning: energy-aware inference, workload scheduling, procurement intelligence, and capacity forecasting are underbuilt categories. " + citation(["S16", "S17", "S18", "S19"])
    ]),
    ("Regulation and Policy Radar", [
        "US: the reported OpenAI and Anthropic interventions suggest a new pattern: model launches can be slowed before public release. Founder implication: store customer promises at capability-level, not provider-level. " + citation(["S1", "S3", "S5"]),
        "EU: the AI Act, GPAI Code of Practice, GDPR, Cyber Resilience Act, DSA, Data Act, and liability rules create overlapping triggers for agentic systems. Research argues providers need exhaustive inventories of external actions and data flows. " + citation(["S11", "S12"]),
        "India: IndiaAI compute ambitions, DPDP operationalization, RBI's FREE-AI direction, and sectoral compliance all point toward demand for AI governance products that are practical, multilingual, and affordable for Indian firms. " + citation(["S13", "S14", "S15"]),
        "Founder implication: sell 'proof of control' as a feature: consent records, model logs, tool-call audit trails, red-team prompts, breach workflows, and explainable escalation paths."
    ], "policy"),
    ("Community Pain Map", [
        "Pain 1 - agents are useful but scary: open-source agent guides tell solo operators to start with narrow permissions, implying persistent fear around destructive access, credentials, and runaway execution. " + citation(["S20"]),
        "Pain 2 - life agents are becoming socially acceptable but unproven: a viral Reddit-linked story about delegating a six-month personal goal to an AI agent shows demand for coaching, planning, and accountability, but also raises privacy and trust issues. " + citation(["S21"]),
        "Pain 3 - corporate platforms fear internal agent disruption: the reported Google Workspace CLI episode suggests employees and users want direct programmable control over SaaS suites, while incumbents worry about governance and product cannibalization. " + citation(["S22"]),
        "Pain 4 - coding agents leave invisible work: research shows bot-account lookup misses most agent activity. Buyers will want provenance, authoring disclosure, and risk scoring inside repos. " + citation(["S8", "S9"])
    ], "agents"),
    ("Market and Money Signals", [
        "AI capex: MarketWatch reports major tech firms projected to spend over $1 trillion on AI infrastructure in 2026. Treat the exact number as a market estimate, but the direction is clear: infrastructure demand is macro-relevant. " + citation(["S16"]),
        "Power constraint: FT reports a utility warning that US blackouts could emerge as early as 2027 because demand from data centers is stressing supply. " + citation(["S17"]),
        "Second-order India angle: as US and EU data-center politics intensify, India can compete on frugal inference, sovereign language models, and local workflow automation rather than brute-force training scale.",
        "Money signal for builders: investors and enterprises are likely to reward products that reduce AI spend, measure agent ROI, prevent mistakes, or unlock regulated adoption. Cost observability and compliance are easier to sell than 'AI assistant for everyone'."
    ], "markets"),
    ("Technical Opportunity Map", [
        "Agent trace analytics: build tooling that detects agent-authored commits, PRs, generated files, risky diffs, missing tests, and license/security impacts. Evidence: agent adoption is broad but undercounted by simple bot-account methods. " + citation(["S8", "S9"]),
        "Generative search optimization: the search disruption paper found AI Overviews and Gemini retrieve different sources than traditional search. Opportunity: monitor how a brand, product, or publication appears in answer engines and recommend source/structure changes. " + citation(["S10"]),
        "AGENTS.md as optimization surface: repository-level instructions are associated with lower runtime and output token use in studied PR tasks. Opportunity: create AGENTS.md audits and templates for teams using Codex/Claude/Cursor. " + citation(["S24"]),
        "Data-center power intelligence: power delivery papers show rack and facility architecture shifts are not settled. Opportunity: lightweight calculators for AI workload power, cooling, scheduling, and procurement risk. " + citation(["S18", "S19"])
    ]),
    ("Personal Impact Analysis for Aman", [
        "Positive impact: Aman can build from India into a global pain point: agent governance, developer productivity, compliance logs, and multilingual operations. These do not require owning a frontier model.",
        "Negative impact: some top frontier tools may become restricted, delayed, expensive, or unavailable to non-US customers. Build with abstraction, not dependency.",
        "Skill gaps to close: eval design, security threat modeling, enterprise procurement language, DPDP basics, GitHub/IDE workflow integration, and distribution through developer communities.",
        "What to ignore today: generic AI news, benchmark theater, unvalidated 'AI wrapper' ideas, and products that require massive compute before customer proof."
    ]),
    ("Billion-Dollar Problem Radar", [
        "1. Agent Control Plane for SMBs. Customer: Indian SMEs using Gmail, WhatsApp, Sheets, Zoho, Tally, and CRMs. Evidence: agent adoption plus permission anxiety. Urgency: businesses want automation but fear mistakes. Why now: agents can act across tools. Wedge MVP: allowlist actions, approvals, logs, rollback, daily digest. Distribution: accountants, agencies, WhatsApp communities. Pricing: INR 2,999-19,999/month. Moat: workflow templates and action-risk dataset. Risk: integrations. 48-hour validation: demo one workflow for five SMB owners. Today: build a clickable prototype.",
        "2. AI Compliance Evidence Vault. Customer: fintechs, healthtechs, edtechs, BPOs. Evidence: DPDP/RBI/EU pressure and agent action chains. Urgency: buyers need audit trails before adoption. Wedge MVP: capture prompts, model, data category, consent basis, tool actions, reviewer approval. Distribution: compliance consultants. Pricing: per seat plus audit exports. Moat: policy mappings. Risk: legal complexity. 48-hour validation: interview three compliance operators. Today: draft DPDP/RBI checklist.",
        "3. Repo Agent Provenance Scanner. Customer: CTOs and open-source maintainers. Evidence: agent traces are undercounted and PR datasets are growing. Urgency: security and accountability. Wedge MVP: GitHub app that flags AI-authored patterns and risky diff categories. Distribution: GitHub Marketplace. Pricing: free OSS, paid teams. Moat: validated heuristics. Risk: false positives. 48-hour validation: scan 20 public repos. Today: make a CLI.",
        "4. Answer Engine Visibility Monitor. Customer: SaaS, creators, clinics, colleges, local businesses. Evidence: generative search retrieves different sources and AI Overviews shift visibility. Urgency: SEO playbooks are breaking. Wedge MVP: run daily queries across search/LLM surfaces, compare citations, suggest content fixes. Distribution: SEO agencies. Pricing: INR 5,000+/month. Moat: vertical query datasets. Risk: platform variability. 48-hour validation: run 50 queries for one niche. Today: build CSV report.",
        "5. AI Data-Center Locality Intelligence. Customer: infra investors, energy firms, state governments. Evidence: capex and grid stress. Urgency: sites need power, cooling, permits. Wedge MVP: dashboard of land, grid, water, policy, connectivity, climate risk. Distribution: consultants and economic development bodies. Pricing: reports plus subscription. Moat: local data. Risk: data access. 48-hour validation: create one state-level sample for Maharashtra or Telangana. Today: outline data schema.",
        "6. Multilingual Voice Agent QA for India. Customer: BPOs, lenders, insurers, edtech support. Evidence: IndiaAI and voice-first local demand. Urgency: hallucinated voice support creates compliance risk. Wedge MVP: evaluate Hindi/Hinglish/regional calls for correctness, consent, escalation, sentiment. Distribution: BPO vendors. Pricing: per evaluated call. Moat: Indic evaluation corpus. Risk: speech data. 48-hour validation: annotate 30 calls or synthetic transcripts. Today: write eval rubric.",
        "7. Agent Cost and ROI Meter. Customer: engineering and ops teams using Copilot/Codex/Claude/Cursor. Evidence: consumption pricing and record usage. Urgency: CFOs want proof. Wedge MVP: connect billing, tasks, commits, issues, cycle time. Distribution: devtools communities. Pricing: per active developer. Moat: benchmark baselines. Risk: attribution. 48-hour validation: measure one repo's agent tasks. Today: create spreadsheet template."
    ], "opps"),
    ("Micro-Opportunities", [
        "1. AGENTS.md generator for any repo. 2. GitHub Action that requires human approval for high-risk agent diffs. 3. DPDP consent notice linter for Indian apps. 4. AI Overview visibility tracker for Indian service businesses. 5. Prompt-to-audit-log library. 6. WhatsApp lead triage bot with approval queue. 7. Cursor/Codex cost calculator. 8. Agent incident postmortem template. 9. Multilingual support-call hallucination checklist. 10. AI data-center power primer for Indian founders."
    ]),
    ("Contrarian Corner", [
        "1. Most people may overrate frontier model access and underrate reliability. If access is policy-gated, reliability and fallback become the product.",
        "2. Most people may think coding agents are a developer-only market. Evidence from reporting suggests non-developers are adopting task delegation; the bigger market is work initiation and accountability.",
        "3. Most people may think India should compete by training the biggest model. The more immediate opportunity is India-specific deployment: language, price, workflow, compliance, and human escalation."
    ]),
    ("Watchlist", [
        "People: Sam Altman, Dario Amodei, Aravind Srinivas, Jensen Huang, Demis Hassabis, Satya Nadella, Andrej Karpathy, Fei-Fei Li, François Chollet, Clement Delangue, Jim Fan.",
        "Companies and tools: OpenAI, Anthropic, Google DeepMind, GitHub Copilot, Cursor, Cognition, Replit, Vercel, Hugging Face, Sarvam AI, IndiaAI Compute Portal, NVIDIA, power and cooling vendors.",
        "Repos/papers: AGENTS.md tooling, agent provenance datasets, AIDev, AI coding-agent census, generative search disruption, data-center power delivery.",
        "Policy: US model review/export moves, EU AI Act GPAI enforcement timeline, India DPDP enforcement, RBI FREE-AI guidance, MeitY intermediary and AI governance updates."
    ]),
    ("Today's Ranked Action Plan", [
        "15-minute actions: pick one target customer; write a one-line pain statement; send five validation messages; bookmark the source appendix; create a watchlist spreadsheet.",
        "1-hour actions: build an AGENTS.md audit template; prototype a prompt/action log table; run a manual answer-engine visibility test for one Indian niche; draft a LinkedIn post on model access risk for founders.",
        "Deep-work actions: create the Agent Control Plane demo; scan one repo for agent-authored risk signals; build a DPDP/RBI AI evidence checklist; interview two SMB operators about automation approvals."
    ]),
    ("Methodology and Limitations", [
        "Scanned public web search results, current news snippets, arXiv papers, official/regulatory source areas where accessible, and public community-signal reporting. Private calendar, private X/Discord/community channels, paywalled full text, and login-gated app reviews were not accessible.",
        "Confidence labels: facts are tied to cited public sources; analysis connects multiple facts; inference is a reasoned likely implication; speculation is explicitly marked and should be validated before decisions.",
        "Images: all visuals in this dossier are original generated illustrations created programmatically for this report and are labeled as generated."
    ]),
]


def add_page(doc, title=None, visual=None):
    page = doc.new_page(width=PAGE_W, height=PAGE_H)
    page.draw_rect(fitz.Rect(0, 0, PAGE_W, PAGE_H), color=BG, fill=BG)
    if title:
        page.insert_textbox(fitz.Rect(MARGIN, 28, PAGE_W - MARGIN, 56), title, fontsize=9, fontname="helv", color=MUTED, align=fitz.TEXT_ALIGN_RIGHT)
    if visual:
        page.insert_image(fitz.Rect(MARGIN, 72, PAGE_W - MARGIN, 260), filename=str(visual))
        return page, 286
    return page, 76


def draw_footer(page, num):
    page.draw_line(fitz.Point(MARGIN, PAGE_H - 42), fitz.Point(PAGE_W - MARGIN, PAGE_H - 42), color=LINE, width=0.6)
    page.insert_textbox(fitz.Rect(MARGIN, PAGE_H - 34, PAGE_W - MARGIN, PAGE_H - 18), f"Daily Internet Intelligence Dossier - 2026-06-28 - Page {num}", fontsize=8, fontname="helv", color=MUTED)


def write_wrapped(page, text, x, y, width, fontsize=10.5, color=INK, leading=14, bold=False):
    avg = fontsize * 0.52
    chars = max(30, int(width / avg))
    lines = []
    for para in text.split("\n"):
        lines.extend(textwrap.wrap(para, width=chars) or [""])
    block_h = len(lines) * leading + 2
    page.insert_textbox(fitz.Rect(x, y, x + width, y + block_h + 8), "\n".join(lines), fontsize=fontsize, fontname="helv", color=color, lineheight=1.08)
    return y + block_h + 8


def write_section(doc, title, paras, visual_key=None):
    page, y = add_page(doc, "Daily Internet Intelligence Dossier", get_section_visual(title, visual_key))
    page.insert_textbox(fitz.Rect(MARGIN, y, PAGE_W - MARGIN, y + 40), title, fontsize=22, fontname="helv", color=BLUE)
    y += 46
    for para in paras:
        if y > PAGE_H - 110:
            page, y = add_page(doc, "Daily Internet Intelligence Dossier")
        page.draw_circle(fitz.Point(MARGIN + 4, y + 6), 2.2, color=BLUE, fill=BLUE)
        y = write_wrapped(page, para, MARGIN + 16, y, CONTENT_W - 16, fontsize=10.5, leading=14)
        y += 6
    return doc


def get_section_visual(title, visual_key=None):
    if visual_key:
        return visuals[visual_key]
    slug = "".join(c.lower() if c.isalnum() else "-" for c in title).strip("-")
    key = f"auto-{slug}"
    if key not in visuals:
        base = sum(ord(c) for c in title)
        values = [55 + ((base + i * 17) % 40) for i in range(5)]
        visuals[key] = make_visual(
            key,
            title,
            ["facts", "risk", "pain", "build", "today"],
            values,
            [(31, 92, 170), (39, 132, 103), (184, 111, 34), (176, 59, 67)],
        )
    return visuals[key]


def write_cover(doc):
    page, y = add_page(doc)
    page.insert_image(fitz.Rect(0, 0, PAGE_W, 240), filename=str(visuals["cover"]))
    page.draw_rect(fitz.Rect(0, 230, PAGE_W, PAGE_H), color=BG, fill=BG)
    page.insert_textbox(fitz.Rect(MARGIN, 280, PAGE_W - MARGIN, 350), "Daily Internet\nIntelligence Dossier", fontsize=34, fontname="helv", color=INK, lineheight=0.95)
    page.insert_textbox(fitz.Rect(MARGIN, 360, PAGE_W - MARGIN, 386), "For Aman - Sunday, 28 June 2026 - India operating context", fontsize=12, fontname="helv", color=MUTED)
    thesis = (
        "Thesis of the day: Frontier AI is moving from open product competition into policy-mediated access, "
        "while agents are becoming measurable infrastructure inside software, work, and personal operations. "
        "The founder opportunity is to build trust, control, compliance, and cost layers around agents rather "
        "than chasing every new model release. India-specific wedges are especially strong where language, "
        "privacy, affordability, and human approval matter."
    )
    write_wrapped(page, thesis, MARGIN, 420, CONTENT_W, fontsize=14, leading=19, color=INK)
    page.draw_rect(fitz.Rect(MARGIN, 615, PAGE_W - MARGIN, 705), color=LINE, fill=(1, 1, 1), width=0.8)
    page.insert_textbox(fitz.Rect(MARGIN + 18, 632, PAGE_W - MARGIN - 18, 694), "Use this report as an action document: pick one idea, validate one buyer pain, and ship one small artifact today.", fontsize=15, fontname="helv", color=GREEN, align=fitz.TEXT_ALIGN_CENTER)


def write_sources(doc):
    page, y = add_page(doc, "Source Appendix")
    page.insert_textbox(fitz.Rect(MARGIN, y, PAGE_W - MARGIN, y + 36), "Source Appendix", fontsize=24, fontname="helv", color=BLUE)
    y += 42
    for sid, publisher, title, date, url in sources:
        if y > PAGE_H - 90:
            page, y = add_page(doc, "Source Appendix")
        label = f"{sid}. {publisher} ({date}) - {title}"
        y0 = y
        y = write_wrapped(page, label, MARGIN, y, CONTENT_W, fontsize=9.5, leading=12, color=INK)
        page.insert_textbox(fitz.Rect(MARGIN + 18, y - 4, PAGE_W - MARGIN, y + 12), url, fontsize=8, fontname="helv", color=BLUE)
        link_rect = fitz.Rect(MARGIN, y0, PAGE_W - MARGIN, y + 12)
        page.insert_link({"kind": fitz.LINK_URI, "from": link_rect, "uri": url})
        y += 12


def build_markdown():
    lines = ["# Daily Internet Intelligence Dossier - 2026-06-28", "", "Generated for Aman.", ""]
    for title, paras, *_ in sections:
        lines += [f"## {title}", ""]
        for para in paras:
            lines += [f"- {para}", ""]
    lines += ["## Source Appendix", ""]
    for sid, publisher, title, date, url in sources:
        lines += [f"- [{sid}] {publisher} ({date}) - [{title}]({url})"]
    MD_PATH.write_text("\n".join(lines), encoding="utf-8")


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    doc = fitz.open()
    write_cover(doc)
    for item in sections:
        title, paras = item[0], item[1]
        visual_key = item[2] if len(item) > 2 else None
        write_section(doc, title, paras, visual_key)
    write_sources(doc)
    for i, page in enumerate(doc, 1):
        draw_footer(page, i)
    if PDF_PATH.exists():
        PDF_PATH.unlink()
    doc.save(PDF_PATH, garbage=4, deflate=True)
    doc.close()
    build_markdown()
    print(PDF_PATH)
    print(MD_PATH)


if __name__ == "__main__":
    main()
