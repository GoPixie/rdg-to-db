import configparser
from getpass import getpass
from collections import OrderedDict
import logging
import os
import re

CRED = 'Login Credentials'
VERSIONING_RE = '([^0-9]+)([0-9][0-9][0-9]+)([^0-9]+)'


def read_config():
    config = configparser.SafeConfigParser()
    config.read('accounts.cfg')
    return config


def _multiprocess_makedirs(dir_path, log, dir_type):
    if not os.path.exists(dir_path):
        try:
            os.makedirs(dir_path)
        except IOError:
            if os.path.exists(dir_path):
                pass  # might have just been created by another process
            else:
                raise
        else:
            log.info('Creating %s %s directory for first time' % (dir_path, dir_type))


def get_dir(dir_type_name):
    dir_type = dir_type_name.lower()
    log = logging.getLogger('get_%s_dir' % (dir_type))
    config = configparser.SafeConfigParser()
    config.read('local.cfg')
    if dir_type_name in config:
        dir_path = config[dir_type_name]['%s_directory' % (dir_type)]
    elif dir_type == 'download':
        dir_path = os.path.join(os.getcwd(), 'feeds')
    else:
        dir_path = os.path.join(get_download_dir(), dir_type)
    _multiprocess_makedirs(dir_path, log, dir_type)
    return dir_path


def get_download_dir():
    return get_dir('Download')


def get_unzip_dir():
    return get_dir('Unzip')


def get_csv_dir():
    return get_dir('CSV')


def keep_old_downloads():
    config = configparser.SafeConfigParser()
    config.read('local.cfg')
    if 'Download' in config:
        return config['Download'].getboolean('keep_old', False)
    else:
        return False


def get_latest_version(file_prefix):
    log = logging.getLogger('get_latest_version')
    download_dir = get_download_dir()
    versions_file = os.path.join(download_dir, '.versions')
    version = False
    if os.path.exists(versions_file):
        with open(versions_file, 'r') as vf:
            for line in vf.readlines():
                vff, v, rest = line.split(' ', 2)
                if vff == file_prefix:
                    version = v
                elif file_prefix + 'F' == vff:  # Full file
                    version = 'F' + v
                # don't break; keep reading more lines to get the latest one
    else:
        possible_versions = []
        for fname in os.listdir(download_dir):
            fv = re.search(VERSIONING_RE, fname)
            if fv:
                fv_file_sig = fv.groups()[0]
                if fv_file_sig == file_prefix:
                    possible_versions.append((int(fv.groups()[1]), fv.groups()[1]))
                elif fv_file_sig == file_prefix + 'F':
                    possible_versions.append((int(fv.groups()[1]), 'F'+fv.groups()[1]))
        if possible_versions:
            version = max(possible_versions)[1]  # the bit including the 'F'
            log.warning("Can't find .versions file; were files downloaded using"
                        " the ./download script?"
                        " Falling back to highest number found: %s%s" % (file_prefix, version))
    return version


def get_remote_csv_dir():
    """
    If csv files have been uploaded to a remote server
    with postgresql
    """
    config = configparser.SafeConfigParser()
    config.read('local.cfg')
    if 'CSV' in config:
        if 'remote_csv_directory' in config['CSV']:
            csv_dir = config['CSV']['remote_csv_directory']
        else:
            csv_dir = config['CSV']['csv_directory']
    else:
        csv_dir = os.path.join(os.getcwd(), 'feeds', 'csv')
    return csv_dir


def get_dburi():
    log = logging.getLogger('get_dburi')
    config = configparser.SafeConfigParser()
    config.read('local.cfg')
    if 'Database' in config and 'dburi' in config['Database']:
        dburi = config['Database']['dburi']
    else:
        log.info('No database connection string found in local.cfg')
        dburi = input('DB Connection String (default postgresql://postgres@localhost:5432/rdg): ')
        if not dburi.strip():
            dburi = 'postgresql://postgres@localhost:5432/rdg'
    return dburi


def get_rdg_credentials(args, site):
    log = logging.getLogger('download')
    r = {}
    if args.get('username', None):
        r['username'] = args['username']
    config = read_config()
    SITE_CRED = site + ' ' + CRED
    if SITE_CRED in config:
        if 'username' not in r and config[SITE_CRED].get('username', '').strip():
            r['username'] = config[SITE_CRED]['username']
        if config[SITE_CRED].get('password', '').strip():
            r['password'] = config[SITE_CRED]['password']
    if 'username' not in r or 'password' not in r:
        if args['quiet']:
            log.error(
                "You need to have already stored login "
                "credentials to run quiet/automatically"
            )
            import sys
            sys.exit(1)
        if 'username' not in r:
            r['username'] = input('%s username: ' % (site))
            if 'password' not in r:
                r['password'] = getpass('%s password: ' % (site))
        elif 'password' not in r:
            r['password'] = getpass('%s password (username %s): ' % (site, r['username']))
        y_or_no = input('Save these credentials in accounts.cfg? (y/n): ')
        if y_or_no.lower() == 'y':
            existing = read_config()
            existing[SITE_CRED] = OrderedDict([
                ('username', r['username']),
                ('password', r['password'])
            ])
            with open('accounts.cfg', 'w') as configfile:
                existing.write(configfile)
    return r
