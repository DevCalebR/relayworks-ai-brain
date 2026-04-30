import json
import os
from pathlib import Path

from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from tools.upload_check import validate_upload_package


SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
DEFAULT_CLIENT_SECRETS_FILE = "client_secret.json"
DEFAULT_TOKEN_FILE = "youtube_token.json"
DEFAULT_PRIVACY_STATUS = "private"
VALID_PRIVACY_STATUSES = {"private", "unlisted", "public"}


load_dotenv()


def _get_env_path(name, default):
    return Path(os.getenv(name, default)).expanduser()


def _get_privacy_status(privacy_status):
    selected_status = privacy_status or os.getenv(
        "YOUTUBE_PRIVACY_STATUS", DEFAULT_PRIVACY_STATUS
    )
    selected_status = selected_status.strip().lower()

    if selected_status not in VALID_PRIVACY_STATUSES:
        valid_values = ", ".join(sorted(VALID_PRIVACY_STATUSES))
        raise ValueError(
            f"Invalid privacy status: {selected_status}. Expected one of: {valid_values}"
        )

    return selected_status


def _load_metadata(metadata_path):
    return json.loads(metadata_path.read_text(encoding="utf-8"))


def _format_hashtag(hashtag):
    value = str(hashtag).strip()

    if not value:
        return ""

    return value if value.startswith("#") else f"#{value}"


def _description_with_hashtags(description, hashtags):
    description = str(description).strip()
    formatted_hashtags = [
        formatted
        for formatted in (_format_hashtag(hashtag) for hashtag in hashtags or [])
        if formatted
    ]
    missing_hashtags = [
        hashtag for hashtag in formatted_hashtags if hashtag not in description
    ]

    if not missing_hashtags:
        return description

    return f"{description}\n\n{' '.join(missing_hashtags)}"


def _load_credentials(client_secrets_path, token_path):
    credentials = None

    if token_path.exists():
        credentials = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if credentials and credentials.valid:
        return credentials

    if credentials and credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
    else:
        if not client_secrets_path.exists():
            raise FileNotFoundError(
                "YouTube OAuth client secrets file does not exist: "
                f"{client_secrets_path}"
            )

        flow = InstalledAppFlow.from_client_secrets_file(
            str(client_secrets_path), SCOPES
        )
        credentials = flow.run_local_server(port=0)

    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(credentials.to_json(), encoding="utf-8")

    return credentials


def _build_youtube_client():
    client_secrets_path = _get_env_path(
        "YOUTUBE_CLIENT_SECRETS_FILE", DEFAULT_CLIENT_SECRETS_FILE
    )
    token_path = _get_env_path("YOUTUBE_TOKEN_FILE", DEFAULT_TOKEN_FILE)
    credentials = _load_credentials(client_secrets_path, token_path)

    return build("youtube", "v3", credentials=credentials)


def upload_video_from_run_folder(run_folder, privacy_status="private"):
    """
    Upload video.mp4 from an organized run folder using metadata.json.

    The run folder is validated before any OAuth flow or upload request starts.
    """
    validation_result = validate_upload_package(run_folder)

    if not validation_result["ready"]:
        errors = "; ".join(validation_result["errors"])
        raise ValueError(f"Run folder is not upload-ready: {errors}")

    run_path = Path(run_folder)
    video_path = run_path / "video.mp4"
    metadata_path = run_path / "metadata.json"
    metadata = _load_metadata(metadata_path)
    selected_privacy_status = _get_privacy_status(privacy_status)

    title = str(metadata["title"]).strip()
    description = _description_with_hashtags(
        metadata["description"], metadata.get("hashtags", [])
    )
    tags = [str(tag).strip() for tag in metadata.get("tags", []) if str(tag).strip()]

    request_body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": "28",
        },
        "status": {
            "privacyStatus": selected_privacy_status,
        },
    }

    media = MediaFileUpload(str(video_path), chunksize=-1, resumable=True)
    youtube = _build_youtube_client()
    request = youtube.videos().insert(
        part="snippet,status",
        body=request_body,
        media_body=media,
    )
    response = None

    while response is None:
        _, response = request.next_chunk()

    video_id = response["id"]

    return {
        "video_id": video_id,
        "video_url": f"https://www.youtube.com/watch?v={video_id}",
        "title": title,
        "privacy_status": selected_privacy_status,
        "run_folder": str(run_path),
    }
