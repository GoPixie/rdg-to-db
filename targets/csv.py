
import csv as csv_module
import logging
import json
import os
import shutil
from multiprocessing import Pool
from time import time as t_time

from lib.util import json_comment_filter
from lib.fields import iterate_fields
from targets.unzip import unzip
from lib.config import get_download_dir, get_unzip_dir, get_csv_dir, get_latest_version


def csv(file_prefixes=None):
    """
    Transform each file in downloaded ZIP to csv format under a /csv/
    directory specified in local.cfg.
    Files with multiple record types are output to multiple csv files
    e.g. /RJFAF123.TOC becomes
        /csv/RJFA-TOC-T.CSV (main train operating company ids and names)
        /csv/RJFA-TOC-F.CSV (additional toc fare ids)
    """
    log = logging.getLogger('targets_csv')
    stime = t_time()
    file_fields = json_comment_filter(json.load(open('file-fields.json', 'r')))
    if not file_prefixes:
        file_prefixes = file_fields.keys()

    versions = {}
    done = []
    todo = []
    for fprefix in sorted(file_prefixes):
        unzip_dir = os.path.join(get_unzip_dir(), fprefix)
        version = get_latest_version(fprefix).lstrip('F')
        versions[fprefix] = version
        if not os.path.isdir(unzip_dir):
            unzip([fprefix])
        else:
            with open(os.path.join(unzip_dir, '.version.' + fprefix), 'r') as f:
                unzip_version = f.read().strip()
            if unzip_version != version:
                log.warning('%s: Newer ZIP file available, unzipping again' % (fprefix))
                unzip([fprefix])
        existing = os.listdir(unzip_dir)
        for filename in sorted(existing):
            if filename in ['DAT'] or filename.startswith('.version'):
                continue
            if filename not in file_fields[fprefix]:
                log.warning('%s: Missing spec for %s' % (fprefix, filename))
                continue
            log.debug('%s: Found spec for %s' % (fprefix, filename))
            file_path = os.path.join(unzip_dir, filename)
            if False:
                # don't multiprocess
                _, _, csv_files = file_to_csv(fprefix, filename, file_path, file_fields)
                done.extend(csv_files)
                if csv_files:
                    log.info('Finished processing %s/%s %s csv file(s)' % (
                        fprefix, filename, len(csv_files)))
            else:
                todo.append((fprefix, filename, file_path, file_fields))
    if todo:
        n = 1
        with Pool() as pool:
            for fprefix, filename, csv_files in pool.imap_unordered(file_to_csv_tup, todo):
                csv_msg = ''
                if len(csv_files) > 1:
                    csv_msg = '- %d csv files' % (len(csv_files))
                if len(csv_files) > 0:
                    log.info('Finished processing %s/%s (%d of %d) %s' % (
                        fprefix, filename, n, len(todo), csv_msg))
                n += 1
                done.extend(csv_files)

    # remove old versions of files
    csv_dir = get_csv_dir()
    for fname in os.listdir(csv_dir):
        if fname.endswith('.csv') and fname not in done and fname.split('-')[0] in file_prefixes:
            os.unlink(os.path.join(csv_dir, fname))

    for fprefix in file_prefixes:
        version_file = os.path.join(csv_dir, '.version.' + fprefix)
        with open(version_file, 'w') as vf:
            vf.write(versions[fprefix] + '\n')

    log.debug('csv: %ds total time' % (t_time()-stime))


def file_to_csv_tup(tup):
    # required as we don't have pool.starmap_unordered
    return file_to_csv(*tup)


def file_to_csv(fprefix, filename, file_path=None, file_fields=None):
    """
    A file can have multiple record types. Output separate
    CSV files for each one
    """
    version = get_latest_version(fprefix).lstrip('F')
    if file_path is None:
        file_path = os.path.join(get_download_dir(), fprefix, filename)
    if file_fields is None:
        file_fields = json_comment_filter(json.load(open('file-fields.json', 'r')))
    csv_files = {}
    csv_writers = {}
    try:
        fields = file_fields[fprefix][filename]
        for record in iterate_fields(file_path, fields):
            k = record.get('RECORD_TYPE', '')
            if k not in csv_writers:
                fsuffix = ''
                if k != '':
                    fsuffix = '-' + k
                csv_filename = fprefix + '-' + filename + fsuffix + '.' + version + '.csv'
                csv_path = os.path.join(get_csv_dir(), csv_filename)
                csv_files[csv_filename] = open(csv_path, 'w')
                fieldnames = [f[0] if not isinstance(f, str) else f for f in fields[k]]
                fieldnames = [f for f in fieldnames if f not in ['RECORD_TYPE', 'UPDATE_MARKER']]
                csv_writers[k] = csv_module.DictWriter(csv_files[csv_filename], fieldnames=fieldnames)
                csv_writers[k].writeheader()
            if k:
                del record['RECORD_TYPE']  # contained in filename
            csv_writers[k].writerow(record)
    finally:
        for f in csv_files.values():
            f.close()
    return fprefix, filename, list(csv_files.keys())
