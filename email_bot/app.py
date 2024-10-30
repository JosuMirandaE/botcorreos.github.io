from flask import Flask, render_template, request, redirect, url_for, flash,session
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from twilio.rest import Client  # Para enviar mensajes de WhatsApp con Twilio
import pandas as pd
import os
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

app = Flask(__name__)
app.secret_key = "your_secret_key"  # Cambia esto por un valor seguro

# Configuración de Gmail
SCOPES = ['https://www.googleapis.com/auth/gmail.send']

# Ruta para la página de inicio
@app.route('/')
def index():
    return render_template('index.html')

# Ruta para la interfaz de Gmail
@app.route('/gmail')
def gmail():
    return render_template('gmail.html')

# Ruta para la interfaz de WhatsApp
@app.route('/whatsapp')
def whatsapp():
    return render_template('whatsapp.html')

# Ruta para autenticarse en Gmail
@app.route('/login')
def login():
    flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
    credentials = flow.run_local_server(port=0)
    with open("token.json", "w") as token:
        token.write(credentials.to_json())
    flash("Autenticación exitosa", "success")
    return redirect(url_for('gmail'))

# Ruta para enviar correo por Gmail
@app.route('/send_email', methods=['POST'])
def send_email():
    subject = request.form['subject']
    body = request.form['body']
    attachment = request.files['attachment']
    recipients_file = request.files['recipients']

    # Leer la lista de correos
    recipients = []
    if recipients_file:
        if recipients_file.filename.endswith('.xlsx') or recipients_file.filename.endswith('.xls'):
            df = pd.read_excel(recipients_file)
            recipients = df['email'].tolist()
        elif recipients_file.filename.endswith('.txt'):
            recipients = recipients_file.read().decode().splitlines()
    
    # Cargar credenciales de Gmail
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)

    if not creds or not creds.valid:
        flash("Error en la autenticación de Gmail", "error")
        return redirect(url_for('gmail'))

    # Enviar correos
    service = build('gmail', 'v1', credentials=creds)
    for recipient in recipients:
        message = {
            'raw': create_message(subject, body, recipient, attachment)
        }
        service.users().messages().send(userId="me", body=message).execute()
    
    flash("Correos enviados exitosamente", "success")
    return redirect(url_for('gmail'))

def create_message(subject, body, to, attachment):
    message = MIMEMultipart()
    message['to'] = to
    message['subject'] = subject
    message.attach(MIMEText(body, 'plain'))

    if attachment:
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(attachment.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f'attachment; filename={attachment.filename}')
        message.attach(part)

    return base64.urlsafe_b64encode(message.as_bytes()).decode()

# Ruta para enviar mensaje por WhatsApp
@app.route('/send_whatsapp', methods=['POST'])
def send_whatsapp():
    message = request.form['message']
    recipients_file = request.files['recipients']

    phone_numbers = []
    if recipients_file:
        if recipients_file.filename.endswith('.xlsx') or recipients_file.filename.endswith('.xls'):
            df = pd.read_excel(recipients_file)
            phone_numbers = df['phone'].tolist()
        elif recipients_file.filename.endswith('.txt'):
            phone_numbers = recipients_file.read().decode().splitlines()

    # Configuración del twilio (para el WhatsApp)
    account_sid = '?'
    auth_token = '?'
    client = Client(account_sid, auth_token)

    # Enviar mensajes
    for phone_number in phone_numbers:
        client.messages.create(
            body=message,
            from_='whatsapp:+14155238886',  # Número de Twilio para WhatsApp
            to=f'whatsapp:{phone_number}'
        )

    flash("Mensajes de WhatsApp enviados exitosamente", "success")
    return redirect(url_for('whatsapp'))

if __name__ == '__main__':
    app.run(debug=True)
