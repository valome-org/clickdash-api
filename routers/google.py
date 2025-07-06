from fastapi import APIRouter, HTTPException, Body, Request
from fastapi.responses import RedirectResponse
from googleapiclient.discovery import build
import google.oauth2.credentials
import json
import urllib.parse

router = APIRouter()

@router.post("/list-sheets")
async def list_google_sheets(credentials: dict = Body(...)):
    """
    List user's Google Sheets using OAuth2 credentials.
    Expects credentials dict from /google/callback.
    """
    try:
        creds = google.oauth2.credentials.Credentials(
            credentials["token"],
            refresh_token=credentials.get("refresh_token"),
            client_id=credentials["client_id"],
            client_secret=credentials["client_secret"],
            scopes=credentials["scopes"],
        )
        service = build("drive", "v3", credentials=creds)
        results = service.files().list(
            q="mimeType='application/vnd.google-apps.spreadsheet'",
            pageSize=10,
            fields="files(id, name)"
        ).execute()
        files = results.get("files", [])
        
        print(f"Found {len(files)} Google Sheets:")
        return {"sheets": files}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to list sheets: {str(e)}")
