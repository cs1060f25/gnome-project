import os.path
import jwt
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "openid",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/userinfo.email"
]

def main():
    """Shows basic usage of the Drive v3 API.
    Prints the names and ids of the first 10 files the user has access to.
    """
    creds = None

    # Set working directory to project root
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "oauth.json", SCOPES
            )
            creds = flow.run_local_server(port=8080, authorization_prompt_message='',
                                         success_message='Authentication complete. You may close this window.',
                                         open_browser=True,
                                         access_type='offline',
                                         prompt='consent')

        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    # Decode id_token and print user_id
    if creds and creds.id_token:
        try:
            payload = jwt.decode(creds.id_token, options={"verify_signature": False})
            user_id = payload.get("sub")
            print("🔵 User ID:", user_id)
        except Exception as e:
            print("Error decoding id_token:", e)
    else:
        print("No id_token found in credentials.")

    try:
        service = build("drive", "v3", credentials=creds)

        # Call the Drive v3 API
        results = (
            service.files()
            .list(pageSize=10, fields="nextPageToken, files(id, name)")
            .execute()
        )
        items = results.get("files", [])

        if not items:
            print("No files found.")
            return
        print("Files:")
        for item in items:
            print(f"{item['name']} ({item['id']})")
    except HttpError as error:
        print(f"An error occurred: {error}")

if __name__ == "__main__":
    main()
