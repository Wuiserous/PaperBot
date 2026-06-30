from __future__ import annotations

import os
import textwrap
from datetime import datetime, timezone, timedelta
from pathlib import Path

import fitz
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(r"C:\Users\Aman\PycharmProjects\PaperBot")
OUT_DIR = ROOT / "reports" / "daily-intelligence"
IMG_DIR = ROOT / "tmp" / "daily-intelligence-2026-06-29"
PDF_PATH = OUT_DIR / "2026-06-29-daily-internet-intelligence-dossier.pdf"
MD_PATH = OUT_DIR / "2026-06-29-daily-internet-intelligence-dossier.md"

IST = timezone(timedelta(hours=5, minutes=30))
RUN_TIME = datetime.now(IST).isoformat(timespec="seconds")

COLORS = {
    "ink": (31, 41, 55),
    "muted": (91, 105, 121),
    "paper": (251, 250, 247),
    "navy": (15, 43, 75),
    "blue": (41, 121, 255),
    "teal": (0, 150, 136),
    "orange": (236, 137, 46),
    "red": (202, 78, 78),
    "green": (71, 159, 104),
    "gray": (226, 232, 240),
    "line": (203, 213, 225),
}

SOURCES = [
    ("OpenAI staggered GPT-5.6 rollout report", "The Guardian", "https://www.theguardian.com/technology/2026/jun/26/openai-ai-model-release-trump-us-sam-altman-gpt-anthropic-mythos"),
    ("Anthropic/Alibaba alleged distillation report", "New York Post", "https://nypost.com/2026/06/25/business/anthropic-accuses-alibaba-of-campaign-to-rip-off-ai-capabilities/"),
    ("GitHub best month from AI coding demand", "Business Insider", "https://www.businessinsider.com/github-best-month-ever-internal-meeting-2026-6"),
    ("AI coding agents and declining human review", "Business Insider", "https://www.businessinsider.com/ai-coding-agents-cursor-human-review-2026-6"),
    ("Claude outage on June 23", "TechRadar", "https://www.techradar.com/news/live/claude-down-june-23-2026"),
    ("AI coding costs may overtake salaries by 2028", "TechRadar", "https://www.techradar.com/pro/token-discipline-will-not-emerge-through-developer-choice-alone-experts-predict-that-ai-coding-costs-will-overtake-developer-salaries-by-2028"),
    ("India AI startup Rocket funding talks", "Economic Times", "https://m.economictimes.com/tech/funding/ai-startup-rocket-in-talks-to-raise-40-50-million-sources/articleshow/132055768.cms"),
    ("Indian startup funding weekly digest", "Economic Times", "https://m.economictimes.com/tech/funding/ettech-deals-digest-creds-mega-round-lifts-startup-funding-to-1-09-billion-this-week-up-290-on-year/articleshow/132019602.cms"),
    ("Vi Business MSME Growth Insights Study coverage", "Times of India", "https://timesofindia.indiatimes.com/technology/tech-news/ai-emerges-as-key-growth-driver-for-msmes-vodafone-idea-study-finds/articleshow/132013586.cms"),
    ("MeitY and UP AI Centres of Excellence", "Times of India", "https://timesofindia.indiatimes.com/city/lucknow/meity-up-to-set-up-three-ai-centres-of-excellence-under-indiaai-mission/articleshow/132024413.cms"),
    ("EU AI Act overview", "European Union legal text", "https://eur-lex.europa.eu/eli/reg/2024/1689/oj"),
    ("EU GPAI Code of Practice", "European Commission", "https://digital-strategy.ec.europa.eu/en/policies/contents-code-gpai"),
    ("RBI FREE-AI committee report coverage", "Economic Times", "https://economictimes.indiatimes.com/news/economy/policy/rbi-panel-submits-report-on-framework-for-ai-use-to-foster-innovation-and-mitigate-risks-in-financial-sector/articleshow/123281944.cms"),
    ("SEBI Sudarshan AI enforcement coverage", "Economic Times", "https://m.economictimes.com/markets/stocks/news/sebi-deploys-ai-tool-sudarshan-removes-1-2-lakh-misleading-finfluencer-posts-tuhin-kanta-pandey/articleshow/128939153.cms"),
    ("AI chipmaker shares first-half surge", "The Guardian", "https://www.theguardian.com/business/2026/jun/29/shares-in-chipmakers-underpinning-ai-boom-surge-in-first-half-of-2026"),
    ("AI power-sector M&A boom", "Financial Times", "https://www.ft.com/content/6e15876d-1882-45e2-a13c-16a1327079d7"),
    ("Indian market June 29 snapshot", "Economic Times", "https://m.economictimes.com/markets/commodities/views/sensex-falls-50-points-nifty-above-24050-eternal-sun-pharma-techm-rise-1/articleshow/132062424.cms"),
    ("Phoenix safe GitHub issue resolution", "arXiv", "https://arxiv.org/abs/2606.20243"),
    ("Next-generation AI data center power delivery", "arXiv", "https://arxiv.org/abs/2606.25095"),
    ("AI data centers and power system sustainability", "arXiv", "https://arxiv.org/abs/2606.21064"),
    ("AI agents under EU law", "arXiv", "https://arxiv.org/abs/2604.04604"),
    ("Pragmatic approach to regulating AI agents", "arXiv", "https://arxiv.org/abs/2604.22819"),
    ("Evidence from 177,000 MCP tools", "arXiv", "https://arxiv.org/abs/2603.23802"),
]


def font(size: int, bold: bool = False):
    candidates = [
        r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\segoeuib.ttf" if bold else r"C:\Windows\Fonts\segoeui.ttf",
    ]
    for item in candidates:
        if Path(item).exists():
            return ImageFont.truetype(item, size)
    return ImageFont.load_default()


def make_visual(name: str, title: str, subtitle: str, items: list[tuple[str, int, tuple[int, int, int]]]) -> Path:
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    path = IMG_DIR / f"{name}.png"
    img = Image.new("RGB", (1400, 760), COLORS["paper"])
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((42, 42, 1358, 718), radius=28, fill=(255, 255, 255), outline=COLORS["line"], width=3)
    d.text((78, 76), title, font=font(44, True), fill=COLORS["navy"])
    d.text((80, 134), subtitle + "  |  Generated illustrative visual", font=font(25), fill=COLORS["muted"])
    x = 95
    y0 = 550
    maxv = max(v for _, v, _ in items) or 1
    bar_w = 145
    gap = 45
    for label, value, color in items:
        h = int(330 * value / maxv)
        d.rounded_rectangle((x, y0 - h, x + bar_w, y0), radius=18, fill=color)
        d.text((x, y0 + 26), "\n".join(textwrap.wrap(label, 12)), font=font(22, True), fill=COLORS["ink"])
        d.text((x + 34, y0 - h - 42), str(value), font=font(30, True), fill=color)
        x += bar_w + gap
    d.line((90, y0, 1300, y0), fill=COLORS["line"], width=3)
    img.save(path, quality=94)
    return path


VISUALS = {
    "cover": make_visual(
        "cover",
        "Founder Signal Map - 2026-06-29",
        "Regulation, agents, India demand, compute, and capital are converging",
        [
            ("Agent reliability", 78, COLORS["blue"]),
            ("India demand", 72, COLORS["teal"]),
            ("Regulatory clock", 69, COLORS["orange"]),
            ("Compute strain", 84, COLORS["red"]),
            ("Builder wedges", 88, COLORS["green"]),
        ],
    ),
    "dashboard": make_visual(
        "dashboard",
        "Opportunity / Risk / Action Scores",
        "Scores are editorial synthesis, not measured market indexes",
        [
            ("Opportunity", 87, COLORS["green"]),
            ("Risk", 72, COLORS["red"]),
            ("Actionability", 91, COLORS["blue"]),
            ("India angle", 82, COLORS["teal"]),
            ("Urgency", 78, COLORS["orange"]),
        ],
    ),
    "frontier": make_visual(
        "frontier",
        "AI Frontier Watch",
        "The frontier is moving from model demos to governed action systems",
        [
            ("Restricted release", 80, COLORS["orange"]),
            ("Coding agents", 88, COLORS["blue"]),
            ("Reliability gaps", 76, COLORS["red"]),
            ("Tool layer", 83, COLORS["teal"]),
            ("Security controls", 70, COLORS["green"]),
        ],
    ),
    "india": make_visual(
        "india",
        "India Builder Demand Surface",
        "MSMEs, fintech, sovereign AI, and state capacity are forming real demand",
        [
            ("MSME AI pull", 79, COLORS["teal"]),
            ("Startup capital", 73, COLORS["green"]),
            ("Govt AI hubs", 66, COLORS["blue"]),
            ("Fintech rules", 72, COLORS["orange"]),
            ("Local language", 81, COLORS["red"]),
        ],
    ),
    "market": make_visual(
        "market",
        "Compute Becomes Infrastructure Finance",
        "AI value is spilling into memory, grids, utilities, and power electronics",
        [
            ("Memory upside", 92, COLORS["green"]),
            ("Utility M&A", 86, COLORS["orange"]),
            ("Grid stress", 75, COLORS["red"]),
            ("Power tech", 69, COLORS["blue"]),
            ("Capex scrutiny", 78, COLORS["teal"]),
        ],
    ),
    "ideas": make_visual(
        "ideas",
        "Builder Wedge Map",
        "Highest-value wedges combine urgency, distribution, and regulatory tailwind",
        [
            ("AI cost control", 90, COLORS["blue"]),
            ("Agent audit", 86, COLORS["green"]),
            ("MSME copilots", 83, COLORS["teal"]),
            ("Compliance kits", 76, COLORS["orange"]),
            ("Grid intelligence", 64, COLORS["red"]),
        ],
    ),
}


def src(n: int) -> str:
    title, publisher, url = SOURCES[n - 1]
    return f"[S{n}: {publisher}]"


SOURCE_GROUPS = [
    ("AI frontier, labs, and coding agents", [1, 2, 3, 4, 5, 6, 18, 23]),
    ("India, regulation, and policy", [7, 8, 9, 10, 11, 12, 13, 14, 20, 21]),
    ("Markets, compute, and energy", [15, 16, 17, 19, 20]),
]


SECTIONS = [
    {
        "title": "Executive Dashboard",
        "visual": "dashboard",
        "body": [
            "Thesis of the day: the Internet is showing a practical convergence: frontier AI is being treated as regulated strategic infrastructure, coding agents are moving from novelty to budget line item, India demand is becoming more concrete in MSMEs and state AI programs, and the compute boom is spilling into memory, power, and utilities. The founder opening is not another generic chatbot. It is control planes: cost, compliance, reliability, evaluation, localization, and trust layers around AI that can act.",
            "Top 10 things Aman must know today:",
            "1. Reported US pressure around advanced model rollout suggests access gating may become a real product constraint, not a policy footnote. Builder implication: design for model diversity, delayed access, and compliance proof from day one. " + src(1),
            "2. Anthropic's alleged distillation complaint against Alibaba is a reminder that model output is now treated as strategic IP. Builder implication: prompts, logs, evals, and synthetic data pipelines need provenance and abuse monitoring. " + src(2),
            "3. GitHub's reported best month and Copilot usage-based billing show coding agents are crossing into mainstream spend. Builder implication: AI devtool finance ops is a wedge. " + src(3),
            "4. AI coding agents reaching production with less human review creates both productivity upside and latent defect/security risk. Builder implication: sell review gates, regression baselines, and explainable code provenance. " + src(4),
            "5. Claude's June 23 outage exposed dependence risk for teams building daily workflows on a single AI provider. Builder implication: failover orchestration and model SLA dashboards matter. " + src(5),
            "6. Analysts warning about token spend exceeding developer salaries by 2028 crystallizes the 'AI cost governance' category. Builder implication: token budgets, policy routing, and usage anomaly alerts can be sold to CTOs. " + src(6),
            "7. Indian MSMEs are reported to be adopting AI meaningfully, with 25 percent already using it and 57 percent seeing it as essential to growth. Builder implication: verticalized, vernacular, low-friction AI automation for MSMEs is no longer premature. " + src(9),
            "8. Indian startup funding showed a large weekly jump, and a Surat AI app-building startup is reportedly discussing a $40-50 million raise. Builder implication: Indian AI application companies are investable if distribution is credible. " + src(7) + " " + src(8),
            "9. EU AI Act enforcement and GPAI code timelines keep turning compliance into a product surface. Builder implication: agent inventory, data-flow maps, transparency reports, and watermarking systems will be bought by non-EU companies too. " + src(11) + " " + src(12),
            "10. AI compute is now a power-market story: chipmaker shares, memory, data center power delivery, and utility M&A are all connected. Builder implication: AI infrastructure intelligence, energy-aware scheduling, and procurement tools become founder terrain. " + src(15) + " " + src(16) + " " + src(19),
            "Scores: opportunity 87/100, risk 72/100, actionability 91/100. High opportunity because buyers now have urgent pains; high risk because platform access, reliability, and compliance are unstable; high actionability because several wedges can be validated in 48 hours with interviews, prototypes, and public data.",
        ],
    },
    {
        "title": "Calendar And Personal Operating Context",
        "body": [
            "Calendar access: unavailable in this automation run. I searched for available calendar connector tools and none were exposed for Google Calendar or a local calendar source. This section therefore cannot verify Aman's commitments, conflicts, travel buffers, or meeting prep needs.",
            "Operating priority for today: run one validation sprint around AI cost/reliability governance for builders or MSMEs. The strongest evidence cluster today is that coding agents are being adopted rapidly while costs, outages, and review quality are becoming painful.",
            "Personal leverage points: 1. Use India as the proving ground: local MSMEs and AI-forward startups need practical workflows, not abstract AI strategy. 2. Use founder speed: ship a visible dashboard or audit script today. 3. Use content as distribution: publish a teardown of why usage-based AI coding spend needs FinOps-style controls.",
            "Risks to manage: avoid building too broad a platform. Pick a narrow trigger such as 'which AI coding tool consumed the most tokens per merged PR this week?' or 'which agent PRs bypassed review and failed CI?'",
        ],
    },
    {
        "title": "The World Changed Overnight",
        "visual": "market",
        "body": [
            "Fact: AI-linked hardware and memory names are reportedly pulling investor attention away from some software names, while utilities are seeing record AI-driven M&A activity. Analysis: the AI stack is no longer only SaaS and model APIs; the money is following bottlenecks - memory, power, substations, interconnects, and cooling. " + src(15) + " " + src(16),
            "Builder relevance: when infrastructure bottlenecks get financialized, downstream buyers need forecasting, procurement, and optimization software. A founder in India can watch global bottlenecks and build localized versions for Indian data centers, cloud resellers, universities, and AI labs.",
            "Second-order effect: as grid and chip constraints rise, inference efficiency becomes a sales feature. Products that can prove 'same outcome, fewer tokens/watts/rupees' will beat products that only promise better answers.",
            "Fact: Indian markets were mixed today amid oil/geopolitical tension, with Nifty above 24,050 in early coverage. Analysis: macro uncertainty matters because AI builders selling to Indian SMEs and enterprises should expect budget scrutiny, not blank-check experimentation. " + src(17),
            "Contrarian read: the biggest AI opportunity today may be boring accounting around AI usage, review, and compliance. The spectacle is model capability; the budget holder's pain is unpredictability.",
        ],
    },
    {
        "title": "AI Frontier Watch",
        "visual": "frontier",
        "body": [
            "Fact: press reports describe a staggered release of OpenAI's newer model after US government engagement. Treat this as reported information, not direct primary confirmation from OpenAI in this run. Analysis: even if details evolve, the directional signal is strong: frontier model access is becoming conditional on national-security and policy review. " + src(1),
            "Founder implication: model abstraction is no longer a technical nicety. Products need provider routing, fallback, audit logs, and customer-visible controls for when a frontier capability is delayed, region-gated, or terms-restricted.",
            "Fact: Anthropic reportedly accused Alibaba-linked operators of a large distillation campaign. Analysis: this makes 'AI supply-chain security' wider than model weights. It includes account creation, usage anomalies, training data provenance, and evidence trails for model-output-derived data. " + src(2),
            "Fact: the June 23 Claude outage hit chat, Claude Code, and API surfaces for many users. Analysis: single-provider AI workflows now have classic enterprise availability risk. " + src(5),
            "Technical signal: the Phoenix paper proposes multi-agent GitHub issue resolution with safety controls, baseline tests, and webhook state machines. It reports promising results on a curated slice but admits localization failures. Builder implication: the market needs practical guardrails more than another autonomous agent demo. " + src(18),
            "Technical signal: research on public MCP tools found software development dominating usage and 'action' tools rising. Analysis: the tool layer is where risk and product opportunity concentrate, because agents now write files, send emails, access finance systems, and interact with external APIs. " + src(23),
        ],
    },
    {
        "title": "AI Giants Pulse",
        "body": [
            "OpenAI: today's actionable signal is access governance. The reported staggered release should be tracked against official OpenAI posts, API changelogs, and model availability pages. Builder action: never hardcode a launch plan around a single frontier model becoming universally available on a promised date.",
            "Anthropic: reliability and IP-defense are both in focus: outage recovery on one side, distillation allegations on the other. Builder action: if building on Claude or Claude Code, create a provider outage runbook and customer-facing degradation mode. " + src(2) + " " + src(5),
            "GitHub/Microsoft: reported Copilot demand and usage-based billing reinforce that coding assistance is becoming metered infrastructure. Builder action: create a Copilot/Cursor/Claude Code/Codex cost ledger per repo, PR, team, and task type. " + src(3),
            "Google/Meta/NVIDIA: no fresh primary announcement was verified in this run, but today's market and infrastructure signals keep NVIDIA-adjacent memory/power ecosystems important. Builder action: watch data center power and memory constraints as leading indicators for API price changes. " + src(15) + " " + src(19),
            "Important limitation: leader posts from X/Twitter were not directly accessible through a reliable logged-in connector in this run. I used accessible web reports, official/legal pages, and arXiv instead of fabricating social chatter.",
        ],
    },
    {
        "title": "Regulation And Policy Radar",
        "body": [
            "EU: the AI Act remains the most concrete near-term compliance driver. GPAI obligations started applying earlier, while enforcement milestones and adjacent transparency obligations create an implementation clock. The General-Purpose AI Code of Practice provides an operational map around transparency, copyright, and safety/security. " + src(11) + " " + src(12),
            "Agent-specific regulation: two recent arXiv papers argue that agentic systems raise obligations beyond the underlying model because they plan, use tools, alter external systems, and can create contractual or safety consequences. Builder implication: agent products need task inventories, authorization tiers, logs, and rollback controls. " + src(20) + " " + src(21),
            "India finance: RBI's FREE-AI direction and SEBI's AI-assisted finfluencer enforcement signal a dual market: regulators will use AI, and regulated firms will need proof that their AI use is responsible. " + src(13) + " " + src(14),
            "India state capacity: MeitY and Uttar Pradesh's reported plan for three AI Centres of Excellence under IndiaAI Mission suggests the public-sector AI demand funnel is widening beyond Delhi/Bengaluru. Builder implication: sell training, evaluation, data labeling, Indic language workflows, and governance kits to state-linked institutions. " + src(10),
            "Founder implication: compliance should be productized as defaults, not a PDF appendix. The wedge is a dashboard that answers: what actions can the agent take, who authorized them, what data did it touch, what model/provider was used, and what evidence can be shown to a regulator or customer.",
        ],
    },
    {
        "title": "Community Pain Map",
        "body": [
            "Pain 1 - AI coding spend shock: usage-based pricing is becoming normal, but teams lack token-level accountability by feature, PR, repo, and developer. Evidence comes from GitHub billing shift and analyst warnings about token discipline. " + src(3) + " " + src(6),
            "Pain 2 - unreliable AI work dependencies: outages interrupt coding, customer support, and agent workflows. Teams need graceful degradation rather than Slack panic. " + src(5),
            "Pain 3 - review fatigue and trust gap: AI-generated code can reach production with less human review, but managers still need accountability. " + src(4),
            "Pain 4 - agent permission anxiety: public MCP/tool research shows action tools are rising, including consequential tasks. Operators need fine-grained permissions and auditability. " + src(23),
            "Pain 5 - India MSME implementation gap: many MSMEs believe AI matters, but lack process design, local-language onboarding, and ROI measurement. " + src(9),
            "Pain 6 - regulatory ambiguity for AI agents: founders do not know whether their agent is just a UI, a high-risk AI system, an outsourced processor, or a contractual actor. " + src(20) + " " + src(21),
            "Pain 7 - compute/power opacity: AI infra buyers cannot easily forecast whether model choice, memory prices, or energy prices will break unit economics. " + src(15) + " " + src(16) + " " + src(19),
        ],
    },
    {
        "title": "Market And Money Signals",
        "visual": "india",
        "body": [
            "India startup capital: ET reported Indian startups raised about $1.09 billion in the week ending June 26, helped by a large CRED round. This is not a pure AI signal, but it suggests risk capital is not frozen. " + src(8),
            "India AI apps: Surat-based Rocket is reportedly discussing a $40-50 million round at around a $500 million valuation. Analysis: investor appetite is expanding beyond Bengaluru/US-style model labs into AI application builders. " + src(7),
            "MSME pull: Vi Business's MSME study coverage reports that 57 percent of MSMEs see AI as essential and 25 percent have integrated AI. Inference: SMB buyers may be ready for packaged AI if it maps to cashflow, customer acquisition, compliance, inventory, or collections. " + src(9),
            "Compute finance: chipmaker and memory surges plus utility M&A show AI capex is pushing value into physical infrastructure. " + src(15) + " " + src(16),
            "India macro watch: oil/geopolitical tension can tighten discretionary spend. Founder implication: pitch cost savings, revenue recovery, and compliance risk reduction before 'AI transformation'. " + src(17),
        ],
    },
    {
        "title": "Technical Opportunity Map",
        "body": [
            "1. Safe multi-agent GitHub workflows: Phoenix's design points to webhook-driven state machines, baseline-aware tests, layered safety controls, and explicit failure analysis. Product wedge: a GitHub app that refuses to merge agent PRs unless baseline, tests, secret scanning, and ownership checks pass. " + src(18),
            "2. AI data center power delivery: the recent power-delivery paper highlights shifts beyond traditional 48 V architectures. Product wedge: knowledge base and procurement assistant for data center teams evaluating power electronics vendors. " + src(19),
            "3. Sustainability/load scheduling: AI data center sustainability research frames both risks and flexibility opportunities. Product wedge: carbon-aware, price-aware inference routing for enterprise batch jobs. " + src(20),
            "4. Agent compliance architecture: EU-law papers converge on external-action inventory, data-flow maps, human oversight, and drift monitoring. Product wedge: 'agent bill of materials' generator. " + src(20) + " " + src(21),
            "5. MCP/tool observability: public MCP tool growth implies a new artifact to scan: tool manifests. Product wedge: MCP risk scanner that classifies actions by data sensitivity, write capability, financial/legal impact, and required approval level. " + src(23),
            "6. AI coding cost telemetry: usage-based billing creates a missing analytics layer. Product wedge: extension or CLI that estimates token spend per task and recommends cheaper model/routing policies. " + src(3) + " " + src(6),
        ],
    },
    {
        "title": "Personal Impact Analysis For Aman",
        "body": [
            "Positive effects: Aman's geography is an advantage if he targets Indian MSMEs, state AI programs, BFSI compliance, and Indic language workflows. These buyers need pragmatic builders who understand local constraints and global AI tools.",
            "Negative effects: global AI platform volatility can break demos, pricing, and product margins. A startup built as a thin wrapper around one provider is fragile.",
            "Skill gaps to close: AI FinOps, agent permissions, evaluation design, enterprise procurement language, RBI/SEBI/DPDP basics, and local-language UX research.",
            "Threats: big platforms can copy broad agent dashboards. To defend, own narrow workflows, local data, integrations, and trust. Example: 'AI coding cost governance for Indian dev agencies using GitHub, Cursor, Claude Code, and Codex' is sharper than 'AI productivity platform'.",
            "What to ignore today: generic AGI discourse, undifferentiated prompt libraries, and product ideas that require frontier-model access before any customer validation.",
        ],
    },
    {
        "title": "Billion-Dollar Problem Radar",
        "visual": "ideas",
        "body": [
            "1. AI DevTool FinOps. Problem: coding-agent spend becomes unpredictable under usage-based pricing. Customer: CTOs, engineering managers, dev agencies. Evidence: GitHub usage-based billing and analyst warnings. Urgency: rising now. Why now: agent usage is moving into production workflows. Wedge MVP: GitHub app that maps AI usage estimates to PRs and teams. Distribution: dev Twitter, GitHub Marketplace, agency partnerships. Pricing: $20/user/month plus team analytics. Moat: repo-level historical cost/outcome dataset. Competitors: platform-native dashboards, CloudZero-style FinOps. Key risk: access to token telemetry. 48-hour validation: interview 10 CTOs; scrape invoices manually from 3 teams. Action today: build a mock dashboard with sample PR cost attribution. " + src(3) + " " + src(6),
            "2. Agent Review Gate. Problem: AI code reaches production with declining human review. Customer: regulated engineering teams. Evidence: AI code production trend plus Phoenix safety-control research. Wedge MVP: required GitHub check for agent-authored PRs. Distribution: security communities, SOC2 consultants. Pricing: $99/repo/month. Moat: policy templates and failure dataset. Risk: dev friction. Validation: ask teams what would make them trust agent PRs. Action today: create a GitHub Action that labels agent PRs and blocks risky paths. " + src(4) + " " + src(18),
            "3. Model Outage Router. Problem: Claude/OpenAI outages break workflows. Customer: AI-native teams, support automation vendors. Evidence: Claude outage. Wedge MVP: provider health + automatic fallback + customer SLA page. Distribution: Vercel/Next.js templates, AI SaaS groups. Pricing: $49/month starter, usage add-on. Moat: incident history and routing policies. Risk: provider-specific behavior differences. Validation: talk to 5 teams that were disrupted June 23. Action today: prototype a tiny SDK wrapper with fallback logs. " + src(5),
            "4. Agent Compliance BOM. Problem: founders cannot explain what their agents can do. Customer: AI SaaS companies selling to EU/India enterprises. Evidence: EU agent-law research. Wedge MVP: scanner that creates an Agent Bill of Materials: tools, permissions, models, data, approval tiers. Distribution: compliance advisors and AI agencies. Pricing: $500 audit plus SaaS. Moat: regulatory mappings. Risk: legal accuracy. Validation: offer free ABOM review to 3 AI startups. Action today: draft a one-page ABOM template. " + src(20) + " " + src(21),
            "5. MSME Voice Workflow Copilot. Problem: Indian MSMEs want AI but lack workflow design. Customer: retailers, clinics, coaching centers, small manufacturers. Evidence: MSME AI adoption data. Wedge MVP: WhatsApp/voice assistant for follow-ups, invoices, stock reminders in Hindi/English plus local language. Distribution: CA networks, telecom partners, local SaaS resellers. Pricing: Rs 999-4999/month. Moat: vertical playbooks and local language datasets. Risk: support burden. Validation: visit/call 20 MSMEs and sell a concierge prototype. Action today: pick one vertical and script the workflow. " + src(9),
            "6. SEBI/RBI AI Governance Kit. Problem: BFSI firms need responsible AI controls while regulators use AI enforcement. Customer: fintechs, brokers, lenders. Evidence: FREE-AI and SEBI Sudarshan signals. Wedge MVP: policy pack + monitoring checklist + model decision log. Distribution: fintech compliance consultants. Pricing: Rs 50k implementation plus subscription. Moat: India-specific templates. Risk: legal review needed. Validation: ask 5 fintech compliance leads what evidence auditors ask for. Action today: map RBI principles into a product checklist. " + src(13) + " " + src(14),
            "7. AI Infrastructure Intelligence India. Problem: cloud/data-center buyers cannot see compute, memory, power, and regulatory bottlenecks. Customer: AI labs, cloud resellers, campuses, enterprises. Evidence: memory/utility/power signals. Wedge MVP: weekly dashboard of GPU availability, memory prices, power constraints, and vendor lead times. Distribution: paid newsletter plus API. Pricing: $99/month. Moat: proprietary quotes and local supplier data. Risk: data collection. Validation: call 10 infra buyers. Action today: create a sample dashboard from public sources. " + src(15) + " " + src(16) + " " + src(19),
            "8. MCP Risk Scanner. Problem: action tools are expanding without governance. Customer: AI teams deploying MCP/tool servers. Evidence: 177,000 MCP tool study. Wedge MVP: CLI scans tool manifests and classifies read/write/financial/legal/data risks. Distribution: open-source core. Pricing: enterprise policy engine. Moat: risk taxonomy. Risk: standard fragmentation. Validation: scan 50 public MCP servers and publish a report. Action today: write the taxonomy. " + src(23),
        ],
    },
    {
        "title": "Micro-Opportunities",
        "body": [
            "1. Chrome extension that estimates AI coding prompt cost before sending.",
            "2. GitHub Action that labels PRs likely written by agents and requires owner review for sensitive files.",
            "3. Public leaderboard of AI provider outage minutes and degraded-mode docs.",
            "4. Notion template: Agent Bill of Materials for SaaS founders.",
            "5. Indian MSME AI ROI calculator in Hindi/English.",
            "6. CLI that inventories MCP tools and flags write-capable actions.",
            "7. Content series: 'AI FinOps teardown' using anonymized invoices.",
            "8. Dataset of AI coding failure modes from public GitHub Actions logs.",
            "9. Compliance explainer for EU AI Act Article 50 synthetic-content transparency.",
            "10. WhatsApp bot template for collections follow-up and invoice reminders for small businesses.",
        ],
    },
    {
        "title": "Contrarian Corner",
        "body": [
            "1. Most people may be overrating model launches and underrating access governance. If frontier releases become gated, the winner is not the app with the newest model; it is the app that degrades gracefully and proves compliance.",
            "2. AI coding may not reduce engineering management workload soon. It may shift work from writing code to policing cost, review quality, CI failures, and production accountability.",
            "3. India's near-term AI opportunity may be less about training a global frontier model and more about operationalizing AI in MSMEs, public services, fintech compliance, and local language workflows.",
            "Uncertainty: several current items are press reports rather than primary-source announcements. Treat them as directional signals, not final facts, until official pages confirm details.",
        ],
    },
    {
        "title": "Watchlist",
        "body": [
            "People: Sam Altman, Dario Amodei, Jensen Huang, Satya Nadella, Aravind Srinivas, Alexandr Wang, Kunal Shah, Indian MeitY/RBI/SEBI officials.",
            "Companies: OpenAI, Anthropic, GitHub, Cursor/Anysphere, Google DeepMind, Meta AI, NVIDIA, Micron, SK Hynix, Sarvam AI, Rocket, CRED, major Indian cloud/data-center players.",
            "Repos/tools: MCP servers, AI code review bots, GitHub Actions for agent PRs, model routers, AI cost dashboards.",
            "Papers: Phoenix, MCP tool evidence, AI agents under EU law, data center power delivery, AI data center sustainability.",
            "Policy clocks: EU AI Act transparency and GPAI enforcement dates, India FREE-AI movement, SEBI finfluencer enforcement, DPDP implementation details, US frontier-model access policy.",
            "Communities: Hacker News AI coding threads, r/LocalLLaMA, r/SaaS, r/IndianStartups, Product Hunt AI launches, GitHub issues for agent frameworks.",
        ],
    },
    {
        "title": "Today's Action Plan",
        "body": [
            "15-minute actions: 1. Create a one-page AI DevTool FinOps landing page headline. 2. Draft 5 CTO interview questions on AI coding spend. 3. Bookmark the EU AI Act/GPAI and RBI FREE-AI source pages. 4. Post a short insight: 'AI coding's next bottleneck is budget governance, not code generation.'",
            "1-hour actions: 1. Build a spreadsheet model estimating AI coding cost per PR. 2. Write a sample Agent Bill of Materials for one of Aman's own tools. 3. Call or message 5 Indian dev agencies/MSME owners about AI workflow pains. 4. Prototype a GitHub Action that marks agent-authored PRs.",
            "Deep-work actions: 1. Build an MVP dashboard with repo, PR, tool, estimated cost, review status, and CI result. 2. Publish a mini-report on AI coding cost/reliability using today's cited evidence. 3. Design a WhatsApp-first MSME workflow copilot for one vertical with a concierge backend.",
            "Ranked priority: start with AI DevTool FinOps because it has global demand, visible pain, buyer urgency, and can be validated without waiting for platform permissions.",
        ],
    },
    {
        "title": "Methodology And Limitations",
        "body": [
            "Scanned: accessible web search results, news coverage, official/legal EU sources, India regulatory/news coverage, arXiv papers, market coverage, and automation memory from the prior run. Prior memory was used to avoid repeating yesterday's main thesis unless today's evidence changed it.",
            "Unavailable: Aman's live calendar; logged-in X/Twitter feeds; private Discords/Slack groups; paywalled article full text where only snippets were accessible; direct Google Calendar or email connectors.",
            "Evidence labeling: facts are tied to cited sources; analysis and founder implications are my synthesis; speculation is explicitly marked where used. Several late-June 2026 items are press reports and should be checked against primary company pages as they appear.",
        ],
    },
]


def build_markdown() -> str:
    lines = [
        "# Daily Internet Intelligence Dossier - 2026-06-29",
        "",
        f"Prepared for Aman. Generated at {RUN_TIME}.",
        "",
        "## Thesis Of The Day",
        "Frontier AI is being pulled into governance, coding agents are becoming metered infrastructure, Indian AI demand is becoming more practical, and compute scarcity is moving into memory and power markets. The opportunity is to build control planes around AI action: cost, compliance, reliability, localization, and evidence.",
        "",
    ]
    for section in SECTIONS:
        lines.append(f"## {section['title']}")
        for para in section["body"]:
            lines.append("")
            lines.append(para)
        lines.append("")
    lines.append("## Source Appendix")
    seen = set()
    for group, indexes in SOURCE_GROUPS:
        lines.append("")
        lines.append(f"### {group}")
        for i in indexes:
            if i in seen:
                continue
            seen.add(i)
            title, publisher, url = SOURCES[i - 1]
            lines.append(f"{i}. [{title} - {publisher}]({url})")
    remaining = [i for i in range(1, len(SOURCES) + 1) if i not in seen]
    if remaining:
        lines.append("")
        lines.append("### Additional sources")
        for i in remaining:
            title, publisher, url = SOURCES[i - 1]
            lines.append(f"{i}. [{title} - {publisher}]({url})")
    return "\n".join(lines) + "\n"


class PDFBuilder:
    def __init__(self, path: Path):
        self.doc = fitz.open()
        self.path = path
        self.page = None
        self.y = 0
        self.page_no = 0
        self.margin = 54
        self.width = 595
        self.height = 842

    def add_page(self, title: str | None = None):
        self.page = self.doc.new_page(width=self.width, height=self.height)
        self.page_no += 1
        self.page.draw_rect(fitz.Rect(0, 0, self.width, self.height), color=None, fill=(0.985, 0.98, 0.965))
        self.y = self.margin
        if self.page_no > 1:
            self.page.insert_text((self.margin, 28), "Daily Internet Intelligence Dossier - 2026-06-29", fontsize=8, color=(0.35, 0.40, 0.47))
            self.page.insert_text((self.width - 82, self.height - 28), f"{self.page_no}", fontsize=8, color=(0.35, 0.40, 0.47))
        if title:
            self.heading(title)

    def ensure(self, needed: float):
        if self.page is None or self.y + needed > self.height - 60:
            self.add_page()

    def heading(self, text: str):
        self.ensure(50)
        self.page.insert_text((self.margin, self.y), text, fontsize=18, fontname="helv", color=(0.06, 0.17, 0.29))
        self.y += 28
        self.page.draw_line((self.margin, self.y), (self.width - self.margin, self.y), color=(0.80, 0.84, 0.89), width=0.8)
        self.y += 16

    def paragraph(self, text: str, size: int = 9, leading: float = 12.5, indent: int = 0):
        max_chars = 102 if size <= 9 else 86
        wrapper = textwrap.TextWrapper(width=max_chars - indent, break_long_words=False, replace_whitespace=False)
        lines = []
        for raw in text.split("\n"):
            lines.extend(wrapper.wrap(raw) or [""])
        block_h = max(leading * len(lines) + 5, 16)
        self.ensure(block_h)
        y = self.y
        for line in lines:
            self.page.insert_text((self.margin + indent * 4, y), line, fontsize=size, fontname="helv", color=(0.12, 0.16, 0.22))
            y += leading
        self.y = y + 5

    def image(self, path: Path, h: int = 210):
        self.ensure(h + 18)
        rect = fitz.Rect(self.margin, self.y, self.width - self.margin, self.y + h)
        self.page.insert_image(rect, filename=str(path), keep_proportion=True)
        self.y += h + 14

    def callout(self, text: str):
        self.ensure(90)
        rect = fitz.Rect(self.margin, self.y, self.width - self.margin, self.y + 78)
        self.page.draw_rect(rect, color=(0.78, 0.84, 0.90), fill=(0.93, 0.97, 1.0), width=0.8)
        old_y = self.y
        self.y += 18
        self.paragraph(text, size=10, leading=14, indent=2)
        self.y = max(self.y, old_y + 90)

    def source_link(self, idx: int, title: str, publisher: str, url: str):
        self.ensure(38)
        label = f"S{idx}. {title} - {publisher}"
        x = self.margin
        y = self.y
        self.page.insert_text((x, y), label, fontsize=9, color=(0.05, 0.30, 0.68))
        rect = fitz.Rect(x, y - 10, self.width - self.margin, y + 4)
        self.page.insert_link({"kind": fitz.LINK_URI, "from": rect, "uri": url})
        self.y += 14
        self.paragraph(url, size=7, leading=9, indent=2)

    def save(self):
        self.doc.save(self.path)
        self.doc.close()


def build_pdf():
    b = PDFBuilder(PDF_PATH)
    b.add_page()
    b.page.insert_text((54, 88), "Daily Internet", fontsize=38, fontname="helv", color=(0.06, 0.17, 0.29))
    b.page.insert_text((54, 132), "Intelligence Dossier", fontsize=38, fontname="helv", color=(0.06, 0.17, 0.29))
    b.page.insert_text((54, 172), "2026-06-29 | Prepared for Aman", fontsize=13, color=(0.36, 0.42, 0.50))
    b.y = 206
    b.image(VISUALS["cover"], h=270)
    b.callout("Thesis: frontier AI is becoming governed infrastructure, coding agents are becoming metered work systems, India demand is becoming practical, and compute scarcity is becoming a power-and-memory market. Build control planes around AI action: cost, compliance, reliability, localization, and evidence.")
    b.paragraph(f"Generated at {RUN_TIME}. Visuals are generated illustrative visuals created for this dossier.", size=8, leading=11)

    for section in SECTIONS:
        b.add_page(section["title"])
        if "visual" in section:
            b.image(VISUALS[section["visual"]], h=210)
        for para in section["body"]:
            if para.endswith(":"):
                b.paragraph(para, size=10, leading=13)
            else:
                b.paragraph(para, size=8.7, leading=12.1)

    b.add_page("Source Appendix")
    b.paragraph("Clickable source list grouped for verification. Some current items were available only through accessible news coverage or snippets; primary official pages are preferred where available.", size=9)
    seen = set()
    for group, indexes in SOURCE_GROUPS:
        b.heading(group)
        for i in indexes:
            if i in seen:
                continue
            seen.add(i)
            title, publisher, url = SOURCES[i - 1]
            b.source_link(i, title, publisher, url)
    remaining = [i for i in range(1, len(SOURCES) + 1) if i not in seen]
    if remaining:
        b.heading("Additional sources")
        for i in remaining:
            title, publisher, url = SOURCES[i - 1]
            b.source_link(i, title, publisher, url)
    b.save()


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    MD_PATH.write_text(build_markdown(), encoding="utf-8")
    build_pdf()
    print(PDF_PATH)
    print(MD_PATH)


if __name__ == "__main__":
    main()
