import configparser
from getpass import getpass

CRED = 'RDG Login Credentials'

def read_config():
    config = configparser.SafeConfigParser()
    config.read('local.cfg')
    return config

def get_rdg_credentials(args):
    r = {'username': args.get('username', None)}
    config = read_config()
    if CRED in config:
        if not r['username'] and config[CRED].get('username', '').strip():
            r['username'] = config[CRED]['username']
        if config[CRED].get('password', '').strip():
            r['password'] = config[CRED]['password']
    if 'password' not in r:
        r['password'] = getpass('atoc password:')
    return r
