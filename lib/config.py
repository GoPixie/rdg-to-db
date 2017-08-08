import configparser
from getpass import getpass
from collections import OrderedDict
import logging

CRED = 'Login Credentials'


def read_config():
    config = configparser.SafeConfigParser()
    config.read('local.cfg')
    return config


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
            log.error("You need to have already stored login credentials to run quiet/automatically")
            import sys
            sys.exit(1)
        if 'username' not in r:
            r['username'] = input('%s username: ' % (site))
            if 'password' not in r:
                r['password'] = getpass('%s password: ' % (site))
        elif 'password' not in r:
            r['password'] = getpass('%s password (username %s): ' % (site, r['username']))
        y_or_no = input('Save these credentials in local.cfg? (y/n): ')
        if y_or_no.lower() == 'y':
            existing = read_config()
            existing[SITE_CRED] = OrderedDict([
                ('username', r['username']),
                ('password', r['password'])
            ])
            with open('local.cfg', 'w') as configfile:
                existing.write(configfile)
    return r
