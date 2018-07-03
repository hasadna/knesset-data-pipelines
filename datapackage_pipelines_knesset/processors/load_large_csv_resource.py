from datapackage_pipelines.lib.load_resource import ResourceLoader

import csv, sys
csv.field_size_limit(sys.maxsize)

if __name__ == '__main__':
    ResourceLoader()()
