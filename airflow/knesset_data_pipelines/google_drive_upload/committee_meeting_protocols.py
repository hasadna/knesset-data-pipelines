import os
from pprint import pprint
from collections import defaultdict
from contextlib import contextmanager

import requests
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from knesset_data_pipelines import config


def iterate_knesset_committee_sessions(knesset_num):
    # print(f'getting sessions for knesset_num {knesset_num}')
    for committee_session in requests.get(f'https://backend.oknesset.org/committee_sessions?knesset_num={knesset_num}').json()['data']:
        yield committee_session


def iterate_committee_sessions(stats, only_knesset_num=None):
    if only_knesset_num:
        for session in iterate_knesset_committee_sessions(only_knesset_num):
            stats['num_sessions'] += 1
            stats['num_knessets'] = 1
            yield session
    else:
        knesset_num = 0
        num_consecutive_no_session_knessets = 0
        while True:
            knesset_num += 1
            num_sessions = 0
            for session in iterate_knesset_committee_sessions(knesset_num):
                num_sessions += 1
                stats['num_sessions'] += 1
                if num_sessions == 1:
                    stats['num_knessets'] += 1
                yield session
            if num_sessions == 0:
                num_consecutive_no_session_knessets += 1
            else:
                num_consecutive_no_session_knessets = 0
            if num_consecutive_no_session_knessets >= 5:
                break


def stream_download(url, filepath):
    # print(f'downloading {url} to {filepath}')
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(filepath, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)


@contextmanager
def get_google_drive_service():
    with config.get_google_service_account_json_file_name() as service_account_json_file_name:
        SCOPES = ['https://www.googleapis.com/auth/drive']
        # 1. go to https://console.developers.google.com/apis/credentials
        # 2. create a new project
        # 3. create a new service account
        # 4. download the credentials json file
        # 5. share the target folder with the service account email address
        credentials = service_account.Credentials.from_service_account_file(service_account_json_file_name, scopes=SCOPES)
        yield build('drive', 'v3', credentials=credentials)


def get_or_create_google_drive_folder(service, name, parent_id):
    name = name.replace("'", "`")
    response = service.files().list(
        q=f"name='{name}' and '{parent_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false",
        fields='files(id, name)',
        driveId=config.GOOGLE_COMMITTEE_MEETING_PROTOCOLS_DRIVE_ID,
        includeItemsFromAllDrives=True,
        corpora='drive',
        supportsAllDrives=True,
    ).execute()
    files = response.get('files', [])
    if len(files) != 0:
        # print(f"Folder '{name}' already exists in Google Drive.")
        return files[0]['id']
    else:
        file_metadata = {
            'name': name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [parent_id],
        }
        folder = service.files().create(body=file_metadata, fields='id', supportsAllDrives=True).execute()
        return folder['id']


def upload_to_google_drive(filepath, target_folders, target_filename, service):
    try:
        # print(f"Uploading {filepath} to Google Drive folders {target_folders} with filename {target_filename}")
        parent_folder_id = config.GOOGLE_COMMITTEE_MEETING_PROTOCOLS_FOLDER_ID
        for target_folder in target_folders:
            parent_folder_id = get_or_create_google_drive_folder(service, target_folder, parent_folder_id)
        target_filename = target_filename.replace("'", "`").replace('\\', ' ')
        response = service.files().list(
            q=f"name='{target_filename}' and '{parent_folder_id}' in parents and trashed=false",
            fields='files(id, name)',
            driveId=config.GOOGLE_COMMITTEE_MEETING_PROTOCOLS_DRIVE_ID,
            includeItemsFromAllDrives=True,
            corpora='drive',
            supportsAllDrives=True,
        ).execute()
        files = response.get('files', [])
        if len(files) == 0:
            file_metadata = {
                'name': target_filename,
                'parents': [parent_folder_id],
            }
            media = MediaFileUpload(filepath, resumable=True)
            file = service.files().create(body=file_metadata, media_body=media, fields='id', supportsAllDrives=True).execute()
            print(f"Uploaded id {file.get('id')}")
        else:
            pass
            # print(f"File already exists in Google Drive: id {files[0]['id']}")
    except Exception:
        print(f"Failed to upload {filepath} to Google Drive folders {target_folders} with filename {target_filename}")
        raise


def main(download_from_url=False, knesset_num=None, limit=None, only_session_id=None):
    with get_google_drive_service() as service:
        stats = defaultdict(int)
        for session in iterate_committee_sessions(stats, only_knesset_num=knesset_num):
            if only_session_id and session['CommitteeSessionID'] != only_session_id:
                continue
            download_filename = session['download_filename']
            if download_filename:
                ext = download_filename.split('.')[-1]
                assert ext.lower() in ['doc', 'docx', 'pdf']
                stats['num_downloaded_sessions'] += 1
                filepath = os.path.join(config.KNESSET_PIPELINES_DATA_PATH, 'committees', 'download_document_committee_session', download_filename)
                if download_from_url and not os.path.exists(filepath):
                    url = f'https://production.oknesset.org/pipelines/data/committees/download_document_committee_session/{download_filename}'
                    stream_download(url, filepath)
                assert os.path.exists(filepath), f'file {filepath} does not exist'
                session_title = '-'
                if session.get('Note'):
                    session_title = session['Note']
                elif session.get('topics'):
                    session_title = ', '.join(session['topics'])
                if len(session_title) > 500:
                    session_title = session_title[:500] + '...'
                target_file_name = ' '.join([
                    'כנסת', str(session["KnessetNum"]),
                    session['committee_name'],
                    'ישיבה', str(session["Number"]),
                    session["StartDate"].split('T')[0],
                    session_title,
                    f'({session["CommitteeSessionID"]})',
                ]) + '.' + ext
                upload_to_google_drive(
                    filepath,
                    [],
                    target_file_name,
                    service
                )
                if limit and stats['num_downloaded_sessions'] >= limit:
                    break
    pprint(dict(stats))
