"""
Order Intake - Step 1: Read & Categorize Customer Emails
-----------------------------------------------------------
Connects to a Gmail inbox over IMAP, reads new (unread) customer emails,
classifies each one into a supply-chain intake category using FREE
keyword-based rules (no paid API needed), and prints the result to the
terminal.

SETUP REQUIRED before running:
1. Fill in EMAIL_ACCOUNT and APP_PASSWORD below.
2. APP_PASSWORD must be a Gmail "App Password", not your normal Gmail
   password (Gmail blocks plain-password IMAP logins). To generate one:
   - Enable 2-Step Verification on the Google account
   - Go to https://myaccount.google.com/apppasswords
   - Create an app password for "Mail" and paste the 16-char code below
3. No extra packages needed — only Python's standard library is used.


import imaplib
import email
from email.header import decode_header
import time

# ================= CONFIG (fill these in) =================
EMAIL_ACCOUNT = "sm9122158@gmail.com"
APP_PASSWORD = "hdbe iozt jxnm oqtq"

IMAP_SERVER = "imap.gmail.com"
CHECK_INTERVAL_SECONDS = 30   # how often to poll the inbox

"""

"""
Order Intake - Step 1: Read & Categorize Customer Emails
-----------------------------------------------------------
Connects to a Gmail inbox over IMAP, classifies each customer email into a
supply-chain intake category using FREE keyword-based rules (no paid API
needed), and prints the result to the terminal.

Two modes, chosen at runtime:
  live  - ignores everything already in the inbox; only processes mail
          that arrives AFTER you start this mode, checked every
          CHECK_INTERVAL_SECONDS. Runs until Ctrl+C.
  range - asks for a FROM and TO date (dd/mm/yyyy) and processes only
          the emails received within that window, then exits.

SETUP REQUIRED before running:
1. Fill in EMAIL_ACCOUNT and APP_PASSWORD below.
2. APP_PASSWORD must be a Gmail "App Password", not your normal Gmail
   password (Gmail blocks plain-password IMAP logins). To generate one:
   - Enable 2-Step Verification on the Google account
   - Go to https://myaccount.google.com/apppasswords
   - Create an app password for "Mail" and paste the 16-char code below
3. No extra packages needed — only Python's standard library is used.
"""

import imaplib
import email
from email.header import decode_header
from datetime import datetime, timedelta
import time

# ================= CONFIG (fill these in) =================
EMAIL_ACCOUNT = "sm9122158@gmail.com"
APP_PASSWORD = "hdbe iozt jxnm oqtq"

IMAP_SERVER = "imap.gmail.com"
CHECK_INTERVAL_SECONDS = 30   # how often to poll the inbox
# =============================================================

# Each category maps to a list of keywords/phrases (lowercase) that, if
# found in the subject+body, count as a vote for that category. The
# category with the most votes wins; ties go to the earlier category in
# this list. Tune these lists as you see real customer emails.
CATEGORY_KEYWORDS = {
    "Order Cancellation": [
        "cancel my order", "cancel order", "cancellation", "no longer need",
        "please cancel", "want to cancel",
    ],
    "Order Modification": [
        "change my order", "modify order", "update the order", "amend",
        "change quantity", "change the address", "reschedule delivery",
        "update my order",
    ],
    "Complaint / Issue": [
        "complaint", "damaged", "defective", "wrong item", "not working",
        "poor quality", "refund", "unhappy", "disappointed", "issue with",
        "problem with", "missing item", "incomplete order",
    ],
    "Delivery / Shipping Inquiry": [
        "tracking", "shipment", "delivery status", "when will it arrive",
        "shipping update", "courier", "dispatch", "eta", "delayed",
        "out for delivery",
    ],
    "Quotation / Pricing Inquiry": [
        "quotation", "quote", "price list", "pricing", "cost estimate",
        "how much does", "bulk discount", "rfq",
    ],
    "New Order Request": [
        "place an order", "new order", "i would like to order",
        "purchase order", "po number", "need to order", "order request",
        "would like to purchase",
    ],
}


def classify_email(subject: str, body: str) -> str:
    """Keyword-based classification: score each category, return the best match."""
    text = f"{subject}\n{body}".lower()

    scores = {category: 0 for category in CATEGORY_KEYWORDS}
    for category, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                scores[category] += 1

    best_category = max(scores, key=scores.get)
    if scores[best_category] == 0:
        return "Other"
    return best_category


def decode_mime_words(s: str) -> str:
    if not s:
        return ""
    decoded = decode_header(s)
    return "".join(
        (t[0].decode(t[1] or "utf-8", errors="ignore") if isinstance(t[0], bytes) else t[0])
        for t in decoded
    )


def get_email_body(msg) -> str:
    """Extract the plain-text body, falling back to HTML if needed."""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            disposition = str(part.get("Content-Disposition"))
            if content_type == "text/plain" and "attachment" not in disposition:
                charset = part.get_content_charset() or "utf-8"
                payload = part.get_payload(decode=True)
                if payload:
                    return payload.decode(charset, errors="ignore")
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                charset = part.get_content_charset() or "utf-8"
                payload = part.get_payload(decode=True)
                if payload:
                    return payload.decode(charset, errors="ignore")
    else:
        charset = msg.get_content_charset() or "utf-8"
        payload = msg.get_payload(decode=True)
        if payload:
            return payload.decode(charset, errors="ignore")
    return ""


def print_email(msg):
    """Decode one email message, classify it, and print it to the terminal."""
    subject = decode_mime_words(msg.get("Subject", ""))
    from_ = decode_mime_words(msg.get("From", ""))
    date_ = msg.get("Date", "")
    body = get_email_body(msg).strip()

    category = classify_email(subject, body)

    print("=" * 70)
    print(f"From     : {from_}")
    print(f"Subject  : {subject}")
    print(f"Date     : {date_}")
    print(f"Category : {category}")
    print("-" * 70)
    print("Body:")
    print(body[:1000] if body else "(no readable body)")
    print("=" * 70 + "\n")


def connect():
    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    mail.login(EMAIL_ACCOUNT, APP_PASSWORD)
    mail.select("inbox")
    return mail


def get_current_max_uid(mail) -> int:
    """Highest UID currently in the inbox, used as the 'live' cutoff point."""
    status, data = mail.uid("search", None, "ALL")
    if status != "OK" or not data or not data[0]:
        return 0
    uids = data[0].split()
    return int(uids[-1]) if uids else 0


def run_live_mode():
    """Only process mails that arrive AFTER this mode was started."""
    mail = connect()
    last_uid = get_current_max_uid(mail)
    mail.logout()
    print("Live mode started. Ignoring existing mail, watching for new arrivals only.")
    print(f"Checking every {CHECK_INTERVAL_SECONDS}s. Press Ctrl+C to stop.\n")

    try:
        while True:
            try:
                # Reconnect fresh each cycle - a long-lived IMAP connection can
                # go stale and not report newly arrived mail on Gmail's server.
                mail = connect()
                status, data = mail.uid("search", None, f"UID {last_uid + 1}:*")
                new_uids = []
                if status == "OK" and data and data[0]:
                    new_uids = [int(u) for u in data[0].split() if int(u) > last_uid]
                    for uid in sorted(new_uids):
                        status, msg_data = mail.uid("fetch", str(uid), "(RFC822)")
                        for response_part in msg_data:
                            if isinstance(response_part, tuple):
                                msg = email.message_from_bytes(response_part[1])
                                print_email(msg)
                        last_uid = uid
                mail.logout()
                if not new_uids:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] checked - no new mail")
            except (imaplib.IMAP4.error, OSError) as e:
                print(f"Connection hiccup, will retry next cycle: {e}")
            time.sleep(CHECK_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        print("\nStopped live monitoring.")


def run_range_mode():
    """Process mails whose date falls within a user-given dd/mm/yyyy range."""
    while True:
        try:
            from_str = input("Enter FROM date (dd/mm/yyyy): ").strip()
            to_str = input("Enter TO date (dd/mm/yyyy): ").strip()
            date_from = datetime.strptime(from_str, "%d/%m/%Y")
            date_to = datetime.strptime(to_str, "%d/%m/%Y")
            break
        except ValueError:
            print("Invalid format. Please use dd/mm/yyyy, e.g. 05/09/2026\n")

    # IMAP SEARCH is inclusive on SINCE and exclusive on BEFORE, so add
    # a day to the "to" date to include the whole end day.
    imap_since = date_from.strftime("%d-%b-%Y")
    imap_before = (date_to + timedelta(days=1)).strftime("%d-%b-%Y")

    mail = connect()
    status, data = mail.search(None, f'(SINCE {imap_since} BEFORE {imap_before})')
    if status != "OK" or not data or not data[0]:
        print(f"No emails found between {from_str} and {to_str}.")
        mail.logout()
        return

    email_ids = data[0].split()
    print(f"Found {len(email_ids)} email(s) between {from_str} and {to_str}.\n")

    for eid in email_ids:
        status, msg_data = mail.fetch(eid, "(RFC822)")
        for response_part in msg_data:
            if isinstance(response_part, tuple):
                msg = email.message_from_bytes(response_part[1])
                print_email(msg)

    mail.logout()
    print("Done processing date range.")


def main():
    print(f"Inbox: {EMAIL_ACCOUNT}\n")
    print("Choose a mode:")
    print("  1) live  - only process NEW mail received from now onward")
    print("  2) range - process mail received within a date range (dd/mm/yyyy)")
    choice = input("Type 'live' or 'range': ").strip().lower()

    if choice == "live":
        run_live_mode()
    elif choice == "range":
        run_range_mode()
    else:
        print("Unrecognized choice. Please run again and type 'live' or 'range'.")


if __name__ == "__main__":
    main()