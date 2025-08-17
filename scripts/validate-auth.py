import json
import logging
from requests_oauthlib import OAuth2Session
from oauthlib.oauth2 import InvalidGrantError

logging.basicConfig(level=logging.INFO)

CREDENTIALS_FILE = '../auth/credentials.json'
TOKEN_FILE = '../auth/token.json'

def load_credentials():
    try:
        with open(CREDENTIALS_FILE, 'r') as f:
            credentials = json.load(f)['web']
        return credentials
    except Exception as e:
        logging.error(f'Error loading credentials: {e}')
        raise

def load_token():
    try:
        with open(TOKEN_FILE, 'r') as f:
            token = json.load(f)
        return token
    except Exception as e:
        logging.error(f'Error loading token: {e}')
        raise

def check_refresh_token_validity(credentials, token):
    session = OAuth2Session(
        credentials['client_id'],
        token=token,
        auto_refresh_url=credentials['token_uri'],
        auto_refresh_kwargs={
            'client_id': credentials['client_id'],
            'client_secret': credentials['client_secret']
        }
    )
    
    try:
        session.refresh_token(credentials['token_uri'], refresh_token=token['refresh_token'])
        logging.info('Refresh token is valid!')
        return True
    except InvalidGrantError:
        logging.error('Refresh token is invalid or expired.')
        return False
    except Exception as e:
        logging.error(f'Error checking refresh token: {e}')
        return False

if __name__ == '__main__':
    try:
        credentials = load_credentials()
        token = load_token()
        
        if check_refresh_token_validity(credentials, token):
            logging.info('Token is valid!')
        else:
            logging.error('Token is not valid. You may need to reauthenticate.')
    except Exception as e:
        logging.error(f'An error occurred: {e}')
