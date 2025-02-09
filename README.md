# Cold Email Assistant
Easily manage and track sending cold emails for job search.

## Features
- Resume Management
- Email template management
- Email tracking and logging
- Streamlit web interface

## Prerequisites

- Python 3.8 or higher
- Google Cloud Platform account with Gmail API enabled
- OAuth 2.0 Client Credentials
  
## Installation

1. Clone the repository

2. Create and activate a virtual environment
   
3. Install required packages: pip install -r requirements.txt

4. Set up Google OAuth 2.0:
   - Go to [Google Cloud Console](https://console.cloud.google.com)
   - Create a new project or select an existing one
   - Enable the Gmail API
   - Configure the OAuth consent screen
   - Create OAuth 2.0 Client Credentials
   - Download the client configuration file and save it as `credentials.json` in the project root


## Usage

1. Start the Streamlit application: streamlit run cold_email_app.py
2. Send me a request to add you to test users @shlpadyal@gmail.com
3. Navigate to `http://localhost:8501` in your web browser

4. First-time setup:
   - Click "Authorize Gmail" to complete OAuth authentication
   - Grant the necessary permissions
   - The authentication token will be saved as `token.pickle`

5. Using the application:
   - Upload your resume and the job description
   - Generate and customize your email
   - Send or save the email for later

## Email Templates

- Default templates are provided in `email_templates.json`
- Customize templates through the web interface
- New templates are automatically saved

## Logging

- All sent emails are logged in `email_log.csv`
- View email history and statistics in the application

## Contributing

1. Fork the repository
2. Create a new branch
3. Make your changes
4. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support, please open an issue in the GitHub repository or contact [shlpadyal@gmail.com].
