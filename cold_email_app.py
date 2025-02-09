import streamlit as st
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import pandas as pd
from datetime import datetime, timezone
import json
import schedule
import time
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
import pickle
import base64

# Gmail API scopes
SCOPES = [
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.modify',  # Required for scheduling
    'https://www.googleapis.com/auth/gmail.compose'  # Required for creating drafts
]

# Initialize session state
if 'templates' not in st.session_state:
    st.session_state.templates = {}
if 'saved_resumes' not in st.session_state:
    # Load saved resumes from the saved_resumes directory
    st.session_state.saved_resumes = {}
    if os.path.exists('saved_resumes'):
        for file in os.listdir('saved_resumes'):
            if file.endswith('.pdf'):
                name = file[:-4]  # Remove .pdf extension
                st.session_state.saved_resumes[name] = os.path.join('saved_resumes', file)
if 'recipients' not in st.session_state:
    st.session_state.recipients = []
if 'credentials' not in st.session_state:
    st.session_state.credentials = None

def get_gmail_service():
    """Get Gmail API service instance"""
    creds = st.session_state.credentials
    return build('gmail', 'v1', credentials=creds)

def authenticate_gmail():
    """Authenticate using Gmail OAuth2"""
    creds = None
    
    # Check if token file exists
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    
    # If credentials are invalid or don't exist, authenticate
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Use credentials from secrets.toml
            client_config = {
                "installed": {
                    "client_id": st.secrets["client_id"],
                    "client_secret": st.secrets["client_secret"],
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                    "redirect_uris": ["http://localhost"]
                }
            }
            flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save credentials
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    
    st.session_state.credentials = creds
    return creds

def send_email_gmail_api(to_email, subject, body, resume_path=None, scheduled_time=None):
    """Send email using Gmail API with optional scheduling"""
    try:
        service = get_gmail_service()
        message = MIMEMultipart()
        message['to'] = to_email
        message['subject'] = subject

        # Add body
        message.attach(MIMEText(body, 'plain'))

        # Add resume if provided
        if resume_path:
            with open(resume_path, 'rb') as f:
                resume = MIMEApplication(f.read(), _subtype='pdf')
                # Always set filename to Sahil_Padyal.pdf
                resume.add_header('Content-Disposition', 'attachment', 
                                filename='Sahil_Padyal.pdf')
                message.attach(resume)

        # Encode the message
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        
        # Create the email request body
        email_request = {'raw': raw_message}
        
        # Add scheduling if specified
        if scheduled_time:
            # Convert to UTC and format as RFC 3339
            utc_time = scheduled_time.astimezone(timezone.utc)
            email_request.update({
                'labelIds': ['INBOX'],
                'scheduledTime': utc_time.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
            })
        
        # Send the email
        if scheduled_time:
            # Use messages.insert for scheduled emails
            service.users().messages().insert(
                userId='me',
                body=email_request
            ).execute()
        else:
            # Use messages.send for immediate sending
            service.users().messages().send(
                userId='me',
                body=email_request
            ).execute()

        return True
    except Exception as e:
        st.error(f"Error sending email: {str(e)}")
        return False

def save_template(name, subject, body):
    """Save email template to JSON file"""
    if not name.strip() or not subject.strip() or not body.strip():
        st.error("Template name, subject, and body are required")
        return False
        
    template = {"subject": subject, "body": body}
    templates = {}
    
    if os.path.exists('email_templates.json'):
        with open('email_templates.json', 'r') as f:
            templates = json.load(f)
    
    templates[name] = template
    
    with open('email_templates.json', 'w') as f:
        json.dump(templates, f)
    
    st.session_state.templates = templates
    return True

def save_resume(name, file_content):
    """Save resume to file system"""
    os.makedirs('saved_resumes', exist_ok=True)
    file_path = os.path.join('saved_resumes', f"{name}.pdf")
    
    with open(file_path, 'wb') as f:
        f.write(file_content)
    
    st.session_state.saved_resumes[name] = file_path

def log_email(recipient, subject, status, resume_used=None):
    """Log email details to CSV file"""
    log_file = 'email_log.csv'
    date_sent = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    new_log = pd.DataFrame({
        'date_sent': [date_sent],
        'recipient': [recipient],
        'subject': [subject],
        'status': [status],
        'resume_used': [resume_used if resume_used else 'None']
    })
    
    try:
        if os.path.exists(log_file):
            existing_log = pd.read_csv(log_file)
            updated_log = pd.concat([existing_log, new_log], ignore_index=True)
        else:
            updated_log = new_log
        
        updated_log.to_csv(log_file, index=False)
    except Exception as e:
        st.error(f"Error logging email: {str(e)}")

def main():
    st.title("Cold Email Sender")

    # Email Authentication Section
    st.header("Email Authentication")
    
    # Display connection status
    if st.session_state.credentials:
        st.success("✓ Connected to Gmail")
        if st.button("Disconnect Email"):
            st.session_state.credentials = None
            if os.path.exists('token.pickle'):
                os.remove('token.pickle')
            st.experimental_rerun()
    else:
        st.warning("⚠ Not connected to Gmail")
        if st.button("Connect Gmail Account"):
            with st.spinner("Connecting to Gmail..."):
                try:
                    authenticate_gmail()
                    st.success("Successfully connected to Gmail!")
                    st.experimental_rerun()
                except Exception as e:
                    st.error(f"Failed to connect: {str(e)}")

    # Only show the rest of the app if authenticated
    if not st.session_state.credentials:
        st.info("Please connect your Gmail account to continue")
        return

    # Email composition section
    st.header("Compose Email")

    # Recipient management
    st.subheader("Recipients")
    new_recipient = st.text_input("Add recipient email")
    if st.button("Add Recipient") and new_recipient:
        if '@' not in new_recipient or '.' not in new_recipient:
            st.error("Please enter a valid email address")
        elif new_recipient not in st.session_state.recipients:
            st.session_state.recipients.append(new_recipient)
            st.success(f"Added {new_recipient}")
        else:
            st.warning("This email is already in the recipients list")

    # Display and manage recipients
    if st.session_state.recipients:
        for idx, recipient in enumerate(st.session_state.recipients):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.text(recipient)
            with col2:
                if st.button("Remove", key=f"remove_{idx}"):
                    st.session_state.recipients.pop(idx)
                    st.experimental_rerun()

    # Email content
    st.subheader("Email Content")
    subject = st.text_input("Subject", value=st.session_state.get('subject', ''))
    body = st.text_area("Body", value=st.session_state.get('body', ''))

    # Template management
    st.subheader("Email Templates")
    col1, col2 = st.columns([3, 1])
    with col1:
        template_name = st.text_input("Template Name")
    with col2:
        if st.button("Save Template"):
            if save_template(template_name, subject, body):
                st.success(f"Template '{template_name}' saved!")
                st.balloons()  # Add a fun visual feedback

    # Load templates at startup
    if os.path.exists('email_templates.json'):
        with open('email_templates.json', 'r') as f:
            templates = json.load(f)
    else:
        templates = {}

    # Template selection
    if templates:
        selected_template = st.selectbox(
            "Load Template",
            [""] + list(templates.keys()),
            key="template_selector"
        )
        
        # Only update if a template is selected and it's different from current
        if (selected_template and 
            selected_template != st.session_state.get('last_selected_template')):
            template = templates[selected_template]
            st.session_state.subject = template["subject"]
            st.session_state.body = template["body"]
            st.session_state.last_selected_template = selected_template

    # Initialize resume_path and temp_file flag
    resume_path = None
    is_temp_file = False

    # Resume management
    st.subheader("Resume Management")
    resume_tab1, resume_tab2 = st.tabs(["Upload New", "Saved Resumes"])
    
    with resume_tab1:
        uploaded_file = st.file_uploader("Upload PDF", type=['pdf'])
        resume_name = st.text_input("Save resume as (optional)")
        
        if uploaded_file and resume_name:
            if st.button("Save Resume"):
                save_resume(resume_name, uploaded_file.getvalue())
                st.success(f"Resume '{resume_name}' saved!")
        
        if uploaded_file:
            with open("temp_attachment.pdf", "wb") as f:
                f.write(uploaded_file.getvalue())
            resume_path = "temp_attachment.pdf"
            is_temp_file = True
            if 'selected_saved_resume' in st.session_state:
                del st.session_state.selected_saved_resume
    
    with resume_tab2:
        if st.session_state.saved_resumes and not uploaded_file:
            selected_resume = st.selectbox(
                "Select Saved Resume",
                [""] + list(st.session_state.saved_resumes.keys()),
                key='selected_saved_resume'
            )
            if selected_resume:
                resume_path = st.session_state.saved_resumes[selected_resume]
                is_temp_file = False
        else:
            if uploaded_file:
                st.info("Using uploaded file instead of saved resume")
            else:
                st.info("No saved resumes found")
            selected_resume = None

    # Add Email Log viewer
    st.header("Email Log")
    if os.path.exists('email_log.csv'):
        log_df = pd.read_csv('email_log.csv')
        # Sort by date in descending order
        log_df['date_sent'] = pd.to_datetime(log_df['date_sent'])
        log_df = log_df.sort_values('date_sent', ascending=False)
        # Add download button for the log
        csv = log_df.to_csv(index=False)
        st.download_button(
            "Download Email Log",
            csv,
            "email_log.csv",
            "text/csv",
            key='download-csv'
        )
        st.dataframe(log_df)
    else:
        st.info("No emails logged yet")

    # Add scheduling options
    st.subheader("Email Scheduling")
    enable_scheduling = st.checkbox("Schedule Email")
    scheduled_time = None
    
    if enable_scheduling:
        scheduled_date = st.date_input("Select Date")
        scheduled_time_input = st.time_input("Select Time")
        scheduled_datetime = datetime.combine(scheduled_date, scheduled_time_input)
        
        if scheduled_datetime <= datetime.now():
            st.error("Please select a future date and time")
            enable_scheduling = False
        else:
            scheduled_time = scheduled_datetime.astimezone().replace(microsecond=0)

    # Add template deletion
    if templates:
        col1, col2 = st.columns([3, 1])
        with col1:
            template_to_delete = st.selectbox(
                "Select template to delete",
                [""] + list(templates.keys()),
                key="template_delete_selector"
            )
        with col2:
            if st.button("Delete Template") and template_to_delete:
                templates.pop(template_to_delete)
                with open('email_templates.json', 'w') as f:
                    json.dump(templates, f)
                st.success(f"Template '{template_to_delete}' deleted!")
                st.experimental_rerun()

    # Modify the send email button section
    if st.button("Send Emails"):
        if not st.session_state.recipients:
            st.error("Please add at least one recipient email address")
        elif not subject or not body:
            st.error("Please provide both subject and body for the email")
        else:
            progress_bar = st.progress(0)
            status_text = st.empty()
            all_success = True

            for idx, email in enumerate(st.session_state.recipients):
                try:
                    success = send_email_gmail_api(
                        email, 
                        subject, 
                        body, 
                        resume_path, 
                        scheduled_time if enable_scheduling else None
                    )
                    status = "Success" if success else "Failed"
                    
                    # Log the email
                    resume_name = "Sahil_Padyal.pdf" if resume_path else None
                    log_email(email, subject, status, resume_name)
                    
                    if success:
                        progress = (idx + 1) / len(st.session_state.recipients)
                        progress_bar.progress(progress)
                        status_text.text(f"Sending: {idx + 1}/{len(st.session_state.recipients)} emails sent")
                    else:
                        all_success = False
                        st.error(f"Failed to send email to {email}")
                except Exception as e:
                    all_success = False
                    st.error(f"Failed to send email to {email}: {str(e)}")
                    log_email(email, subject, f"Error: {str(e)}", resume_name)
            
            if all_success:
                success_message = "All emails scheduled successfully!" if enable_scheduling else "All emails sent successfully!"
                st.success(success_message)
                # Clear recipients after successful sending
                st.session_state.recipients = []
                time.sleep(2)  # Give user time to see the success message

    # Cleanup temporary file after sending emails
    if is_temp_file and resume_path and os.path.exists(resume_path):
        os.remove(resume_path)

if __name__ == "__main__":
    main() 