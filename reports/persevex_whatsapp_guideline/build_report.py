from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import (
    Flowable,
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets"
OUT = ROOT / "persevex-whatsapp-business-guideline.pdf"

PAGE_W, PAGE_H = A4
BLACK = colors.HexColor("#111111")
INK = colors.HexColor("#202020")
MUTED = colors.HexColor("#666666")
LIGHT = colors.HexColor("#F6F6F3")
LINE = colors.HexColor("#E6E2D8")
YELLOW = colors.HexColor("#F4C430")
PALE_YELLOW = colors.HexColor("#FFF4C2")
GREEN = colors.HexColor("#2FA866")
RED = colors.HexColor("#C94B4B")


def style_sheet():
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            "Eyebrow",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8.5,
            leading=11,
            textColor=MUTED,
            uppercase=True,
            spaceAfter=5,
        )
    )
    styles.add(
        ParagraphStyle(
            "TitleLarge",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=31,
            leading=35,
            textColor=BLACK,
            spaceAfter=10,
        )
    )
    styles.add(
        ParagraphStyle(
            "PageTitle",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=26,
            textColor=BLACK,
            spaceAfter=12,
        )
    )
    styles.add(
        ParagraphStyle(
            "Section",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=13.5,
            leading=16,
            textColor=BLACK,
            spaceAfter=7,
        )
    )
    styles.add(
        ParagraphStyle(
            "Body",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=9.8,
            leading=14,
            textColor=INK,
            spaceAfter=7,
        )
    )
    styles.add(
        ParagraphStyle(
            "Small",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11.5,
            textColor=MUTED,
        )
    )
    styles.add(
        ParagraphStyle(
            "CardTitle",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=10.5,
            leading=13,
            textColor=BLACK,
            spaceAfter=3,
        )
    )
    styles.add(
        ParagraphStyle(
            "CardBody",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=8.8,
            leading=12,
            textColor=INK,
        )
    )
    styles.add(
        ParagraphStyle(
            "Checklist",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=9,
            leading=12.5,
            textColor=INK,
            leftIndent=0,
        )
    )
    return styles


STYLES = style_sheet()


def p(text, style="Body"):
    return Paragraph(text, STYLES[style])


class AccentRule(Flowable):
    def __init__(self, width=44 * mm, height=3):
        super().__init__()
        self.width = width
        self.height = height

    def draw(self):
        self.canv.setFillColor(YELLOW)
        self.canv.roundRect(0, 0, self.width, self.height, 1.5, fill=1, stroke=0)


class BulletDot(Flowable):
    def __init__(self):
        super().__init__()
        self.width = 4 * mm
        self.height = 4 * mm

    def draw(self):
        self.canv.setFillColor(YELLOW)
        self.canv.circle(1.8 * mm, 1.9 * mm, 1.3 * mm, fill=1, stroke=0)


class CheckBox(Flowable):
    def __init__(self):
        super().__init__()
        self.width = 6 * mm
        self.height = 6 * mm

    def draw(self):
        self.canv.setStrokeColor(YELLOW)
        self.canv.setLineWidth(1.1)
        self.canv.roundRect(0.8 * mm, 1.1 * mm, 3.5 * mm, 3.5 * mm, 0.8 * mm, fill=0, stroke=1)


class Timeline(Flowable):
    def __init__(self, items, width=160 * mm):
        super().__init__()
        self.items = items
        self.width = width
        self.height = 45 * mm

    def draw(self):
        c = self.canv
        gap = self.width / (len(self.items) - 1)
        y = 25 * mm
        c.setStrokeColor(LINE)
        c.setLineWidth(1.5)
        c.line(5 * mm, y, self.width - 5 * mm, y)
        for i, (label, detail) in enumerate(self.items):
            x = i * gap
            c.setFillColor(YELLOW if i < 3 else GREEN)
            c.circle(x, y, 4.5 * mm, fill=1, stroke=0)
            c.setFillColor(BLACK)
            c.setFont("Helvetica-Bold", 7.6)
            c.drawCentredString(x, y + 8 * mm, label)
            c.setFillColor(MUTED)
            c.setFont("Helvetica", 6.9)
            for line_no, line in enumerate(wrap_text(detail, 18, "Helvetica", 6.9)):
                c.drawCentredString(x, y - (8 + line_no * 3.5) * mm, line)


def wrap_text(text, max_width_mm, font, size):
    words = text.split()
    lines = []
    current = ""
    max_width = max_width_mm * mm
    for word in words:
        test = f"{current} {word}".strip()
        if stringWidth(test, font, size) <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines[:3]


def header_footer(canvas, doc):
    canvas.saveState()
    margin = 15 * mm
    logo = ASSETS / "persevex-logo.png"
    if logo.exists():
        canvas.drawImage(str(logo), margin, PAGE_H - 16 * mm, width=32 * mm, height=9 * mm, preserveAspectRatio=True, mask="auto")
    canvas.setStrokeColor(LINE)
    canvas.setLineWidth(0.6)
    canvas.line(margin, PAGE_H - 20 * mm, PAGE_W - margin, PAGE_H - 20 * mm)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(margin, 10 * mm, "PERSEVEX - WhatsApp Business Usage Guideline")
    canvas.drawRightString(PAGE_W - margin, 10 * mm, f"{doc.page}")
    canvas.restoreState()


def cover_footer(canvas, doc):
    canvas.saveState()
    margin = 16 * mm
    logo = ASSETS / "persevex-logo.png"
    if logo.exists():
        canvas.drawImage(str(logo), margin, PAGE_H - 24 * mm, width=42 * mm, height=12 * mm, preserveAspectRatio=True, mask="auto")
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica", 8)
    canvas.drawString(margin, 13 * mm, "Internal employee guideline - concise usage, onboarding, and mitigation playbook")
    canvas.restoreState()


def image(path, width, height=None):
    img = Image(str(ASSETS / path))
    img._restrictSize(width, height or 200 * mm)
    return img


def card(title, body, tone="plain"):
    bg = {"plain": colors.white, "warn": PALE_YELLOW, "ok": colors.HexColor("#EAF7EF"), "stop": colors.HexColor("#FFF0F0")}[tone]
    border = {"plain": LINE, "warn": YELLOW, "ok": GREEN, "stop": RED}[tone]
    t = Table(
        [[p(title, "CardTitle")], [p(body, "CardBody")]],
        colWidths=[50 * mm],
        style=TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), bg),
                ("BOX", (0, 0), (-1, -1), 0.7, border),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        ),
    )
    return t


def three_cards(items):
    return Table(
        [[card(*items[0]), card(*items[1]), card(*items[2])]],
        colWidths=[52 * mm, 52 * mm, 52 * mm],
        hAlign="LEFT",
        style=TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 5)]),
    )


def bullet_list(items):
    return Table(
        [[BulletDot(), p(item, "Checklist")] for item in items],
        colWidths=[6 * mm, 150 * mm],
        style=TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        ),
    )


def checklist_group(title, items):
    rows = [[p(title, "CardTitle"), ""]]
    rows.extend([[CheckBox(), p(item, "Checklist")] for item in items])
    return Table(
        rows,
        colWidths=[8 * mm, 69 * mm],
        style=TableStyle(
            [
                ("SPAN", (0, 0), (-1, 0)),
                ("BACKGROUND", (0, 0), (-1, 0), PALE_YELLOW),
                ("BOX", (0, 0), (-1, -1), 0.7, LINE),
                ("LINEBELOW", (0, 0), (-1, 0), 0.7, YELLOW),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        ),
    )


def signoff_box():
    line = "<font color='#666666'>________________________________</font>"
    return Table(
        [
            [p("Prepared by", "Small"), p("Date", "Small")],
            [p(line, "Small"), p(line, "Small")],
        ],
        colWidths=[77 * mm, 77 * mm],
        style=TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), LIGHT),
                ("BOX", (0, 0), (-1, -1), 0.7, LINE),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        ),
    )


def build():
    doc = SimpleDocTemplate(
        str(OUT),
        pagesize=A4,
        rightMargin=16 * mm,
        leftMargin=16 * mm,
        topMargin=26 * mm,
        bottomMargin=18 * mm,
    )
    story = []

    story.extend(
        [
            Spacer(1, 30 * mm),
            p("EMPLOYEE GUIDELINE", "Eyebrow"),
            p("Using WhatsApp Business Without Triggering Avoidable Bans", "TitleLarge"),
            AccentRule(),
            Spacer(1, 8 * mm),
            p(
                "A practical, low-stress guide for PERSEVEX employees to onboard numbers gradually, keep communication natural, and reduce restriction risk.",
                "Body",
            ),
            Spacer(1, 8 * mm),
            image("cover-visual.png", 166 * mm, 96 * mm),
            Spacer(1, 8 * mm),
            p("Core idea: use each number like a real business communication channel before scaling any customer outreach.", "Section"),
        ]
    )
    story.append(PageBreak())

    story.extend(
        [
            p("01 - The Problem", "Eyebrow"),
            p("Why WhatsApp numbers get banned", "PageTitle"),
            p(
                "Restrictions usually happen when a new or low-trust number suddenly behaves like a broadcast tool. The account may look empty, fast, repetitive, link-heavy, or unwanted.",
                "Body",
            ),
            Spacer(1, 5 * mm),
            image("risk-visual.png", 82 * mm, 82 * mm),
            Spacer(1, 5 * mm),
            three_cards(
                [
                    ("New number, high activity", "Sending many messages before the account has normal usage history.", "warn"),
                    ("One-way communication", "Many outbound messages with few replies can resemble spam.", "warn"),
                    ("Repeated copy-paste", "Identical text, links, and fast bursts increase restriction signals.", "warn"),
                ]
            ),
            Spacer(1, 7 * mm),
            p(
                "<b>Important reality:</b> no SOP can guarantee that a number will never be restricted. The goal is to remove avoidable risk and make every account behave like a legitimate support channel.",
                "Body",
            ),
        ]
    )
    story.append(PageBreak())

    story.extend(
        [
            p("02 - First 3 Days", "Eyebrow"),
            p("Warm up the account naturally", "PageTitle"),
            p("Do not launch campaigns from a fresh number. Build trust signals first: a complete profile, real replies, and calm pacing.", "Body"),
            Spacer(1, 7 * mm),
            Timeline(
                [
                    ("Day 0", "Install, verify OTP, keep SIM active"),
                    ("Profile", "Add name, photo, website, email, hours"),
                    ("24 hrs", "Chat with 5-10 known people"),
                    ("Days 1-3", "Reply, save contacts, use naturally"),
                    ("Scale", "Increase volume only after healthy replies"),
                ]
            ),
            Spacer(1, 10 * mm),
            three_cards(
                [
                    ("Complete the profile", "A blank business profile looks new and less trustworthy.", "ok"),
                    ("Get real replies", "Two-way conversations are healthier than one-way outbound messaging.", "ok"),
                    ("Move gradually", "Small batches with pauses are safer than sudden high-volume bursts.", "ok"),
                ]
            ),
        ]
    )
    story.append(PageBreak())

    story.extend(
        [
            p("03 - Daily Messaging Rules", "Eyebrow"),
            p("Send like support, not spam", "PageTitle"),
            p("The safest messages feel expected, specific, and conversational. The first touch should not look like a mass promotion.", "Body"),
            Spacer(1, 7 * mm),
            image("mitigation-visual.png", 166 * mm, 70 * mm),
            Spacer(1, 8 * mm),
            Table(
                [
                    [card("Do", "Personalize greetings, reply to questions, share links only when useful, vary wording naturally.", "ok"), card("Avoid", "Mass customer blasts, identical forwarded text, link-first messages, adding many unknown contacts.", "stop")],
                    [card("Good flow", "Customer asks -> employee replies -> short conversation -> relevant link or next step.", "ok"), card("Bad flow", "New number -> copied offer -> link -> same message to everyone.", "stop")],
                ],
                colWidths=[79 * mm, 79 * mm],
                style=TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]),
            ),
            Spacer(1, 4 * mm),
            p("Message variation examples", "Section"),
            p("Use different openings while keeping the same intent: 'Hi John, sharing the course details you requested.' / 'Thanks for reaching out, John. Here are the details.' / 'Great speaking with you, John. Sending the information below.'", "Body"),
        ]
    )
    story.append(PageBreak())

    story.extend(
        [
            p("04 - Mitigation Strategy", "Eyebrow"),
            p("What employees should do from now on", "PageTitle"),
            p("Every new number should pass a small readiness check before any customer campaign or higher-volume communication.", "Body"),
            Spacer(1, 5 * mm),
            three_cards(
                [
                    ("1. Prepare", "Install WhatsApp Business, complete profile, set greeting, verify SIM and details.", "plain"),
                    ("2. Humanize", "Exchange messages with 5-10 known contacts and receive real replies.", "plain"),
                    ("3. Scale slowly", "Start with individual customer support, then increase only when engagement stays healthy.", "plain"),
                ]
            ),
            Spacer(1, 8 * mm),
            p("SIM card change rule", "Section"),
            Table(
                [
                    [
                        card("Keep using the working account", "When SIM cards change, avoid creating a new WhatsApp account if the previous WhatsApp is still working. Continue using it as long as it remains active.", "ok"),
                        card("Do not lose the old SIM", "Keep the previous SIM card safely with the team. It may be required later for OTP verification or relogging into the old WhatsApp account.", "warn"),
                    ]
                ],
                colWidths=[79 * mm, 79 * mm],
                style=TableStyle(
                    [
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 0),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ]
                ),
            ),
            Spacer(1, 8 * mm),
            p("If using WhatsApp Business Platform/API", "Section"),
            bullet_list(
                [
                    "Verify the business and number before campaigns.",
                    "Use approved templates where required.",
                    "Start with smaller volumes and increase gradually.",
                    "Monitor delivery rate, quality rating, and user feedback.",
                    "Personalize once users respond inside the customer service window.",
                ]
            ),
            Spacer(1, 8 * mm),
            p("If an account is restricted", "Section"),
            bullet_list(
                [
                    "Stop bulk or automated messaging immediately.",
                    "Complete any WhatsApp verification or review steps.",
                    "Continue only genuine one-to-one conversations where appropriate.",
                    "Review recent activity before resuming higher-volume messaging.",
                    "Do not rapidly cycle new replacement numbers to bypass restrictions.",
                ]
            ),
        ]
    )
    story.append(PageBreak())

    story.extend(
        [
            p("05 - Employee Checklist", "Eyebrow"),
            p("Before using a new number", "PageTitle"),
            p("Use this as a quick sign-off before handing a number to the sales, support, or outreach team.", "Body"),
            Spacer(1, 6 * mm),
            Table(
                [
                    [
                        checklist_group(
                            "Account readiness",
                            [
                                "Profile photo, business name, category, website/email, and hours are complete.",
                                "The account has exchanged messages with 5-10 known people.",
                                "There are genuine incoming replies.",
                            ],
                        ),
                        checklist_group(
                            "Messaging behavior",
                            [
                                "No mass customer messaging happened on Day 1.",
                                "Outbound messages are personalized, not identical copy-paste.",
                                "Links are shared only after context or customer interest.",
                            ],
                        ),
                    ],
                    [
                        checklist_group(
                            "SIM and access control",
                            [
                                "If an old WhatsApp is still working after a SIM change, keep using it.",
                                "The previous SIM card is stored safely for future OTP or relogin needs.",
                            ],
                        ),
                        checklist_group(
                            "Risk response",
                            [
                                "Activity is spread through the day with natural pauses.",
                                "The employee knows what to do if a warning or restriction appears.",
                            ],
                        ),
                    ],
                ],
                colWidths=[80 * mm, 80 * mm],
                style=TableStyle(
                    [
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 0),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                        ("TOPPADDING", (0, 0), (-1, -1), 0),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                    ]
                ),
            ),
            Spacer(1, 6 * mm),
            signoff_box(),
            Spacer(1, 7 * mm),
            KeepTogether(
                [
                    p("Key principle", "Section"),
                    p(
                        "Do not try to 'look human' artificially. Use WhatsApp the way legitimate businesses do: clear identity, expected messages, real replies, relevant links, and gradual scaling.",
                        "Body",
                    ),
                ]
            ),
        ]
    )

    doc.build(story, onFirstPage=cover_footer, onLaterPages=header_footer)


if __name__ == "__main__":
    build()
    print(OUT)
