"""Fetch correct broadcast video URLs from the Knesset WebSiteApi.

The Knesset OData API returns broken broadcast URLs (AllCommitteesBroadcast.aspx).
The Knesset's new WebSiteApi has the correct video stream URLs for all sessions.

This script fetches all broadcast URLs day-by-day (API returns max 10 per request)
and saves them as a JSON mapping file:
  { CommitteeSessionID: "https://video.knesset.gov.il/..." }

Usage:
  python committees/fetch_broadcast_urls.py

Output:
  committees/broadcast_urls.json

See: https://github.com/hasadna/knesset-data-pipelines/issues/241
"""
import json
import sys
import time
from datetime import datetime, timedelta

import requests

API_URL = 'https://www.knesset.gov.il/WebSiteApi/knessetapi/CommitteeBroadcasts/GetCommitteePortalsBroadcast'

KNESSET_DATES = {
    18: ('2009-02-24', '2013-02-05'),
    19: ('2013-02-05', '2015-03-31'),
    20: ('2015-03-31', '2019-04-30'),
    21: ('2019-04-30', '2019-10-03'),
    22: ('2019-10-03', '2020-03-16'),
    23: ('2020-03-16', '2021-06-13'),
    24: ('2021-06-13', '2022-11-15'),
    25: ('2022-11-15', '2026-12-31'),
}


def fetch_day(knesset_num, date_str):
    """Fetch broadcasts for a single day. API returns max 10 per request."""
    resp = requests.post(API_URL, json={
        'CommitteeId': None,
        'FromDate': f'{date_str}T00:00:00',
        'ToDate': f'{date_str}T23:59:59',
        'KnessetIDs': str(knesset_num),
        'Language': 'he',
        'Subject': '',
    }, timeout=60)
    data = resp.json()
    if not data or not isinstance(data, list):
        return []
    return data


def main():
    url_mapping = {}
    total = 0

    for knesset_num, (from_str, to_str) in sorted(KNESSET_DATES.items()):
        start = datetime.strptime(from_str, '%Y-%m-%d')
        end = datetime.strptime(to_str, '%Y-%m-%d')
        days = (end - start).days
        count = 0

        print(f'Knesset {knesset_num}: {days} days to scan ({from_str} to {to_str})')

        current = start
        while current <= end:
            date_str = current.strftime('%Y-%m-%d')
            try:
                broadcasts = fetch_day(knesset_num, date_str)
                for b in broadcasts:
                    session_id = b.get('FKItemID')
                    video_url = b.get('StreamPublishedUrl')
                    if session_id and video_url:
                        url_mapping[str(session_id)] = video_url
                        count += 1
            except Exception as e:
                print(f'  Error on {date_str}: {e}')

            current += timedelta(days=1)

            if count > 0 and count % 100 == 0:
                print(f'  {date_str}: {count} URLs so far...')

            time.sleep(0.1)

        total += count
        print(f'  Done: {count} video URLs')

    output_path = 'committees/broadcast_urls.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(url_mapping, f, indent=2, ensure_ascii=False)

    print(f'\nTotal: {total} video URLs saved to {output_path}')


if __name__ == '__main__':
    main()
