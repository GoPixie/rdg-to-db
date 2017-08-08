
import csv as csv_module
import logging
import json
import os

from lib.util import json_comment_filter
from lib.fixed_fields import iterate_fixed_fields
from targets.unzip import unzip


def csv(file_prefixes=None):
    log = logging.getLogger('targets_csv')
    csv_dir = os.path.join(os.getcwd(), 'feeds', 'csv')
    if not os.path.exists(csv_dir):
        os.makedirs(csv_dir)
    file_fields = json_comment_filter(json.load(open('file-fields.json', 'r')))
    if not file_prefixes:
        file_prefixes = file_fields.keys()
    for fprefix in sorted(file_prefixes):
        extracted_dir = os.path.join(os.getcwd(), 'feeds', fprefix)
        if not os.path.isdir(extracted_dir):
            zipfile_path = os.path.join(os.getcwd(), 'feeds', fprefix + '-FULL-LATEST.ZIP')
            if not os.path.exists(zipfile_path):
                log.error('%s: No downloaded ZIP file found' % (fprefix))
                continue
            unzip([fprefix])
        existing = os.listdir(extracted_dir)
        for filename in sorted(existing):
            if filename in ['DAT', '.version']:
                continue
            if filename not in file_fields[fprefix]:
                log.warning('%s: Missing spec for %s' % (fprefix, filename))
                continue
            log.debug('%s: Found spec for %s' % (fprefix, filename))
            csv_files = {}
            csv_writers = {}
            try:
                fields = file_fields[fprefix][filename]
                for record in iterate_fixed_fields(os.path.join(extracted_dir, filename), fields):
                    k = record.get('RECORD_TYPE', '')
                    if k not in csv_writers:
                        fsuffix = ''
                        if k != '':
                            fsuffix = '-' + k
                        csv_path = os.path.join(os.getcwd(), 'feeds', 'csv',
                                                fprefix + '-' + filename + fsuffix + '.csv')
                        csv_files[k] = open(csv_path, 'w')
                        csv_writers[k] = csv_module.DictWriter(
                            csv_files[k],
                            fieldnames=[f[0] for f in fields[k]])
                        csv_writers[k].writeheader()
                    if k:
                        del record['RECORD_TYPE']  # contained in filename
                    csv_writers[k].writerow(record)
            finally:
                for f in csv_files.values():
                    f.close()
