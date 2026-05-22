"""hurtig.ai contact form handler — receives POST, sends email via Hostinger SMTP."""
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs
import json
import html

SMTP_HOST = os.environ.get('SMTP_HOST', 'smtp.hostinger.com')
SMTP_PORT = int(os.environ.get('SMTP_PORT', '465'))
SMTP_USER = os.environ.get('SMTP_USER', 'laura@hurtig.ai')
SMTP_PASS = os.environ.get('SMTP_PASS', '')
TO_EMAIL = os.environ.get('TO_EMAIL', 'laura@hurtig.ai')
ALLOWED_ORIGINS = ['https://hurtig.ai', 'https://www.hurtig.ai']


class FormHandler(BaseHTTPRequestHandler):
    def _cors_headers(self):
        origin = self.headers.get('Origin', '')
        if origin in ALLOWED_ORIGINS:
            self.send_header('Access-Control-Allow-Origin', origin)
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors_headers()
        self.end_headers()

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8')
        content_type = self.headers.get('Content-Type', '')

        if 'json' in content_type:
            data = json.loads(body)
        else:
            data = {k: v[0] for k, v in parse_qs(body).items()}

        # Honeypot check
        if data.get('_gotcha'):
            self.send_response(302)
            self.send_header('Location', 'https://hurtig.ai/booking.html?sent=spam')
            self.end_headers()
            return

        TOPIC_LABELS = {
            'local-llm': 'Local LLM Deployment',
            'legal-ai': 'LegalAI / Medical Criminal Law',
            'strategy': 'AI Strategy & Ideation',
            'shadowing': 'AI Shadowing (1:1 Coaching)',
            'support': 'Maintenance & Support',
            'research': 'Research Collaboration',
            'other': 'Other',
        }
        TOPIC_LABELS_DE = {
            'local-llm': 'Lokales LLM-Deployment',
            'legal-ai': 'LegalAI / Medizinstrafrecht',
            'strategy': 'KI-Strategie & Ideenfindung',
            'shadowing': 'AI Shadowing (1:1 Coaching)',
            'support': 'Wartung & Support',
            'research': 'Forschungskooperation',
            'other': 'Sonstiges',
        }

        name = html.escape(data.get('name', 'Unknown'))
        email = html.escape(data.get('email', 'no-reply@hurtig.ai'))
        topic_raw = data.get('topic', 'General')
        topic = html.escape(TOPIC_LABELS.get(topic_raw, topic_raw))
        message = html.escape(data.get('message', '(no message)'))

        msg = MIMEMultipart('alternative')
        msg['Subject'] = '[hurtig.ai] ' + topic + ' — from ' + name
        msg['From'] = SMTP_USER
        msg['To'] = TO_EMAIL
        msg['Reply-To'] = email

        text_body = (
            "New contact form submission from hurtig.ai\n\n"
            "Name: " + name + "\n"
            "Email: " + email + "\n"
            "Topic: " + topic + "\n\n"
            "Message:\n" + message + "\n"
        )

        html_body = (
            '<div style="font-family:sans-serif;max-width:600px">'
            '<h2 style="color:#a03f28">New Contact Form Submission</h2>'
            '<table style="border-collapse:collapse;width:100%">'
            '<tr><td style="padding:8px;font-weight:bold;color:#666">Name</td>'
            '<td style="padding:8px">' + name + '</td></tr>'
            '<tr><td style="padding:8px;font-weight:bold;color:#666">Email</td>'
            '<td style="padding:8px"><a href="mailto:' + email + '">' + email + '</a></td></tr>'
            '<tr><td style="padding:8px;font-weight:bold;color:#666">Topic</td>'
            '<td style="padding:8px">' + topic + '</td></tr>'
            '</table>'
            '<div style="margin-top:16px;padding:16px;background:#fff8ef;'
            'border-left:3px solid #a03f28;border-radius:4px">'
            '<p style="margin:0;white-space:pre-wrap">' + message + '</p>'
            '</div>'
            '<p style="margin-top:24px;color:#999;font-size:12px">'
            'Sent via hurtig.ai contact form</p>'
            '</div>'
        )

        msg.attach(MIMEText(text_body, 'plain'))
        msg.attach(MIMEText(html_body, 'html'))

        # Confirmation email to the requestor
        is_de = '/de/' in self.headers.get('Referer', '')
        topic_display = html.escape(TOPIC_LABELS_DE.get(topic_raw, topic_raw)) if is_de else topic
        confirm = MIMEMultipart('alternative')
        confirm['Subject'] = ('Ihre Anfrage bei hurtig.ai' if is_de else 'Your inquiry at hurtig.ai')
        confirm['From'] = SMTP_USER
        confirm['To'] = data.get('email', '')

        LOGO_URL = 'https://hurtig.ai/assets/logo-email.png'
        PHONE = '+49 176 5652 1182'
        PHONE_HREF = 'tel:+4917656521182'

        # Shared HTML blocks
        header_html = (
            '<table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:32px"><tr>'
            '<td style="padding-bottom:20px;border-bottom:2px solid #a03f28">'
            '<a href="https://hurtig.ai" style="text-decoration:none;display:inline-flex;align-items:center">'
            '<img src="' + LOGO_URL + '" alt="hurtig.ai" width="28" height="28" '
            'style="width:28px;height:28px;vertical-align:middle;margin-right:10px">'
            '<span style="font-size:22px;font-weight:700;font-style:italic;color:#1e1b14;vertical-align:middle">'
            'hurtig.ai</span></a>'
            '</td></tr></table>'
        )

        footer_de_html = (
            '<table width="100%" cellpadding="0" cellspacing="0" style="margin-top:32px;'
            'border-top:1px solid #ddc0ba;padding-top:24px"><tr><td>'
            '<p style="font-size:15px;line-height:1.6;margin:0 0 4px">'
            'Mit freundlichen Gr&uuml;&szlig;en,</p>'
            '<p style="font-size:15px;line-height:1.4;margin:0 0 16px">'
            '<strong>Laura Isabell Turner</strong></p>'
            '<table cellpadding="0" cellspacing="0"><tr>'
            '<td style="padding:0 16px 0 0;border-right:1px solid #ddc0ba">'
            '<a href="https://hurtig.ai" style="color:#a03f28;text-decoration:none;font-size:13px;font-weight:600">'
            'hurtig.ai</a></td>'
            '<td style="padding:0 16px;border-right:1px solid #ddc0ba">'
            '<a href="mailto:laura@hurtig.ai" style="color:#56423d;text-decoration:none;font-size:13px">'
            'laura@hurtig.ai</a></td>'
            '<td style="padding:0 0 0 16px">'
            '<a href="' + PHONE_HREF + '" style="color:#56423d;text-decoration:none;font-size:13px">'
            '' + PHONE + '</a></td>'
            '</tr></table>'
            '<p style="font-size:11px;color:#8a726c;margin:20px 0 0">'
            'Kurzfristige Absagen bitte per Telefon oder E-Mail.</p>'
            '</td></tr></table>'
        )

        footer_en_html = (
            '<table width="100%" cellpadding="0" cellspacing="0" style="margin-top:32px;'
            'border-top:1px solid #ddc0ba;padding-top:24px"><tr><td>'
            '<p style="font-size:15px;line-height:1.6;margin:0 0 4px">'
            'Best regards,</p>'
            '<p style="font-size:15px;line-height:1.4;margin:0 0 16px">'
            '<strong>Laura Isabell Turner</strong></p>'
            '<table cellpadding="0" cellspacing="0"><tr>'
            '<td style="padding:0 16px 0 0;border-right:1px solid #ddc0ba">'
            '<a href="https://hurtig.ai" style="color:#a03f28;text-decoration:none;font-size:13px;font-weight:600">'
            'hurtig.ai</a></td>'
            '<td style="padding:0 16px;border-right:1px solid #ddc0ba">'
            '<a href="mailto:laura@hurtig.ai" style="color:#56423d;text-decoration:none;font-size:13px">'
            'laura@hurtig.ai</a></td>'
            '<td style="padding:0 0 0 16px">'
            '<a href="' + PHONE_HREF + '" style="color:#56423d;text-decoration:none;font-size:13px">'
            '' + PHONE + '</a></td>'
            '</tr></table>'
            '<p style="font-size:11px;color:#8a726c;margin:20px 0 0">'
            'For short-notice cancellations, please call or email.</p>'
            '</td></tr></table>'
        )

        if is_de:
            confirm_text = (
                'Hallo ' + name + ',\n\n'
                'vielen Dank für Ihre Nachricht. Wir melden uns in der Regel innerhalb von 24 Stunden.\n\n'
                'Ihre Anfrage:\n'
                'Thema: ' + topic_display + '\n'
                'Nachricht: ' + message + '\n\n'
                'Mit freundlichen Grüßen,\n'
                'Laura Isabell Turner\nhurtig.ai\n'
                'laura@hurtig.ai | ' + PHONE + '\n'
            )
            confirm_html = (
                '<div style="font-family:-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif;max-width:560px;margin:0 auto;color:#1e1b14">'
                + header_html +
                '<p style="font-size:15px;line-height:1.6">Hallo ' + name + ',</p>'
                '<p style="font-size:15px;line-height:1.6;color:#56423d">'
                'vielen Dank f&uuml;r Ihre Nachricht. Wir melden uns in der Regel innerhalb von 24 Stunden.</p>'
                '<table width="100%" cellpadding="0" cellspacing="0" style="margin:24px 0">'
                '<tr><td style="padding:20px;background:#fff8ef;border-left:3px solid #a03f28">'
                '<p style="margin:0 0 4px;color:#8a726c;font-size:11px;text-transform:uppercase;letter-spacing:0.1em">Ihre Anfrage</p>'
                '<p style="margin:0 0 12px;font-size:14px"><strong>Thema:</strong> ' + topic_display + '</p>'
                '<p style="margin:0;font-size:14px;white-space:pre-wrap;color:#56423d">' + message + '</p>'
                '</td></tr></table>'
                + footer_de_html +
                '</div>'
            )
        else:
            confirm_text = (
                'Hello ' + name + ',\n\n'
                'Thank you for reaching out. We typically respond within 24 hours.\n\n'
                'Your inquiry:\n'
                'Topic: ' + topic + '\n'
                'Message: ' + message + '\n\n'
                'Best regards,\n'
                'Laura Isabell Turner\nhurtig.ai\n'
                'laura@hurtig.ai | ' + PHONE + '\n'
            )
            confirm_html = (
                '<div style="font-family:-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif;max-width:560px;margin:0 auto;color:#1e1b14">'
                + header_html +
                '<p style="font-size:15px;line-height:1.6">Hello ' + name + ',</p>'
                '<p style="font-size:15px;line-height:1.6;color:#56423d">'
                'Thank you for reaching out. We typically respond within 24 hours.</p>'
                '<table width="100%" cellpadding="0" cellspacing="0" style="margin:24px 0">'
                '<tr><td style="padding:20px;background:#fff8ef;border-left:3px solid #a03f28">'
                '<p style="margin:0 0 4px;color:#8a726c;font-size:11px;text-transform:uppercase;letter-spacing:0.1em">Your inquiry</p>'
                '<p style="margin:0 0 12px;font-size:14px"><strong>Topic:</strong> ' + topic + '</p>'
                '<p style="margin:0;font-size:14px;white-space:pre-wrap;color:#56423d">' + message + '</p>'
                '</td></tr></table>'
                + footer_en_html +
                '</div>'
            )

        confirm.attach(MIMEText(confirm_text, 'plain'))
        confirm.attach(MIMEText(confirm_html, 'html'))

        try:
            with smtplib.SMTP(SMTP_HOST, 587, timeout=10) as smtp:
                smtp.starttls()
                smtp.login(SMTP_USER, SMTP_PASS)
                smtp.send_message(msg)
                if data.get('email'):
                    smtp.send_message(confirm)
            print('Email sent: ' + name + ' <' + email + '> — ' + topic)
        except Exception as e:
            print('SMTP error: ' + str(e))
            self.send_response(500)
            self._cors_headers()
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'Failed to send. Please email laura@hurtig.ai directly.')
            return

        referer = self.headers.get('Referer', '')
        if '/de/' in referer:
            redirect = 'https://hurtig.ai/de/booking.html?sent=1'
        else:
            redirect = 'https://hurtig.ai/booking.html?sent=1'

        self.send_response(302)
        self._cors_headers()
        self.send_header('Location', redirect)
        self.end_headers()

    def log_message(self, fmt, *args):
        print('[contact-form] ' + str(args[0]))


if __name__ == '__main__':
    if not SMTP_PASS:
        print('WARNING: SMTP_PASS not set — emails will fail!')
    server = HTTPServer(('0.0.0.0', 8080), FormHandler)
    print('Contact form handler listening on :8080')
    server.serve_forever()
