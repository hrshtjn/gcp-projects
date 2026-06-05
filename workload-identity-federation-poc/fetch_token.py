import os
import requests
from dotenv import load_dotenv

load_dotenv()

def fetch_and_save_token():
    """
    Simulates a local app authenticating with Keycloak to obtain an OIDC token.
    Saves the token to a file so the Google Auth library (using WIF) can read it.
    """
    keycloak_token_url = os.environ.get("KEYCLOAK_TOKEN_URL")
    client_id = os.environ.get("KEYCLOAK_CLIENT_ID")
    client_secret = os.environ.get("KEYCLOAK_CLIENT_SECRET")
    
    if not all([keycloak_token_url, client_id, client_secret]):
        print("Missing Keycloak environment variables. Please check your .env file.")
        return

    # Using client_credentials for the PoC (Machine-to-Machine)
    # You can also use 'password' grant or actual OAuth2 flow for users
    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "client_credentials" 
    }
    
    print(f"Fetching token from {keycloak_token_url}...")
    response = requests.post(keycloak_token_url, data=payload)
    
    if response.status_code != 200:
        print(f"Failed to fetch token: {response.text}")
        response.raise_for_status()
        
    token = response.json().get("access_token")
    
    # Write the token to the file specified in the WIF credential config
    token_file = os.environ.get("TOKEN_FILE_PATH", "keycloak_token.txt")
    with open(token_file, "w") as f:
        f.write(token)
        
    print(f"Successfully saved Keycloak token to '{token_file}'.")

if __name__ == "__main__":
    fetch_and_save_token()