# pdf_generator.py

import fitz  # PyMuPDF
import os
import tempfile
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import qrcode
import io


def _make_output_path(filename: str) -> str:
    if os.getenv("VERCEL"):
        return os.path.join(tempfile.gettempdir(), filename)
    return filename


# --- HELPER FUNCTION FOR PREVIEW GENERATION ---
def _create_preview_from_pdf(pdf_path: str) -> str:
    """
    Takes a path to a PDF, saves its first page as a PNG image,
    and returns the path to the new image.
    """
    preview_image_path = pdf_path.replace(".pdf", ".png")
    try:
        doc = fitz.open(pdf_path)
        page = doc[0]  # Get the first page
        pix = page.get_pixmap(dpi=150)  # Render page to an image with good resolution
        pix.save(preview_image_path)
        doc.close()
        return preview_image_path
    except Exception as e:
        print(f"Error creating preview image: {e}")
        return ""


# --- UPDATED PDF GENERATION FUNCTIONS WITH PREVIEW ---

def generate_campus_ambassador_pdf_with_preview(name: str, create_preview: bool = True) -> tuple[str, str]:
    """Generates the CA PDF and a preview image of the first page."""
    # Step 1: Generate the full PDF as before
    TEMPLATE_PATH = "templates/campus_ambassador.pdf"
    output_path = _make_output_path(f"CA_Letter_{name.replace(' ', '_')}.pdf")

    NAME_COORDS = (110, 244)
    DATE_COORDS = (423, 245)
    current_date = datetime.now().strftime("%B %d, %Y")

    template_doc = fitz.open(TEMPLATE_PATH)
    page_1 = template_doc[0]
    page_1.insert_text(NAME_COORDS, name, fontsize=18, fontname="helv", color=(0, 0, 0))
    page_1.insert_text(DATE_COORDS, current_date, fontsize=14, fontname="helv", color=(0, 0, 0))

    output_doc = fitz.open()
    output_doc.insert_pdf(template_doc, from_page=0, to_page=1)
    output_doc.save(output_path, garbage=4, deflate=True)
    template_doc.close()
    output_doc.close()

    # Step 2: Create the preview from the generated PDF
    preview_path = _create_preview_from_pdf(output_path) if create_preview else ""
    return output_path, preview_path


def generate_internship_acceptance_pdf_with_preview(name: str, month: str, domain: str, create_preview: bool = True) -> tuple[str, str]:
    """Generates the Internship PDF and a preview image."""

    # Step 1: Generate the full PDF
    domain_to_template_map = {
        "artificial intelligence": "templates/ai-internship.pdf",
        "machine learning": "templates/ml-internship.pdf",
        "web development": "templates/wd-internship.pdf",
        "cybersecurity": "templates/cs-internship.pdf",
        "data science": "templates/ds-internship.pdf",
        "digital marketing": "templates/dm-internship.pdf",
        "human resource management": "templates/hr-internship.pdf",
        "human resource": "templates/hr-internship.pdf",
        "finance": "templates/fi-internship.pdf",
        "financial modeling & analysis": "templates/fi-internship.pdf",
        "financial modeling & valuation": "templates/fi-internship.pdf",
        "cloud computing": "templates/cc-internship.pdf",
        "aws cloud computing": "templates/cc-internship.pdf",
        "auto cad": "templates/ac-internship.pdf",
        "autocad": "templates/ac-internship.pdf",
        "embedded system": "templates/emb-internship.pdf",
        "iot": "templates/iot-internship.pdf",
        "iot (internet of things)": "templates/iot-internship.pdf",
        "stock market & crypto": "templates/stm-internship.pdf",
        "stock market": "templates/stm-internship.pdf",
        "stock market & crypto currency": "templates/stm-internship.pdf",
        "stock market & crypto trading": "templates/stm-internship.pdf",
        "vlsi": "templates/vlsi-internship.pdf",
        "medical coding": "templates/mc-internship.pdf",
        "business analytics": "templates/ba-internship.pdf",
        "data analytics": "templates/da-internship.pdf",
        "logistics and supply chain": "templates/lsc-internship.pdf",
        "logistic and supply chain": "templates/lsc-internship.pdf",
        "logistics and supply chain management": "templates/lsc-internship.pdf",
        "logistic and supply chain management": "templates/lsc-internship.pdf"
    }

    clean_domain = domain.strip().lower()
    template_path = domain_to_template_map.get(clean_domain)

    if not template_path:
        raise ValueError(f"No template found for domain: '{domain}'")

    try:
        # Get current date info
        now = datetime.now()
        current_year = now.year

        # Parse the input month to ensure it is valid
        clean_month = month.strip().title()

        # LOGIC FIX: Always consider the current year for the "from date".
        # This fixes the issue where previous months (like Jan when current is Mar) were bumped to next year.
        target_year = current_year

        # Create the start date object using the current year
        start_month_date = datetime.strptime(f"10 {clean_month} {target_year}", "%d %B %Y")
        from_date = start_month_date.strftime("%d-%m-%Y")

        # relativedelta(months=2) automatically rolls over to the next year if needed
        # (e.g. 10 Nov 2026 + 2 Months -> 10 Jan 2027)
        to_date_obj = start_month_date + relativedelta(months=2)
        to_date = to_date_obj.strftime("%d-%m-%Y")

    except ValueError:
        raise ValueError(f"Invalid month format from sheet: '{month}'. Expected full month name (e.g., 'January').")

    output_path = _make_output_path(f"Internship_Letter_{name.replace(' ', '_')}.pdf")

    domain_lower = domain.lower()

    if domain_lower in (
            "embedded system",
            "stock market & crypto",
            "stock market",
            "stock market & crypto trading",
            "stock market & crypto currency"
    ):
        NAME_COORDS, FROM_DATE_COORDS, TO_DATE_COORDS = (262, 307), (365, 595), (448, 595)

    elif domain_lower in (
            "iot",
            "iot (internet of things)",
            "iot(internet of things)"
    ):
        NAME_COORDS, FROM_DATE_COORDS, TO_DATE_COORDS = (262, 307), (365, 578), (448, 578)
    elif domain_lower in (
            "logistics and supply chain management",
            "logistic and supply chain management",
            "logistics and supply chain",
            "logistic and supply chain"
    ):
        NAME_COORDS, FROM_DATE_COORDS, TO_DATE_COORDS = (262, 307), (365, 596), (448, 596)
    else:
        NAME_COORDS, FROM_DATE_COORDS, TO_DATE_COORDS = (262, 307), (365, 560), (448, 560)

    doc = fitz.open(template_path)
    page = doc[0]
    page.insert_text(NAME_COORDS, name, fontsize=12, fontname="helv", color=(0, 0, 0))
    page.insert_text(FROM_DATE_COORDS, from_date, fontsize=11, fontname="helv", color=(0, 0, 0))
    page.insert_text(TO_DATE_COORDS, to_date, fontsize=11, fontname="helv", color=(0, 0, 0))
    doc.save(output_path, garbage=4, deflate=True)
    doc.close()

    # Step 2: Create the preview
    # Assuming _create_preview_from_pdf is defined elsewhere in your scope
    preview_path = _create_preview_from_pdf(output_path) if create_preview else ""
    return output_path, preview_path

# generate_internship_acceptance_pdf_with_preview('Aman', 'january', 'iot (internet of things)')

def generate_offer_letter_pdf_with_preview(name: str, training_from: str, create_preview: bool = True) -> tuple[str, str]:
    """Generates the Offer Letter PDF and a preview image."""
    # Step 1: Generate the full PDF as before
    TEMPLATE_PATH = "templates/offer_letter.pdf"
    output_path = _make_output_path(f"Offer_Letter_{name.replace(' ', '_')}.pdf")
    NAME_COORDS, TODAY_DATE_COORDS = (91, 293), (94, 253)
    TRAINING_DATES_COORDS, INTERNSHIP_START_COORDS, INTERNSHIP_END_COORDS = (136, 374), (170, 401), (163, 428)

    todays_date = datetime.now().strftime("%d-%m-%Y")
    try:
        training_from_obj = datetime.strptime(training_from, "%d-%m-%Y")
        training_to_obj = training_from_obj + timedelta(days=10)
        internship_start_obj = training_to_obj + timedelta(days=1)
        internship_end_obj = internship_start_obj + relativedelta(months=6)
        training_to = training_to_obj.strftime("%d-%m-%Y")
        internship_start = internship_start_obj.strftime("%d-%m-%Y")
        internship_end = internship_end_obj.strftime("%d-%m-%Y")
        training_dates_text = f"{training_from} to {training_to}"
    except ValueError:
        raise ValueError("Invalid date format. Please use DD-MM-YYYY.")

    template_doc = fitz.open(TEMPLATE_PATH)
    page_1 = template_doc[0]
    page_1.insert_text(NAME_COORDS, name, fontsize=10, fontname="helv", color=(0, 0, 0))
    page_1.insert_text(TODAY_DATE_COORDS, todays_date, fontsize=10, fontname="helv", color=(0, 0, 0))
    page_1.insert_text(TRAINING_DATES_COORDS, training_dates_text, fontsize=10, fontname="helv", color=(0, 0, 0))
    page_1.insert_text(INTERNSHIP_START_COORDS, internship_start, fontsize=10, fontname="helv", color=(0, 0, 0))
    page_1.insert_text(INTERNSHIP_END_COORDS, internship_end, fontsize=10, fontname="helv", color=(0, 0, 0))

    output_doc = fitz.open()
    output_doc.insert_pdf(template_doc, from_page=0, to_page=2)
    output_doc.save(output_path, garbage=4, deflate=True)
    template_doc.close()
    output_doc.close()

    # Step 2: Create the preview
    preview_path = _create_preview_from_pdf(output_path) if create_preview else ""
    return output_path, preview_path


def generate_completion_certificate(name: str, issue_date: str, domain: str, identifier_id: str, create_preview: bool = True) -> tuple[str, str]:
    """Generates the CA PDF (Landscape) with centered domain text and a QR Code."""

    TEMPLATE_PATH = "templates/completion_certificate.pdf"
    output_path = _make_output_path(f"CA_Letter_{name.replace(' ', '_')}.pdf")

    # --- Content Preparation ---
    domain_text = f"This is to certify that the candidate has successfully completed internship in {domain}."

    base_url = "https://persevex.com/verification"
    full_url = f"{base_url}?id={identifier_id}"

    # --- Coordinates (Adjusted for A4 Landscape: 842 x 595 pts) ---

    # 1. Name and Date (kept as per your previous settings)
    NAME_COORDS = (414, 330)
    DATE_COORDS = (623, 458)

    # 2. Domain Text Rectangle (For Centering)
    # Width is now ~842. We set margins at 50 (x0) and 792 (x1) to center properly.
    # Y is set below the name/date (approx y=290 to y=350)
    TEXT_RECT = fitz.Rect(225, 358, 705, 460)

    # 3. QR Code Location (Bottom Left)
    # Page height is only 595. We must place it above that.
    # Position: x=50, y=480 (size 80x80) -> Ends at y=560
    QR_RECT = fitz.Rect(148, 494, 228, 574)

    # --- QR Code Generation ---
    qr = qrcode.QRCode(box_size=10, border=2)
    qr.add_data(full_url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")

    img_byte_arr = io.BytesIO()
    qr_img.save(img_byte_arr, format='PNG')
    img_bytes = img_byte_arr.getvalue()

    # --- PDF Generation ---
    template_doc = fitz.open(TEMPLATE_PATH)
    page_1 = template_doc[0]

    times_font = fitz.Font("times-roman")
    # 2. Insert the font into the page resources with the name "ti"
    page_1.insert_font(fontname="times-roman", fontbuffer=times_font.buffer)

    raleway_font = fitz.Font(fontfile="fonts/raleway.ttf")
    page_1.insert_font(fontname="raleway", fontbuffer=raleway_font.buffer)

    pinyon_font = fitz.Font(fontfile="fonts/pinyon.ttf")
    page_1.insert_font(fontname="pinyon", fontbuffer=pinyon_font.buffer)

    # Insert Name
    page_1.insert_text(NAME_COORDS, name, fontsize=34, fontname="times-roman", color=(0, 0, 0))

    # Insert Issue Date
    page_1.insert_text(DATE_COORDS, issue_date, fontsize=12, fontname="helv", color=(0, 0, 0))

    # Insert Centered Domain Text
    page_1.insert_textbox(
        TEXT_RECT,
        domain_text,
        fontsize=14,
        fontname="helv",
        align=1,  # 1 = Center Alignment
        color=(0, 0, 0)
    )

    # Insert QR Code
    page_1.insert_image(QR_RECT, stream=img_bytes)

    # Save output
    output_doc = fitz.open()
    output_doc.insert_pdf(template_doc, from_page=0, to_page=1)
    output_doc.save(output_path, garbage=4, deflate=True)
    template_doc.close()
    output_doc.close()

    # Step 2: Create the preview
    preview_path = _create_preview_from_pdf(output_path) if create_preview else ""
    return output_path, preview_path

def ca_certificate(name: str, issue_date: str, create_preview: bool = True) -> tuple[str, str]:
    """Generates the CA PDF (Landscape) with centered domain text and a QR Code."""

    TEMPLATE_PATH = "templates/ca_certificate.pdf"
    output_path = _make_output_path(f"CA_Letter_{name.replace(' ', '_')}.pdf")

    # --- Content Preparation ---
    domain_text = f"""
Has successfully completed the Persevex Campus Representative Program from {issue_date} and has demonstrated exceptional competency, dedication, and commitment while contributing effectively to the program.
"""


    # --- Coordinates (Adjusted for A4 Landscape: 842 x 595 pts) ---

    # 1. Name and Date (kept as per your previous settings)
    NAME_COORDS = (310, 305)

    # 2. Domain Text Rectangle (For Centering)
    # Width is now ~842. We set margins at 50 (x0) and 792 (x1) to center properly.
    # Y is set below the name/date (approx y=290 to y=350)
    TEXT_RECT = fitz.Rect(310, 320, 755, 460)

    # --- PDF Generation ---
    template_doc = fitz.open(TEMPLATE_PATH)
    page_1 = template_doc[0]

    times_font = fitz.Font("times-roman")
    # 2. Insert the font into the page resources with the name "ti"
    page_1.insert_font(fontname="times-roman", fontbuffer=times_font.buffer)

    raleway_font = fitz.Font(fontfile="fonts/raleway.ttf")
    page_1.insert_font(fontname="raleway", fontbuffer=raleway_font.buffer)

    pinyon_font = fitz.Font(fontfile="fonts/pinyon.ttf")
    page_1.insert_font(fontname="pinyon", fontbuffer=pinyon_font.buffer)

    # Insert Name
    page_1.insert_text(NAME_COORDS, name, fontsize=54, fontname="pinyon", color=(0, 0, 0))

    # Insert Centered Domain Text
    page_1.insert_textbox(
        TEXT_RECT,
        domain_text,
        fontsize=14,
        fontname="raleway",
        align=0,  # 1 = Center Alignment
        color=(0, 0, 0)
    )

    # Save output
    output_doc = fitz.open()
    output_doc.insert_pdf(template_doc, from_page=0, to_page=1)
    output_doc.save(output_path, garbage=4, deflate=True)
    template_doc.close()
    output_doc.close()

    # Step 2: Create the preview
    preview_path = _create_preview_from_pdf(output_path) if create_preview else ""
    return output_path, preview_path
