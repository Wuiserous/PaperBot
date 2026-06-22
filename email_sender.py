# email_sender.py
import os
import resend
from pathlib import Path
from config_loader import load_project_env

load_project_env()

# --- RESEND CONFIGURATION ---
# Make sure to add RESEND_API_KEY="re_123..." to your .env or PythonAnywhere env vars.
resend.api_key = os.getenv("RESEND_API_KEY")

DEFAULT_EMAIL = os.getenv("DEFAULT_EMAIL", "support@persevex.com")
HR_EMAIL = os.getenv("HR_EMAIL", "hr@persevex.com")

# --- BCC CONFIGURATION ---
BCC_EMAIL = os.getenv("BCC_EMAIL", "startling550@gmail.com")


def get_email_templates(letter_type, recipient_name, domain):
    """
    Returns the appropriate email subject and HTML body based on the letter type.
    """
    # Template for Campus Ambassador
    if letter_type.lower() == "campus ambassador" or letter_type.lower() == "campus ambassador certificate":
        subject = "Appointment Letter – Campus Ambassador at Persevex"
        body = f"""
        <html>
        <body>
            <p>Dear {recipient_name},</p>
            <p>Greetings from Persevex!</p>
            <p>We are excited to officially welcome you as a Campus Ambassador at Persevex. Please find attached your appointment letter, which outlines your key responsibilities, benefits, and the impact you can make as part of our team.</p>
            <p>As a Campus Ambassador, you will play a vital role in building brand awareness, promoting our programs, and fostering student engagement at your institution. Your energy and initiative will be instrumental in expanding Persevex’s mission to empower learners across campuses.</p>
            <p>If you have any questions or need further clarification, feel free to reach out to us at 📧 support@persevex.com.</p>
            <p>We look forward to seeing your contributions and success in this role.</p>
            <p>📣 Feel free to share this exciting opportunity on LinkedIn by posting about your new role, tagging @Persevex and using hashtags such as #Persevex #CampusAmbassador #Leadership #StudentOpportunity #EmpoweringLearners.</p>
            <br>
            <p>Best regards,<br>
            Team Persevex<br>
            📧 support@persevex.com<br>
            🌐 www.persevex.com</p>
        </body>
        </html>
        """
        return subject, body

    elif letter_type.lower() == "internship acceptance":
        subject = "Internship Acceptance Letter at Persevex"
        body = f"""
        <html>
        <body>
            <p>Dear {recipient_name},</p>
            <p>Congratulations once again!<br>
            Please find attached your official internship acceptance letter for the <b>{domain} Intern</b> role at Persevex.</p>
            <p>We’re excited to have you onboard and look forward to your contributions during this internship.</p>
            <p>If you’re comfortable, we’d love for you to share this opportunity and your experience on LinkedIn by tagging @Persevex and helping others know about us.</p>
            <br>
            <p>Best regards,<br>
            Shanmukh Shekar K C<br>
            Administrator<br>
            📧 support@persevex.com</p>
        </body>
        </html>
        """
        return subject, body
    elif letter_type.lower() == "offer letter":
        subject = f"Offer Letter for the position of Business Development Associate at Persevex."
        body = f"""
                <html>
                <body style="font-family: Arial, sans-serif; line-height: 1.6;">
                    <p>Dear {recipient_name},</p>
                    <p>Greetings from Persevex Education Consultancy LLP!</p>
                    <p>Congratulations once again! Please find attached your official Offer Letter for the position of <b>Business Development Associate</b> at Persevex.</p>
                    <p>To proceed with your onboarding, kindly complete the following steps within <b>two working days</b>:</p>
                    <ol>
                        <li>Review and sign the offer letter (a digital or scanned signature is acceptable).</li>
                        <li>Email the signed offer letter along with scanned copies of the following documents:
                            <ul>
                                <li>Academic certificates: Graduation (if applicable)</li>
                                <li>A recent passport-sized photograph</li>
                                <li>A government-issued ID (Aadhaar / Voter ID / Driving License)</li>
                                <li>PAN Card and Bank Account details (Account Number and IFSC Code)</li>
                            </ul>
                        </li>
                    </ol>
                    <p>Please reply to this email with all the required documents attached.</p>
                    <p><b><u>Office Location:</u></b><br>
                    Persevex LLP<br>
                    5A, 1st A Cross Road, Dollar Scheme Colony,<br>
                    1st Stage, BTM Layout, Bengaluru, Karnataka – 560068</p>
                    <p>We are thrilled to have you onboard and look forward to your contributions to the team.</p>
                    <br>
                    <p>Warm regards,<br>
                    Bhumika Vijay Shinde<br>
                    Persevex LLP</p>
                </body>
                </html>
                """
        return subject, body
    else:
        subject = "A Letter from Persevex"
        body = f"""<p>Dear {recipient_name},</p><p>Please find your document attached.</p>"""
        return subject, body


def send_personalized_email(pdf_path: str, recipient_data: dict, sender_account: str = 'default'):
    """
    Sends an email using the Resend API with a PDF attachment.
    """
    try:
        if not resend.api_key:
            print("[ERROR] RESEND_API_KEY is not configured.")
            return False

        # 1. Determine Sender
        if sender_account == 'hr':
            # Resend format: "Friendly Name <email@domain.com>"
            from_email = f"Persevex HR <{HR_EMAIL}>"
        else:
            from_email = f"Persevex Support <{DEFAULT_EMAIL}>"

        recipient_name = recipient_data["name"]
        recipient_email = recipient_data["email"]
        domain = recipient_data["domain"]
        letter_type = recipient_data["letter_type"]

        # 2. Get Subject and Body
        subject, html_body = get_email_templates(letter_type, recipient_name, domain)

        # 3. Handle PDF Attachment
        pdf_path_obj = Path(pdf_path)
        if not pdf_path_obj.is_file():
            print(f"[ERROR] PDF file not found at: {pdf_path}")
            return False

        # Read file as binary
        with open(pdf_path_obj, "rb") as f:
            # Resend SDK expects binary content as a list of integers for attachments
            file_content = list(f.read())

        attachment_filename = f"{letter_type.replace(' ', '_')}.pdf"

        # 4. Construct Resend Parameters
        params: resend.Emails.SendParams = {
            "from": from_email,
            "to": [recipient_email],
            "bcc": [BCC_EMAIL],
            "subject": subject,
            "html": html_body,
            "attachments": [
                {
                    "filename": attachment_filename,
                    "content": file_content
                }
            ]
        }

        print(f"Sending email via Resend API to {recipient_name}...")

        # 5. Send Email
        response = resend.Emails.send(params)

        # Check if an ID was returned to confirm success
        response_id = _response_id(response)
        if response_id:
            print(f"Successfully sent email to {recipient_name}. ID: {response_id}")
            return True
        else:
            print(f"[ERROR] API called but no ID returned: {response}")
            return False

    except Exception as e:
        print(f"[ERROR] An error occurred while sending the email via Resend: {e}")
        return False


def _response_id(response) -> str | None:
    if isinstance(response, dict):
        return response.get("id")
    return getattr(response, "id", None)
