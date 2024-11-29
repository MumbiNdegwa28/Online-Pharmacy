import requests
import json
from requests.auth import HTTPBasicAuth
from datetime import datetime
import base64
class MpesaCredentials:
    consumer_key = 'qGGvcCbvDKwX1h5S95vPy7gBKaI43xjg9jCzY5iMoGnxZ5G5'
    consumer_secret = '9Q12LudJh8NLnMmgoMGjGPDXgJtniWDrXMj7y6xBuN0dpAQOBRGlV5e6XUJCWrAn'
    api_url = 'https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials' #same for everyone, changes when website goes live

#generating access token
class MpesaAccessToken:
    r= requests.get(MpesaCredentials.api_url,
                    auth=HTTPBasicAuth(MpesaCredentials.consumer_key,   MpesaCredentials.consumer_secret)
                    )
    mpesa_access_token = json.loads(r.text)['access_token']

#generating password
class MpesaPassword:
    lipa_time=datetime.now().strftime('%Y%m%d%H%M%S')
    business_short_code = '174379' #given  by Daraja
    OffsetValue = '0'
    passkey = 'bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919' #gotten when you simulate website under APIs as a test credential, it is same for every website
    #encoding the password to json format
    data_to_encode = business_short_code + passkey + lipa_time
    online_password = base64.encode(data_to_encode.encode())
    #decoding to a format that can be understood by HTML files
    decode_password = online_password.decode('utf-8')
