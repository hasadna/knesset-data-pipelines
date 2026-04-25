"""Fix broken committee broadcast URLs.

The Knesset OData API returns broadcast URLs pointing to the old SharePoint site:
  http://main.knesset.gov.il/Activity/committees/Pages/AllCommitteesBroadcast.aspx?TopicID=XXXXX

This site was rebuilt — these URLs no longer work.

The correct video URLs were fetched from the Knesset's WebSiteApi
(GetCommitteePortalsBroadcast) and stored in broadcast_urls.json.
This processor looks up the correct URL by CommitteeSessionID.

To regenerate the mapping: python committees/fetch_broadcast_urls.py

See: https://github.com/hasadna/knesset-data-pipelines/issues/241
"""
import json
import os
import re

from datapackage_pipelines.wrapper import process

BROKEN_PATTERN = re.compile(
    r'https?://main\.knesset\.gov\.il/Activity/committees/Pages/AllCommitteesBroadcast\.aspx\?TopicID=\d+'
)

_url_mapping = None


def _get_url_mapping():
    global _url_mapping
    if _url_mapping is None:
        mapping_path = os.path.join(os.path.dirname(__file__), 'broadcast_urls.json')
        if os.path.exists(mapping_path):
            with open(mapping_path, encoding='utf-8') as f:
                _url_mapping = json.load(f)
        else:
            _url_mapping = {}
    return _url_mapping


def process_row(row, row_index, spec, resource_index, parameters, stats):
    if spec['name'] == 'kns_committeesession':
        broadcast_url = row.get('BroadcastUrl')
        session_id = row.get('CommitteeSessionID')
        if broadcast_url and session_id and BROKEN_PATTERN.match(broadcast_url):
            mapping = _get_url_mapping()
            new_url = mapping.get(str(session_id))
            if new_url:
                row['BroadcastUrl'] = new_url
                stats.setdefault('fixed_broadcast_urls', 0)
                stats['fixed_broadcast_urls'] += 1
            else:
                stats.setdefault('unfixed_broadcast_urls', 0)
                stats['unfixed_broadcast_urls'] += 1
    return row


if __name__ == '__main__':
    process(process_row=process_row)
