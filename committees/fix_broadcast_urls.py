"""Fix broken committee broadcast URLs.

The Knesset OData API returns broadcast URLs pointing to the old SharePoint site:
  http://main.knesset.gov.il/Activity/committees/Pages/AllCommitteesBroadcast.aspx?TopicID=XXXXX

This site was rebuilt — these URLs no longer work.

The actual video streams are available at:
  https://video.knesset.gov.il/KnsVod/_definst_/mp4:archive/CMT/CmtSession_{CommitteeSessionID}.mp4/playlist.m3u8

This processor replaces the broken URLs with direct HLS video stream links
using the CommitteeSessionID which is already in the data.

See: https://github.com/hasadna/knesset-data-pipelines/issues/241
"""
import re

from datapackage_pipelines.wrapper import process

BROKEN_PATTERN = re.compile(
    r'https?://main\.knesset\.gov\.il/Activity/committees/Pages/AllCommitteesBroadcast\.aspx\?TopicID=\d+'
)
VIDEO_TEMPLATE = (
    'https://video.knesset.gov.il/KnsVod/_definst_/mp4:archive/CMT/CmtSession_{session_id}.mp4/playlist.m3u8'
)


def process_row(row, row_index, spec, resource_index, parameters, stats):
    if spec['name'] == 'kns_committeesession':
        broadcast_url = row.get('BroadcastUrl')
        session_id = row.get('CommitteeSessionID')
        if broadcast_url and session_id and BROKEN_PATTERN.match(broadcast_url):
            row['BroadcastUrl'] = VIDEO_TEMPLATE.format(session_id=session_id)
            stats.setdefault('fixed_broadcast_urls', 0)
            stats['fixed_broadcast_urls'] += 1
    return row


if __name__ == '__main__':
    process(process_row=process_row)
