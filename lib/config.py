import configparser
from getpass import getpass
from collections import OrderedDict
import logging
import os

CRED = 'Login Credentials'


def read_config():
    config = configparser.SafeConfigParser()
    config.read('accounts.cfg')
    return config


def get_download_dir():
    log = logging.getLogger('get_download_dir')
    config = configparser.SafeConfigParser()
    config.read('local.cfg')
    if 'Download' in config:
        download_dir = config['Download']['download_directory']
    else:
        download_dir = os.path.join(os.getcwd(), 'feeds')
    if not os.path.exists(download_dir):
        log.info('Creating %s download directory for first time' % (download_dir))
        os.makedirs(download_dir)
    return download_dir


def get_unzip_dir():
    log = logging.getLogger('get_unzip_dir')
    config = configparser.SafeConfigParser()
    config.read('local.cfg')
    if 'Unzip' in config:
        unzip_dir = config['Unzip']['unzip_directory']
    else:
        unzip_dir = os.path.join(os.getcwd(), 'feeds')
    if not os.path.exists(unzip_dir):
        log.info('Creating %s unzip directory for first time' % (unzip_dir))
        os.makedirs(unzip_dir)
    return unzip_dir


def get_csv_dir():
    log = logging.getLogger('get_csv_dir')
    config = configparser.SafeConfigParser()
    config.read('local.cfg')
    if 'CSV' in config:
        csv_dir = config['CSV']['csv_directory']
    else:
        csv_dir = os.path.join(os.getcwd(), 'feeds', 'csv')
    if not os.path.exists(csv_dir):
        log.info('Creating %s csv directory for first time' % (csv_dir))
        os.makedirs(csv_dir)
    return csv_dir


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
