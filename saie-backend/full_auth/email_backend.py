from django.core.mail.backends.smtp import EmailBackend
from django.core.mail import EmailMultiAlternatives
from django.conf import settings

class GlobalHTMLBackend(EmailBackend):
    """
    Wrap every outgoing email into your global HTML template automatically.
    """

    def send_messages(self, email_messages):
        wrapped = []

        from_email = settings.DEFAULT_FROM_EMAIL

        for msg in email_messages:
            subject = msg.subject
            to = msg.to
            text = msg.body

            html = f"""
            <html>
              <body style="font-family: Arial; padding:20px;">
                <h2 style="color:#333;">SAIE CLIPS</h2>

                <p>{text}</p>

                <hr style="margin:20px 0;">
                <p style="font-size:12px; color:#777;">
                  Sent from info@saie-clips.com<br>
                  © 2025 SAIE CLIPS
                </p>
              </body>
            </html>
            """

            new_msg = EmailMultiAlternatives(
                subject=subject,
                body=text,
                from_email=from_email,
                to=to,
            )
            new_msg.attach_alternative(html, "text/html")
            wrapped.append(new_msg)

        return super().send_messages(wrapped)