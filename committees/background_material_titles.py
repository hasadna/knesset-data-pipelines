from datapackage_pipelines.wrapper import ingest, spew
from datapackage_pipelines.utilities.resources import PROP_STREAMING
import logging, requests
from time import sleep
from datapackage_pipelines_knesset.retry_get_response_content import get_retry_response_content
from pyquery import PyQuery as pq


URL_TEMPLATE = 'http://main.knesset.gov.il/Activity/committees/{slug}/Pages/CommitteeMaterial.aspx?ItemID={id}'

ROOT_COMMITTEE_URL_SLUGS = {
    934: 'Women'
}


def get_background_materials(slug, id):
    url = URL_TEMPLATE.format(slug=slug, id=id)
    try:
        content = get_retry_response_content(url, None, None, None, retry_num=1, num_retries=10,
                                             seconds_between_retries=10,
                                             skip_not_found_errors=True)
    except Exception:
        content = None
        logging.exception('failed to get background material titles for {} {}'.format(slug, id))
    if content:
        page = pq(content)
        for aelt in map(pq, page.find('a')):
            file_path = aelt.attr('href')
            if file_path and file_path.strip().startswith('http://fs.knesset.gov.il/'):
                title = aelt.text()
                row = {'FilePath': file_path, 'title': title}
                yield row


parameters, datapackage, resources, stats = ingest() + ({'new_background_material_titles': 0},)


resource_names = [descriptor['name'] for descriptor in datapackage['resources']]


for idx, name in enumerate(reversed(resource_names)):
    if name in ('kns_documentcommitteesession', 'kns_committeesession',
                'kns_committee', 'document_background_material_titles'):
        del datapackage['resources'][len(resource_names)-idx-1]
datapackage['resources'].append({PROP_STREAMING: True,
                                 'name': 'document_background_material_titles',
                                 'path': 'document_background_material_titles.csv',
                                 'schema': {'fields': [{'name': 'DocumentCommitteeSessionID',
                                                        'type': 'integer'},
                                                       {'name': 'CommitteeSessionID',
                                                        'type': 'integer'},
                                                       {'name': 'CommitteeID',
                                                        'type': 'integer'},
                                                       {'name': 'FilePath',
                                                        'type': 'string'},
                                                       {'name': 'title',
                                                        'type': 'string'}]}})


def get_resources():
    existing_background_material_titles = {}
    committees = {}
    sessions = {}

    def get_root_committee_id(committee_id):
        parent_committee_id = committees[committee_id].get('ParentCommitteeID')
        if parent_committee_id:
            return get_root_committee_id(parent_committee_id)
        else:
            return committee_id

    def get_titles(resource):
        scraped_session_ids = set()
        scraped_file_paths = set()
        for row in resource:
            existing_row = existing_background_material_titles.get(row['DocumentCommitteeSessionID'])
            if existing_row:
                yield existing_row
                continue
            committee_id = sessions.get(row['CommitteeSessionID'], {}).get('CommitteeID')
            root_committee_id = get_root_committee_id(committee_id) if committee_id else None
            if committee_id and root_committee_id:
                if row['GroupTypeID'] != 87:
                    continue
                if row['FilePath'] in scraped_file_paths:
                    continue
                if row['CommitteeSessionID'] in scraped_session_ids:
                    logging.warning('session id scraped but file path is not: {} {}'.format(row['CommitteeSessionID'],
                                                                                            row['FilePath']))
                    continue
                root_committee_url_slug = ROOT_COMMITTEE_URL_SLUGS.get(root_committee_id)
                if root_committee_url_slug:
                    # if stats['new_background_material_titles'] > 50:
                    #     continue
                    scraped_session_ids.add(row['CommitteeSessionID'])
                    for background_material in get_background_materials(root_committee_url_slug, row['CommitteeSessionID']):
                        file_path = background_material['FilePath']
                        if file_path in scraped_file_paths:
                            logging.warning('file_path already scraped: {}'.format(file_path))
                            continue
                        if file_path in existing_background_material_titles:
                            logging.warning('file_path in existing background material titles: {}'.format(file_path))
                            continue
                        stats['new_background_material_titles'] += 1
                        scraped_file_paths.add(file_path)
                        background_material.update(CommitteeID=committee_id,
                                                   CommitteeSessionID=row['CommitteeSessionID'],
                                                   DocumentCommitteeSessionID=row['DocumentCommitteeSessionID'])
                        yield background_material
                    sleep(0.01)


    for name, resource in zip(resource_names, resources):
        if name == 'kns_committee':
            for row in resource:
                committees[row['CommitteeID']] = row
        elif name == 'kns_committeesession':
            for row in resource:
                sessions[row['CommitteeSessionID']] = row
        if name == 'document_background_material_titles':
            for row in resource:
                existing_background_material_titles[row['DocumentCommitteeSessionID']] = row
        elif name == 'kns_documentcommitteesession':
            yield get_titles(resource)


spew(datapackage, get_resources(), stats)
