import pandas as pd
import numpy as np
import json
import requests
from dotenv import load_dotenv 
import os
import time
import smtplib
import getpass
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


### For Prototyping
import warnings
warnings.filterwarnings('ignore')

def _setup():
    load_dotenv()
    API_KEY = os.getenv("API_KEY")
    headers = {
        "token":API_KEY
    }

    with open ("exchange_root_addresses.json") as f:
        exchange_addresses = json.load(f)

    return exchange_addresses, headers

def call_clusters_endpoint(address,asset,headers):
    url = f'https://iapi.chainalysis.com/clusters/{address}/{asset}/summary?outputAsset=NATIVE'
    r = requests.get(url,headers=headers)
    if r.status_code == 200:
        print(f"HTTP 200 for {address} on {asset}")
    else:
        print(f"Error {r.status_code} during API request for {address} on {asset}")
    response = json.loads(r.text)
    return response

def set_time_interval():
    # Get input from user
    time_hours = float(input("Enter the query time interval in hours (e.g. 24): "))
    if time_hours == '':
        time_hours = 24
    # Convert input hours to seconds.
    return time_hours * 60 * 60

def set_alert_threshold():
    # Get input from user
    threshold = float(input("Enter the alert threshold as a decimal: "))
    if threshold == '':
        threshold = 0.2
    return threshold

def set_alerting_parameters():
    recipient_email = input("Enter alerting recipient email address: ")
    sending_email = input("Enter your email address to send from: ")
    smtp_url = input("Set SMTP URL (e.g. smtp.google.com): ")
    smtp_port = float(input("Set SMTP Port (e.g. 587): "))
    smtp_user = input("Set SMTP Username: ")
    smtp_pass = getpass.getpass(prompt = "Set SMTP Password: ")
    return recipient_email, sending_email, smtp_url, smtp_port, smtp_user, smtp_pass

def send_email(subject, body, to_email, from_email, smtp_server, smtp_port, smtp_user, smtp_pass):
    msg = MIMEMultipart()
    msg['From'] = from_email
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))
    server = smtplib.SMTP(smtp_server, smtp_port)
    server.starttls()
    server.login(smtp_user, smtp_pass)
    text = msg.as_string()
    server.sendmail(from_email, to_email, text)
    server.quit()

def main():
    # Initial setup
    exchange_addresses, headers = _setup()

    # Initialize empty df with columns for 'Date' and all exchanges and assets
    df_columns = ['Date'] + [f'{exchange}_{asset}' for exchange in exchange_addresses for asset in exchange_addresses[exchange]]
    df = pd.DataFrame(columns=df_columns)

    # Setting user input variables
    time_interval = set_time_interval()
    alert_threshold = set_alert_threshold()
    recipient_email, sending_email, smtp_url, smtp_port, smtp_user, smtp_pass = set_alerting_parameters()

    while True:
        # Get data for each exchange and asset
        for exchange in exchange_addresses:
            for asset in exchange_addresses[exchange]:
                response = call_clusters_endpoint(exchange_addresses[exchange][asset], asset, headers)
                
                # Get the balance
                balance = response.get('balance')
                
                # Append the balance and current date to the dataframe
                df = df.append({'Date': pd.to_datetime('today'), f'{exchange}_{asset}': balance}, ignore_index=True)
                
                # If there are at least two entries, calculate the balance change
                if len(df) >= 2:
                    balance_change = df[f'{exchange}_{asset}'].pct_change().iloc[-1]
                    
                    # If the balance change exceeds the threshold, send an email alert
                    if abs(balance_change) >= alert_threshold:
                        send_email("Balance Alert",
                                   f"The balance for {asset} on {exchange} has changed by {balance_change:.2%}.",
                                   recipient_email, sending_email, smtp_url, smtp_port, smtp_user, smtp_pass)
                        
        # Sleep for the specified interval before making the next request
        time.sleep(time_interval)

        df.to_csv('balance_data.csv',index=False)

# Start the script
if __name__ == "__main__":
    main()
