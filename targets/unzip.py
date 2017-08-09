import os
import json
import logging
import shutil
from zipfile import ZipFile
from collections import defaultdict
from multiprocessing import Pool
from time import time as t_time

from lib.util import json_comment_filter


def unzip(file_prefixes=None):
    log = logging.getLogger('targets_unzip')
    stime = t_time()
    if not file_prefixes:
        file_fields = json_comment_filter(json.load(open('file-fields.json', 'r')))
        file_prefixes = file_fields.keys()
    todo = []
    for ftname in file_prefixes:
        if ftname.lower().endswith('.zip'):
            zipfilename = ftname
            ftname = ftname[:-4]
        else:
            zipfilename = ftname + '-FULL-LATEST.ZIP'
        zpath = os.path.join(os.getcwd(), 'feeds', zipfilename)
        if False:
            # don't multiprocess
            unzip_single(zpath, ftname)
        else:
            todo.append((zpath, ftname))
    if todo:
        with Pool() as pool:
            for _ in pool.imap_unordered(unzip_single_tup, todo):
                pass
    log.debug('unzip: %d total time' % (t_time()-stime))


def unzip_single_tup(tup):
    # required as we don't have pool.starmap_unordered
    return unzip_single(*tup)


def unzip_single(zpath, ftname):
    log = logging.getLogger('targets_unzip')
    zz = ZipFile(open(zpath, 'rb'))
    feed_path = os.path.join(os.getcwd(), 'feeds', ftname)
    if not os.path.exists(feed_path):
        os.makedirs(feed_path)
    versions = defaultdict(int)
    extract_count = 0
    for member in zz.infolist():
        out_name = member.filename
        if out_name.startswith(ftname):
            out_name = out_name[len(ftname):]
            if out_name[0] == 'F':
                out_name = out_name[1:]
            if out_name[0] == 'C':
                log.error("Unexpected 'Changes' file in archive: %s" % (out_name))
                continue
            if '.' in out_name and out_name.split('.')[0].isnumeric():
                version = out_name.split('.')[0]
                versions[version] += 1
                out_name = out_name.split('.', 1)[1]
        zz.extract(member, feed_path)
        if out_name != member.filename:
            shutil.move(
                os.path.join(feed_path, member.filename),
                os.path.join(feed_path, out_name))
        extract_count += 1
    version_file = os.path.join(feed_path, '.version')
    if not versions:
        log.warning('No versioning found')
        if os.path.exists(version_file):
            os.path.remove(version_file)
    else:
        most_common_version = max(versions.items(), key=lambda kv: kv[1])[0]
        highest_version = max(versions.items())[0]
        if most_common_version != highest_version:
            log.warning('%s: Most common version (%d) is not highest (%d)'
                        % (ftname, most_common_version, highest_version))
        elif len(versions) > 1:
            log.warning('%s: Multiple versions in single ZIP: %s'
                        % (', '.join(map(int, sorted(versions)))))
        with open(version_file, 'w') as vf:
            vf.write(highest_version + '\n')
    log.info('%s Extracted %d files to %s' % (ftname, extract_count, feed_path))
