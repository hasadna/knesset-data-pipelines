from datapackage_pipelines.wrapper import ingest, spew
from collections import defaultdict
import logging
from datapackage_pipelines_knesset import common_flow
from glob import glob
import os


def get_sitemap_links(path):
    for filename in glob(path + '/*'):
        if filename.endswith('.html'):
            stats['num-files'] += 1
            yield filename.replace(knesset_data_path, 'https://oknesset.org')
        elif os.path.isdir(filename) and not filename.endswith('/static'):
            stats['num-directories'] += 1
            yield from get_sitemap_links(filename)


def add_to_sitemap(path, sitemap_root_filename, num_links_per_file):
    logging.info('num_links_per_file={}'.format(num_links_per_file))
    sitemap_filenum = 1
    sitemap_file = open(sitemap_root_filename+'.txt', 'w')
    sitemap_file_num_links = 0
    stats['num-sitemap-txt-files'] += 1
    for sitemap_link in get_sitemap_links(path):
        stats['num-sitemap-links'] += 1
        sitemap_file.write(sitemap_link + "\n")
        sitemap_file_num_links += 1
        if sitemap_file_num_links == int(num_links_per_file):
            stats['num-sitemap-txt-files'] += 1
            sitemap_file.close()
            sitemap_filenum += 1
            sitemap_file = open(sitemap_root_filename + str(sitemap_filenum) + '.txt', 'w')
            sitemap_file_num_links = 0
    sitemap_file.close()


parameters, datapackage, resources = ingest()


stats = defaultdict(int)
knesset_data_path = common_flow.get_knesset_data_url_or_path('committees/dist/dist', use_data=True)
add_to_sitemap(knesset_data_path, knesset_data_path + '/sitemap', parameters['num-links-per-file'])


spew(dict(datapackage, resources=[]), [], stats)
