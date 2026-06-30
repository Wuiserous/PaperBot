from __future__ import annotations

import sys
from pathlib import Path
from textwrap import dedent

ROOT = Path(__file__).resolve().parents[2]
VENDOR = ROOT / ".vendor"
if VENDOR.exists():
    sys.path.insert(0, str(VENDOR))

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Flowable,
    KeepTogether,
)


DATE = "2026-06-30"
OUT_DIR = Path("reports/daily-intelligence")
PDF_PATH = OUT_DIR / f"{DATE}-daily-internet-intelligence-dossier.pdf"
MD_PATH = OUT_DIR / f"{DATE}-daily-internet-intelligence-dossier.md"


SOURCES = [
    ("OpenAI news index", "https://openai.com/news/"),
    ("OpenAI GPT-5.6 Sol preview", "https://openai.com/index/previewing-gpt-5-6-sol/"),
    ("OpenAI Broadcom Jalapeno chip", "https://openai.com/index/openai-broadcom-jalapeno-inference-chip/"),
    ("Anthropic newsroom", "https://www.anthropic.com/news"),
    ("Anthropic Claude Tag", "https://www.anthropic.com/news/introducing-claude-tag"),
    ("Anthropic AI-enabled cyber threats", "https://www.anthropic.com/news/AI-enabled-cyber-threats-mitre-attack"),
    ("Google DeepMind news", "https://deepmind.google/blog/"),
    ("Gemini API release notes", "https://ai.google.dev/gemini-api/docs/changelog"),
    ("Meta AI blog", "https://ai.meta.com/blog/"),
    ("GitHub changelog", "https://github.blog/changelog/"),
    ("GitHub Trending today", "https://github.com/trending?since=daily"),
    ("Vercel changelog", "https://vercel.com/changelog"),
    ("Product Hunt today", "https://www.producthunt.com/"),
    ("EU AI Act official page", "https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai"),
    ("RBI bulletin index", "https://www.rbi.org.in/Scripts/BS_ViewBulletin.aspx"),
    ("IndiaAI Mission coverage - ET", "https://m.economictimes.com/tech/artificial-intelligence/20-foundational-ai-models-created-under-indiaai-mission-5-released-meity-secretary/articleshow/131690791.cms"),
    ("IndiaAI UP CoE coverage - TOI", "https://timesofindia.indiatimes.com/city/lucknow/meity-up-to-set-up-three-ai-centres-of-excellence-under-indiaai-mission/articleshow/132024413.cms"),
]


class SignalVisual(Flowable):
    def __init__(self, title: str, labels: list[str], values: list[int], caption: str):
        super().__init__()
        self.title = title
        self.labels = labels
        self.values = values
        self.caption = caption
        self.width = 16.5 * cm
        self.height = 5.0 * cm

    def draw(self):
        c = self.canv
        w, h = self.width, self.height
        c.setFillColor(colors.HexColor("#F6F8FA"))
        c.roundRect(0, 0, w, h, 8, fill=1, stroke=0)
        c.setFillColor(colors.HexColor("#111827"))
        c.setFont("Helvetica-Bold", 11)
        c.drawString(0.45 * cm, h - 0.6 * cm, self.title)
        max_v = max(self.values) if self.values else 1
        left = 0.55 * cm
        top = h - 1.15 * cm
        bar_w = (w - 1.2 * cm) / len(self.values)
        palette = ["#2563EB", "#059669", "#DC2626", "#7C3AED", "#EA580C", "#0891B2"]
        for i, (label, value) in enumerate(zip(self.labels, self.values)):
            x = left + i * bar_w
            bh = (value / max_v) * 2.1 * cm
            c.setFillColor(colors.HexColor(palette[i % len(palette)]))
            c.roundRect(x + 0.15 * cm, top - bh, bar_w - 0.3 * cm, bh, 3, fill=1, stroke=0)
            c.setFillColor(colors.HexColor("#111827"))
            c.setFont("Helvetica-Bold", 8)
            c.drawCentredString(x + bar_w / 2, top - bh - 0.35 * cm, str(value))
            c.setFont("Helvetica", 7)
            c.drawCentredString(x + bar_w / 2, 0.82 * cm, label[:18])
        c.setFillColor(colors.HexColor("#4B5563"))
        c.setFont("Helvetica-Oblique", 7.5)
        c.drawString(0.45 * cm, 0.35 * cm, self.caption)


def styles():
    base = getSampleStyleSheet()
    base.add(ParagraphStyle("CoverTitle", parent=base["Title"], fontName="Helvetica-Bold", fontSize=27, leading=32, textColor=colors.HexColor("#111827"), alignment=TA_CENTER, spaceAfter=12))
    base.add(ParagraphStyle("Sub", parent=base["Normal"], fontSize=10.5, leading=15, textColor=colors.HexColor("#374151"), alignment=TA_CENTER))
    base.add(ParagraphStyle("H1x", parent=base["Heading1"], fontSize=17, leading=22, textColor=colors.HexColor("#111827"), spaceBefore=16, spaceAfter=8))
    base.add(ParagraphStyle("H2x", parent=base["Heading2"], fontSize=12.5, leading=16, textColor=colors.HexColor("#1F2937"), spaceBefore=10, spaceAfter=5))
    base.add(ParagraphStyle("Bodyx", parent=base["BodyText"], fontSize=9.1, leading=12.8, textColor=colors.HexColor("#111827"), spaceAfter=5))
    base.add(ParagraphStyle("Smallx", parent=base["BodyText"], fontSize=7.6, leading=9.4, textColor=colors.HexColor("#374151")))
    base.add(ParagraphStyle("Cell", parent=base["BodyText"], fontSize=7.8, leading=9.6, textColor=colors.HexColor("#111827")))
    base.add(ParagraphStyle("Th", parent=base["BodyText"], fontName="Helvetica-Bold", fontSize=7.7, leading=9.4, textColor=colors.white, alignment=TA_LEFT))
    return base


ST = styles()


def p(text, style="Bodyx"):
    return Paragraph(text, ST[style])


def table(rows, widths=None, header=True):
    data = []
    for r_i, row in enumerate(rows):
        style = "Th" if header and r_i == 0 else "Cell"
        data.append([Paragraph(str(cell), ST[style]) for cell in row])
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0, hAlign="LEFT")
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111827") if header else colors.white),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white if header else colors.HexColor("#111827")),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D1D5DB")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9FAFB")]),
    ]))
    return t


def source_link(name, url):
    return f'<a href="{url}" color="blue">{name}</a>'


def build_story():
    story = []

    story += [
        Spacer(1, 2.0 * cm),
        p("Daily Internet Intelligence Dossier", "CoverTitle"),
        p("For Aman - 30 June 2026 - India builder lens, global scan", "Sub"),
        Spacer(1, 0.6 * cm),
        SignalVisual("Generated visual: today's signal stack", ["Frontier", "Agents", "Policy", "Security", "India", "Demand"], [91, 94, 84, 88, 73, 89], "Generated original illustration, not a news image."),
        Spacer(1, 0.8 * cm),
        p("<b>Thesis of the day:</b> The frontier is shifting from model spectacle to governed, instrumented agent deployment. OpenAI's phased GPT-5.6 preview and chip move, Anthropic's Slack-native Claude Tag, Google's computer-use API, Vercel's agent-stack releases, and GitHub's Copilot controls all point to the same market need: teams want agents, but they need permissioning, memory, spend controls, evals, security boundaries, and operational visibility. For an India-based founder, the opening is not to clone a model lab; it is to build trusted agent infrastructure, vernacular workflow automation, and compliance-ready deployment rails for businesses that cannot absorb frontier-lab complexity."),
        PageBreak(),
    ]

    story += [
        p("Executive Dashboard", "H1x"),
        table([
            ["Rank", "What Aman must know", "Builder interpretation", "Score"],
            ["1", "OpenAI previewed GPT-5.6 Sol/Terra/Luna with phased government-coordinated access, stronger cyber safeguards, new reasoning modes, and pricing tiers.", "Access control and release governance are now product surfaces. Build audit, policy, and procurement wrappers.", "Opportunity 9 / Risk 8 / Action 9"],
            ["2", "OpenAI and Broadcom unveiled Jalapeno, an inference accelerator planned for gigawatt-scale deployment.", "Inference economics are becoming strategic IP. India startups should optimize around routing, caching, and workload selection.", "8 / 7 / 7"],
            ["3", "Anthropic launched Claude Tag for Slack with scoped memories, channel permissions, spend limits, logs, and asynchronous work.", "This validates agent control planes for the messy workplace. SMB-grade versions are underbuilt.", "10 / 7 / 10"],
            ["4", "Anthropic mapped 832 banned cyber-abuse accounts and argues AI attacker scaffolding is outgrowing existing security taxonomies.", "AI security is moving from prompt safety to workflow detection. Defensive agent telemetry is a product category.", "9 / 9 / 9"],
            ["5", "Google's Gemini API added public-preview computer-use tooling with browser/mobile/desktop actions and prompt-injection detection.", "Browser agents are becoming a default capability. The moat shifts to reliability, permissions, and domain data.", "9 / 8 / 9"],
            ["6", "GitHub Copilot and Vercel shipped enterprise controls, observability, gateway, realtime voice, and agent harness updates.", "Developer-tool buyers now expect AI spend and agent behavior to be measurable.", "8 / 6 / 8"],
            ["7", "Product Hunt and GitHub trending show demand around agent memory, open-model Cline access, bookkeeping agents, voice, and agency-in-a-box templates.", "Pain is not 'no AI'. Pain is context loss, trust, fragmented tools, and repeated explanation.", "8 / 5 / 9"],
            ["8", "EU AI Act transparency rules become active in August 2026; GPAI obligations are already active, with more high-risk deadlines later.", "Export-facing Indian AI products need provenance, labeling, logs, and documentation now.", "7 / 8 / 8"],
            ["9", "IndiaAI activity continues via foundation-model releases and state AI centers, but execution bottlenecks remain visible in funding/IP/process reporting.", "India-specific wedge: multilingual workflow AI plus government/regulated-sector deployment services.", "8 / 6 / 7"],
            ["10", "Meta's latest official item is brain-to-text research, while DeepMind emphasizes agents, robotics, safety, science, and embodied/world models.", "Non-chat AI is becoming commercially relevant: health, industrial planning, robotics, assistive interfaces.", "7 / 6 / 6"],
        ], [0.9*cm, 5.0*cm, 6.0*cm, 3.7*cm]),
        Spacer(1, 0.3 * cm),
        SignalVisual("Generated visual: today's opportunity/risk/action profile", ["Agents", "Security", "Compliance", "India AI", "Voice", "DevTools"], [94, 88, 84, 73, 76, 86], "Scores are analyst estimates from public-source signal strength."),
        PageBreak(),
    ]

    sections = [
        ("Calendar And Personal Operating Context", [
            ("Fact", "No calendar connector or authenticated calendar source was available in this automation run, so I could not inspect Aman's meetings, travel, conflicts, or preparation needs."),
            ("Inference", "Given today's internet signals, the single operating priority should be: validate an agent-control or agent-memory pain point with five real users before writing code beyond a prototype."),
            ("Risk", "Without calendar context, the action plan assumes a maker day. If today is meeting-heavy, compress to the 15-minute validation tasks."),
            ("Leverage", "Use the report's Product Hunt and GitHub signals as conversation starters with founders, agencies, accountants, dev shops, and SMB operators."),
        ]),
        ("The World Changed Overnight", [
            ("Fact", "The public web scan did not show one isolated shock; it showed multiple platforms converging on the same operating model: agents that live inside team tools, run asynchronously, use browsers/computers, and need governance."),
            ("Analysis", "OpenAI's phased preview and Anthropic's export-access statement signal that frontier model access can be shaped by state concerns. This creates procurement uncertainty for global builders and strengthens multi-model abstraction layers."),
            ("Second-order effect", "If the best model access becomes segmented by geography, trust tier, or use case, customers will pay for vendors who can degrade gracefully across providers while preserving logs, policies, and outputs."),
            ("Founder implication", "Aman should treat model choice as volatile infrastructure. Product value should sit in workflow ownership, audit trails, domain data, and distribution."),
        ]),
        ("AI Frontier Watch", [
            ("OpenAI", "GPT-5.6 Sol preview claims stronger agentic coding, biology, and cybersecurity performance; introduces max reasoning and ultra subagent mode; prices Sol/Terra/Luna at $5/$30, $2.50/$15, and $1/$6 per million input/output tokens respectively."),
            ("Anthropic", "Claude Tag turns Slack into a shared agent surface with scoped channel memory, admin permissions, spend caps, logs, and ambient follow-ups. This is enterprise agent UX, not chatbot UX."),
            ("Google", "Gemini API computer-use support in public preview makes browser/mobile/desktop action a mainstream API primitive and explicitly includes prompt-injection detection."),
            ("DeepMind", "June 2026 updates emphasize Gemini 3.5 Flash computer use, agent security, multi-agent safety, DiffusionGemma speed, robotics, voice translation, and Gemma 4 12B."),
            ("Open source", "GitHub trending favors privacy messaging, agency-agent packs, local dictation, GPU numerical compute, AI investment research, video editing agents, AI pentest orchestration, and multi-model deliberation."),
        ]),
        ("AI Giants Pulse", [
            ("Sam Altman/OpenAI", "The biggest pulse is vertical integration: limited frontier release plus custom inference silicon. The company is reducing dependence on commodity compute and increasing government-facing release discipline."),
            ("Dario Amodei/Anthropic", "Claude Tag and cyber-threat reporting show Anthropic moving from model vendor to enterprise control surface: Slack, tools, memories, logs, spend caps, and security evidence."),
            ("Google/DeepMind", "Google's developer story is agent infrastructure at API scale: computer use, managed agents, sandboxed code execution, multimodal generation, and science/robotics adjacency."),
            ("Meta", "Meta's June 29 Brain2Qwerty item shows continued investment in non-invasive assistive communication research. The builder lesson is that AI opportunity is broadening beyond chat/coding into healthcare interfaces and human-computer interaction."),
            ("NVIDIA/Microsoft/Amazon/Apple", "No single same-day primary-source launch dominated this scan, but their strategic importance remains compute, distribution, OS-level agent surfaces, and enterprise cloud procurement."),
        ]),
        ("Regulation And Policy Radar", [
            ("EU", "The EU AI Act remains the highest-signal compliance timeline. GPAI obligations became effective in August 2025; transparency rules for chatbots, generated content, deepfakes, and public-interest AI text come into effect in August 2026; high-risk timelines extend into 2027 and 2028 after simplification."),
            ("India", "IndiaAI Mission reporting points to released domestic foundation models and new AI Centres of Excellence, while prior reporting flagged paperwork, funding, and IP concerns for some selected startups. This is opportunity plus execution risk."),
            ("Cyber", "Anthropic's cyber-abuse mapping argues that agentic orchestration is not fully captured by current frameworks. Expect security buyers and regulators to ask for AI-agent activity logs, not just model cards."),
            ("Founder implication", "Build compliance artifacts into product from day one: data-source summaries, model routing logs, prompt/output retention rules, human override, user consent, and generated-content labels."),
        ]),
        ("Community Pain Map", [
            ("Product Hunt", "Today's launches cluster around social-growth agents, end-to-end bookkeeping agents, open-weights access for Cline, AI answer visibility, project-memory tools for coding agents, browser readers, ad-budget automation, ad reframing, and AI sales conversations."),
            ("GitHub", "Trending repos show appetite for agent packs, local voice transcription, personal dossiers, AI trading/research frameworks, video editing with coding agents, pentest orchestration, multi-model councils, and markdown knowledge-base managers."),
            ("HN/Reddit/X limitation", "Authenticated or rate-limited community surfaces were not fully accessible in this run. Signals here use accessible Product Hunt, GitHub, official changelogs, and public pages."),
            ("Pain synthesis", "Users are not asking for yet another generic assistant. They are asking: remember my project, operate in my tools, prove what you did, avoid runaway cost, use open models, and do not expose sensitive context."),
        ]),
        ("Market And Money Signals", [
            ("Compute", "OpenAI's Broadcom chip points to platform-owned inference economics. Startups should assume token prices and latency curves will keep changing and design model-routing flexibility."),
            ("Enterprise", "GitHub and Vercel updates show buyers want AI usage APIs, cost centers, agent session tracing, managed settings, allowed marketplaces, and observability."),
            ("India", "Domestic model and CoE activity creates a services/product wedge around vernacular AI, government workflows, regulated BFSI processes, and low-cost deployment."),
            ("Consumer", "Voice, local privacy, AI answer visibility, and browser-native agents are recurring demand patterns. Distribution can happen through Chrome extensions, Slack apps, VS Code/Cline integrations, and templates."),
        ]),
        ("Technical Opportunity Map", [
            ("Agent control plane", "Common primitives: identity, scoped memory, tool permissions, spend caps, logs, evals, task queues, retries, escalation, and data connectors."),
            ("Security telemetry", "Detect agentic kill-chain behavior: tool chaining, credential access, suspicious file operations, mass exfiltration patterns, repeated policy probing, and autonomous exploit scaffolding."),
            ("Computer-use reliability", "Build test harnesses for browser agents: visual diffing, action replay, prompt-injection fixtures, sandbox policies, and per-site failure analytics."),
            ("Vernacular workflow AI", "Use Indian language models and speech layers for document processing, customer support, education workflows, local-government forms, and voice-first SMB operations."),
            ("AI visibility SEO", "Product Hunt's VisibAI signal suggests demand for monitoring whether brands appear in AI answers. India-local variant: multilingual AI answer presence across categories."),
        ]),
        ("Personal Impact Analysis For Aman", [
            ("Positive effects", "Aman can move faster because the market now educates customers about agents; he does not need to explain why agents matter, only why they can be trusted."),
            ("Negative effects", "Generic agent wrappers are being commoditized by labs and platforms. Thin wrappers around OpenAI/Anthropic/Gemini will be fragile."),
            ("Skill gaps to close", "Agent evals, security logging, OAuth/tool permission design, workflow UX, enterprise onboarding, and India regulatory basics."),
            ("India angle", "India gives access to price-sensitive, process-heavy, multilingual customers whose problems are not solved by Silicon Valley chatbots."),
            ("Ignore today", "Model leaderboard drama without pricing/access/product implications. Also ignore vague AGI discourse unless tied to a customer purchase or regulation."),
        ]),
    ]

    for idx, (title, bullets) in enumerate(sections):
        story.append(p(title, "H1x"))
        story.append(SignalVisual(f"Generated visual: {title.lower()[:44]}", ["Access", "Trust", "Cost", "Demand", "Timing"], [70 + (idx * 3) % 25, 78, 64 + (idx * 5) % 31, 83, 75], "Generated original section visual."))
        for label, body in bullets:
            story.append(p(f"<b>{label}:</b> {body}"))

    story += [
        PageBreak(),
        p("Billion-Dollar Problem Radar", "H1x"),
        table([
            ["Idea", "Problem / customer", "Evidence and why now", "Wedge MVP", "Pricing / moat / risk", "48-hour validation + action today"],
            ["1. Agent Ops Control Plane", "SMBs and dev teams need to let AI agents work without losing control.", "Claude Tag, GitHub, Vercel, and Gemini all point to scoped agents, logs, spend, and browser actions.", "Slack/GitHub app that logs agent tasks, permissions, cost, outputs, and approvals across providers.", "$49-$499/mo per workspace; moat is workflow data and integrations; risk is platform bundling.", "Interview five teams using Claude/Codex/Cline. Today: mock a dashboard and sell the audit-log pain."],
            ["2. AI Agent Security SIEM Lite", "Security teams cannot see when agents behave like attackers.", "Anthropic's 832-account cyber mapping and AI kill-chain gap.", "Log collector for agent tool calls with suspicious chain detection and policy alerts.", "$299-$2k/mo; moat is detection rules; risk is noisy alerts.", "Talk to 3 security consultants. Today: build 10 detection rules from public attack patterns."],
            ["3. India Vernacular Back Office Agents", "Small businesses handle receipts, GST docs, invoices, WhatsApp orders, and bank statements manually.", "Product Hunt bookkeeping-agent signal plus India multilingual model momentum.", "WhatsApp + web agent that classifies docs, extracts line items, prepares accountant-ready packets.", "Per business Rs 999-9,999/mo; moat is local templates/data; risk is accuracy/liability.", "Validate with 10 accountants. Today: process 25 sample receipts and record errors."],
            ["4. AI Answer Visibility For India", "Brands do not know if AI assistants recommend them.", "VisibAI launch and search/AI-discovery anxiety.", "Monitor Hindi/English prompts across AI engines, categories, and competitors.", "$99-$999/mo; moat is prompt corpus and longitudinal data; risk is changing APIs.", "Pitch D2C founders and agencies. Today: produce one sample report for an Indian SaaS niche."],
            ["5. Browser Agent QA Harness", "Computer-use agents fail silently on websites.", "Gemini computer use, Vercel agent observability, and rising browser agents.", "Playwright-based replay, screenshots, prompt-injection tests, and reliability score per workflow.", "$199/mo per app; moat is test library; risk is devtool competition.", "Validate with automation agencies. Today: create a demo on login/form/invoice flows."],
            ["6. Agent Memory Pack For Coding Teams", "Teams repeat project context to every coding agent.", "PMB Product Hunt launch, GitHub/Copilot memory features, repo AGENTS.md growth.", "Repo scanner that creates living agent briefs, architecture maps, decision logs, and task context.", "$20/dev/mo; moat is repo history and update automation; risk is GitHub native feature.", "Survey 20 Cline/Codex users. Today: generate one memory pack for PaperBot."],
            ["7. Compliance-Ready AI Content Labeler", "EU transparency obligations and deepfake rules require AI-content disclosure workflows.", "EU AI Act August 2026 transparency deadline.", "API/browser plugin to mark generated content, store provenance, and export audit summaries.", "$0.005/item plus SaaS; moat is compliance templates; risk is legal ambiguity.", "Talk to agencies exporting to EU. Today: create a policy checklist landing page."],
            ["8. Agentic Procurement Router", "Enterprises fear model access, cost, and availability volatility.", "Government-gated model previews, chip economics, provider model churn.", "Policy-driven model router with fallback, cache, cost caps, geography controls, and audit logs.", "$500+/mo; moat is policy engine and procurement data; risk is gateway incumbents.", "Interview regulated teams. Today: prototype routing policy schema."],
        ], [2.3*cm, 3.1*cm, 3.2*cm, 3.0*cm, 3.0*cm, 3.8*cm]),
        PageBreak(),
        p("Micro-Opportunities", "H1x"),
        table([
            ["#", "Small build", "Why it can work today"],
            ["1", "Claude/Codex/Cline project-memory generator", "Directly addresses re-explaining context to coding agents."],
            ["2", "AI-agent spend calculator for Indian teams", "Pricing tiers are confusing and changing."],
            ["3", "Prompt-injection test pack for browser agents", "Gemini computer-use release makes safety testing timely."],
            ["4", "Slack bot that summarizes agent work logs daily", "Claude Tag normalizes agents in team chat."],
            ["5", "IndiaAI model directory with use-case benchmarks", "Domestic models are scattered across portals and media."],
            ["6", "EU AI Act transparency checklist generator", "Deadline is close enough for agencies to care."],
            ["7", "Local dictation workflow for founders", "GitHub trending shows demand for offline voice tools."],
            ["8", "AI answer visibility mini-audit lead magnet", "Product Hunt signal plus SEO budgets."],
            ["9", "Agent task replay viewer", "Teams need proof of what an agent did."],
            ["10", "Bookkeeping OCR error dataset for India", "Strong wedge for accountants and finance automation."],
        ], [0.8*cm, 5.2*cm, 9.5*cm]),
        p("Contrarian Corner", "H1x"),
        table([
            ["Contrarian view", "Reasoning", "Uncertainty"],
            ["The best near-term AI startup is not another model wrapper.", "Labs are swallowing generic UX. Durable startups own workflow, trust, data, distribution, or regulated liability.", "Medium"],
            ["Open models alone are not the wedge; controlled deployment is.", "Cline/open-weights demand matters, but users still need context, evals, logs, and cost control.", "Medium"],
            ["India's AI opportunity is not only cheap labor displacement.", "Multilingual, voice-first, compliance-heavy, low-margin operations need custom automation that global tools ignore.", "Low-medium"],
        ], [4.5*cm, 8.0*cm, 3.0*cm]),
        p("Watchlist", "H1x"),
        p("People: Sam Altman, Dario Amodei, Demis Hassabis, Aravind Srinivas, Jensen Huang, Yann LeCun, Fei-Fei Li, Andrej Karpathy, Clement Delangue, Jim Fan, Noam Shazeer, S. Krishnan, Ashwini Vaishnaw."),
        p("Companies/repos: OpenAI GPT-5.6, Anthropic Claude Tag, Gemini computer use, Vercel AI Gateway/AI SDK/Harness, GitHub Copilot changelog, Sarvam/BharatGen/IndiaAI releases, browser-use/video-use, ClinePass, PMB, VisibAI, agency-agents, VulnClaw."),
        p("Policy: EU AI Act transparency guidance, India DPDP operational rules, MeitY IndiaAI procurement, RBI fintech/AI risk notes, US export-control posture for frontier models, cyber-framework updates around AI agents."),
        p("Today's Action Plan", "H1x"),
        table([
            ["Time", "Ranked action"],
            ["15 min", "Write a one-page hypothesis: 'Teams will pay for agent logs, permissions, and memory before they pay for another chatbot.'"],
            ["15 min", "Message five founders/dev leads: 'What is the scariest thing an AI agent did or could do in your workflow?'"],
            ["15 min", "Create a spreadsheet of 20 agent-control competitors/features from Anthropic, GitHub, Vercel, Google, Cline, and open-source repos."],
            ["1 hour", "Prototype an agent work-log schema: actor, tool, permission, input, output, cost, risk flag, human approval, replay link."],
            ["1 hour", "Build a sample AI-answer visibility report for one Indian SaaS category."],
            ["1 hour", "Run a browser-agent task and document every failure point as a QA product spec."],
            ["Deep work", "Build a clickable Agent Ops dashboard mock: spend, open tasks, risky actions, memory scopes, approval queue, and audit export."],
            ["Deep work", "Validate India bookkeeping-agent wedge with 10 accountants or SMB owners and collect real documents with consent."],
        ], [2.3*cm, 13.2*cm]),
        PageBreak(),
        p("Methodology And Limitations", "H1x"),
        p("Scanned accessible web sources on 30 June 2026, including official AI lab/company pages, developer changelogs, GitHub trending, Product Hunt, EU policy pages, RBI bulletin index, and IndiaAI-related public coverage. I prioritized primary sources where accessible and labeled secondary-source items as coverage. Authenticated calendar, private email, X/Twitter logged-in views, Reddit logged-in views, Discords, paid newsletters, and private analytics were unavailable. Calendar context is therefore explicitly unavailable."),
        p("Facts are sourced claims from public pages. Analysis is my interpretation of builder implications. Inferences connect multiple public signals. Speculation is limited to opportunity forecasts and marked by uncertainty in the relevant sections."),
        p("Source Appendix", "H1x"),
    ]

    for name, url in SOURCES:
        story.append(p(f"- {source_link(name, url)}", "Smallx"))
    return story


def on_page(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(colors.HexColor("#6B7280"))
    canvas.setFont("Helvetica", 7.5)
    canvas.drawString(1.35 * cm, 0.8 * cm, "Daily Internet Intelligence Dossier - Aman - 2026-06-30")
    canvas.drawRightString(A4[0] - 1.35 * cm, 0.8 * cm, f"Page {doc.page}")
    canvas.restoreState()


def write_markdown():
    md = dedent(f"""
    # Daily Internet Intelligence Dossier - {DATE}

    Thesis: The frontier is shifting from model spectacle to governed, instrumented agent deployment. The strongest builder opportunity today is agent trust infrastructure: scoped memory, permissions, logs, spend controls, security telemetry, and workflow-specific deployment for India/global SMBs.

    Key actions:
    1. Validate agent-control pain with five teams.
    2. Prototype an agent work-log schema.
    3. Build a sample AI-answer visibility report for one Indian category.
    4. Interview accountants/SMBs on vernacular bookkeeping automation.
    5. Track EU AI Act transparency and IndiaAI implementation openings.

    Full polished report is in the PDF at `{PDF_PATH.as_posix()}`.

    ## Sources
    """).strip()
    md += "\n" + "\n".join(f"- [{name}]({url})" for name, url in SOURCES) + "\n"
    MD_PATH.write_text(md, encoding="utf-8")


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    doc = BaseDocTemplate(
        str(PDF_PATH),
        pagesize=A4,
        rightMargin=1.35 * cm,
        leftMargin=1.35 * cm,
        topMargin=1.25 * cm,
        bottomMargin=1.25 * cm,
        title=f"{DATE} Daily Internet Intelligence Dossier",
        author="Codex automation",
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin + 0.2 * cm, doc.width, doc.height - 0.2 * cm, id="normal")
    doc.addPageTemplates([PageTemplate(id="main", frames=[frame], onPage=on_page)])
    doc.build(build_story())
    write_markdown()
    print(PDF_PATH)
    print(MD_PATH)


if __name__ == "__main__":
    main()
