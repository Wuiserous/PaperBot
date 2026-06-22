import os
from typing import Dict, Tuple

import database_handler
import custom_template_service
import pdf_generator
from email_sender import send_personalized_email


LETTER_TYPE_OPTIONS = [
    ("ca_letter", "Campus Ambassador Letter"),
    ("internship_letter", "Internship Acceptance Letter"),
    ("offer_letter", "Offer Letter"),
    ("course_certificate", "Course Completion Certificate"),
    ("ca_certificate", "Campus Ambassador Certificate"),
]
CUSTOM_TEMPLATE_PREFIX = "custom_template:"


def get_letter_type_map() -> Dict[str, str]:
    return dict(LETTER_TYPE_OPTIONS)


def get_letter_schema() -> Dict[str, Dict[str, object]]:
    return {
        "ca_letter": {
            "label": "Campus Ambassador Letter",
            "short_label": "CA Letter",
            "description": "Create and preview a campus ambassador appointment letter, then send it by email.",
            "helper_text": "Use this when you already know the candidate's name and email address.",
            "sender_label": "Persevex Support",
            "fields": [
                {"name": "name", "label": "Candidate Name", "type": "text", "required": True, "placeholder": "Enter full name"},
                {"name": "email", "label": "Email Address", "type": "email", "required": True, "placeholder": "name@example.com"},
            ],
        },
        "internship_letter": {
            "label": "Internship Acceptance Letter",
            "short_label": "Internship Letter",
            "description": "Look up the intern in the onboarding sheet, generate the correct domain template, and send it.",
            "helper_text": "Only the intern name is needed here. Email and domain are fetched from the onboarding sheet.",
            "sender_label": "Persevex Support",
            "fields": [
                {"name": "name", "label": "Intern Name", "type": "text", "required": True, "placeholder": "Enter name as stored in OB"},
            ],
        },
        "offer_letter": {
            "label": "Offer Letter",
            "short_label": "Offer Letter",
            "description": "Generate the offer letter with training dates and send it from the HR account.",
            "helper_text": "Training start date must stay in DD-MM-YYYY format to match the PDF logic.",
            "sender_label": "Persevex HR",
            "fields": [
                {"name": "name", "label": "Candidate Name", "type": "text", "required": True, "placeholder": "Enter full name"},
                {"name": "email", "label": "Email Address", "type": "email", "required": True, "placeholder": "name@example.com"},
                {"name": "training_from", "label": "Training Start Date", "type": "text", "required": True, "placeholder": "DD-MM-YYYY"},
            ],
        },
        "course_certificate": {
            "label": "Course Completion Certificate",
            "short_label": "Course Certificate",
            "description": "Generate a completion certificate with course details and QR verification ID.",
            "helper_text": "Fill all fields exactly as they should appear in the certificate and QR record.",
            "sender_label": "Persevex Support",
            "fields": [
                {"name": "name", "label": "Student Name", "type": "text", "required": True, "placeholder": "Enter student name"},
                {"name": "email", "label": "Email Address", "type": "email", "required": True, "placeholder": "name@example.com"},
                {"name": "domain", "label": "Domain / Course Name", "type": "text", "required": True, "placeholder": "Artificial Intelligence"},
                {"name": "date", "label": "Issue Date", "type": "text", "required": True, "placeholder": "15 November, 2025"},
                {"name": "cert_id", "label": "Certificate ID", "type": "text", "required": True, "placeholder": "js2389rdaa33"},
            ],
        },
        "ca_certificate": {
            "label": "Campus Ambassador Certificate",
            "short_label": "CA Certificate",
            "description": "Generate the campus ambassador certificate and email it after preview approval.",
            "helper_text": "Use the exact issue date text you want printed on the certificate.",
            "sender_label": "Persevex Support",
            "fields": [
                {"name": "name", "label": "Candidate Name", "type": "text", "required": True, "placeholder": "Enter full name"},
                {"name": "email", "label": "Email Address", "type": "email", "required": True, "placeholder": "name@example.com"},
                {"name": "date", "label": "Issue Date", "type": "text", "required": True, "placeholder": "15 November, 2025"},
            ],
        },
    }


def _clean_form_data(form_data: Dict[str, str]) -> Dict[str, str]:
    return {key: (value or "").strip() for key, value in form_data.items()}


def _ensure_required_fields(letter_type: str, data: Dict[str, str]) -> None:
    if letter_type.startswith(CUSTOM_TEMPLATE_PREFIX):
        if not data.get("email"):
            raise ValueError("Missing required fields: Email Address")
        return

    schema = get_letter_schema().get(letter_type)
    if not schema:
        raise ValueError("Unknown letter type selected.")

    missing = [field["label"] for field in schema["fields"] if field.get("required") and not data.get(field["name"])]
    if missing:
        raise ValueError(f"Missing required fields: {', '.join(missing)}")


def cleanup_files(*paths: str) -> None:
    for path in paths:
        if path and os.path.exists(path):
            os.remove(path)


def build_letter_preview(letter_type: str, form_data: Dict[str, str], create_preview: bool = True, owner_user_id: int | None = None) -> Dict[str, object]:
    data = _clean_form_data(form_data)
    _ensure_required_fields(letter_type, data)

    if letter_type.startswith(CUSTOM_TEMPLATE_PREFIX):
        if owner_user_id is None:
            raise ValueError("Sign in again before using custom templates.")
        template_id = letter_type.removeprefix(CUSTOM_TEMPLATE_PREFIX)
        template = custom_template_service.load_template(owner_user_id, template_id)
        if not template:
            raise ValueError("Template not found.")
        pdf_path, preview_path = custom_template_service.render_document(owner_user_id, template_id, data)
        recipient_name = data.get("name") or data.get("candidate_name") or data.get("student_name") or template["name"]
        recipient_data = {
            "name": recipient_name,
            "email": data["email"],
            "domain": template["name"],
            "letter_type": template["name"],
        }
        sender_account = "default"

    elif letter_type == "ca_letter":
        pdf_path, preview_path = pdf_generator.generate_campus_ambassador_pdf_with_preview(data["name"], create_preview=create_preview)
        recipient_data = {
            "name": data["name"],
            "email": data["email"],
            "domain": "Community",
            "letter_type": "Campus Ambassador",
        }
        sender_account = "default"

    elif letter_type == "internship_letter":
        student_data = database_handler.fetch_student_from_client_sheet(data["name"])
        if not student_data:
            raise ValueError(f"Could not find '{data['name']}' in the onboarding sheet.")

        pdf_path, preview_path = pdf_generator.generate_internship_acceptance_pdf_with_preview(
            name=student_data["name"],
            month=student_data["month"],
            domain=student_data["domain"],
            create_preview=create_preview,
        )
        recipient_data = {
            "name": student_data["name"],
            "email": student_data["email"],
            "domain": student_data["domain"],
            "letter_type": "Internship Acceptance",
        }
        sender_account = "default"
        data = {
            "name": student_data["name"],
            "email": student_data["email"],
            "domain": student_data["domain"],
        }

    elif letter_type == "offer_letter":
        pdf_path, preview_path = pdf_generator.generate_offer_letter_pdf_with_preview(
            name=data["name"],
            training_from=data["training_from"],
            create_preview=create_preview,
        )
        recipient_data = {
            "name": data["name"],
            "email": data["email"],
            "domain": "General",
            "letter_type": "Offer Letter",
        }
        sender_account = "hr"

    elif letter_type == "course_certificate":
        pdf_path, preview_path = pdf_generator.generate_completion_certificate(
            name=data["name"],
            issue_date=data["date"],
            domain=data["domain"],
            identifier_id=data["cert_id"],
            create_preview=create_preview,
        )
        recipient_data = {
            "name": data["name"],
            "email": data["email"],
            "domain": data["domain"],
            "letter_type": "Course Completion Certificate",
        }
        sender_account = "default"

    elif letter_type == "ca_certificate":
        pdf_path, preview_path = pdf_generator.ca_certificate(
            name=data["name"],
            issue_date=data["date"],
            create_preview=create_preview,
        )
        recipient_data = {
            "name": data["name"],
            "email": data["email"],
            "domain": "Community",
            "letter_type": "Campus Ambassador Certificate",
        }
        sender_account = "default"

    else:
        raise ValueError("Unsupported letter type selected.")

    return {
        "letter_type": letter_type,
        "form_data": data,
        "recipient_data": recipient_data,
        "sender_account": sender_account,
        "pdf_path": os.path.abspath(pdf_path),
        "preview_path": os.path.abspath(preview_path),
    }


def send_letter_from_preview(preview_payload: Dict[str, object]) -> Tuple[bool, Dict[str, str]]:
    pdf_path = str(preview_payload["pdf_path"])
    recipient_data = dict(preview_payload["recipient_data"])
    sender_account = str(preview_payload["sender_account"])

    sent = send_personalized_email(pdf_path, recipient_data, sender_account=sender_account)
    return sent, recipient_data
