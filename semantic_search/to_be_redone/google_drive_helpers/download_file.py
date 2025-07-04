from io import BytesIO

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload


def download_file(file_id: str, user_token: dict) -> tuple[BytesIO, str]:
	"""
	Downloads a file from Google Drive.
	Args:
		file_id: ID of the file to download
		user_token: User token for authentication
	Returns:
		IO object with location, file name.
	"""

	# Load credentials
	creds = Credentials.from_authorized_user_info(user_token)

	# create drive api client
	service = build("drive", "v3", credentials=creds)

	# pylint: disable=maybe-no-member
	request = service.files().get_media(fileId=file_id)
	file = BytesIO()
	downloader = MediaIoBaseDownload(file, request)
	done = False
	while done is False:
		status, done = downloader.next_chunk()

	metadata = service.files().get(
		fileId=file_id,
		fields="name"
	).execute()

	file_name = metadata.get("name")

	return file.getvalue(), file_name
	