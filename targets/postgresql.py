from sqlalchemy import MetaData, create_engine
from sqlalchemy.engine.reflection import Inspector
from sqlalchemy.exc import OperationalError
import logging
import json
import os
from time import time as t_time
from multiprocessing import Pool

from lib.util import json_comment_filter
from targets.csv import csv
from lib.config import get_dburi, get_remote_csv_dir, get_csv_dir, get_latest_version
from .db import table_from_fields, drop_create_table

def postgresql(file_prefixes=None):
    """
    Move CSV files into corresponding postgresql tables
    using bulk postgresql COPY command.
    Table names and columns are lowercased
    for ease of working in SQL.
    Types conversion:
        Date: Applicable columns ending in '_DATE'
        Time: Applicable columns ending in '_TIME'
    The CSV files must be on the same server as the postgres
    db and readable by the postgres process.
    Composite primary keys have blanks (rather than null) in columns.
    """
    log = logging.getLogger('targets_postgresql')
    stime = t_time()
    dburi = get_dburi()
    engine = create_engine(dburi)
    engine.connect()  # trigger conn. related exceptions, e.g. if db doesn't exist
    metadata = MetaData()

    file_fields = json_comment_filter(json.load(open('file-fields.json', 'r')))
    field_pks = json_comment_filter(json.load(open('field-pks.json', 'r')))
    if not file_prefixes:
        file_prefixes = file_fields.keys()
    todo = []
    for fprefix in sorted(file_prefixes):
        csv_dir = get_remote_csv_dir()
        if not os.path.exists(csv_dir) and csv_dir != get_csv_dir():
            # We don't have access to the directory we'll be COPYing from
            # versions are included in CSV filenames so db server will fail
            # to COPY from an old file
            pass
        else:
            if not os.path.exists(csv_dir):
                csv([fprefix])
            else:
                with open(os.path.join(csv_dir, '.version.' + fprefix), 'r') as f:
                    csv_version = f.read().strip()
                if csv_version != get_latest_version(fprefix).lstrip('F'):
                    log.warning('%s: Newer version available, converting to CSV again' % (fprefix))
                    csv([fprefix])

        for filename in file_fields[fprefix]:
            for record_type, fields in file_fields[fprefix][filename].items():
                pks = field_pks.get(fprefix, {}).get(filename, {}).get(record_type, [])
                if not fields:
                    log.warning('%s: Missing spec for %s %s' % (fprefix, filename, record_type))
                    continue
                if False:
                    table_name, creating = csv_to_table(engine, metadata, fprefix,
                                                        filename, record_type, fields, pks)
                    if table_name and creating:
                        log.info('Finished recreating %s' % (table_name))
                    elif table_name:
                        log.info('Finished creating %s' % (table_name))
                else:
                    todo.append((fprefix, filename, record_type, fields, pks))
    if todo:
        n = 1
        with Pool() as pool:
            for table_name, creating in pool.imap_unordered(csv_to_table_tup, todo):
                if table_name and creating:
                    log.info('Finished recreating %s (%d of %d)' % (table_name, n, len(todo)))
                elif table_name:
                    log.info('Finished creating %s (%d of %d)' % (table_name, n, len(todo)))
                n += 1
    log.debug('csv to postgresql: %ds total time' % (t_time()-stime))


def csv_to_table_tup(tup):
    # required as we don't have pool.starmap_unordered
    dburi = get_dburi()
    engine = create_engine(dburi)  # each process needs it's own engine
    metadata = MetaData()
    tup_with_cx = (engine, metadata) + tup
    return csv_to_table(*tup_with_cx)


def csv_to_table(
        engine, metadata,
        fprefix, filename, record_type, fields, pks=[],
        csv_path=None):
    """
    WARNING: this drops and recreates tables
    table schema is as specified in file-fields.json and field-pks.json
    """
    log = logging.getLogger('targets_postgresql_csv_to_table')

    version = get_latest_version(fprefix)
    if csv_path is None:
        if record_type:
            csv_name = '%s-%s-%s.%s.csv' % (fprefix, filename, record_type, version)
        else:
            csv_name = '%s-%s.%s.csv' % (fprefix, filename, version)
        csv_path = os.path.join(get_remote_csv_dir(), csv_name)

    table = table_from_fields(engine, metadata, fprefix, filename,
                         record_type, fields, pks)

    inspector = Inspector.from_engine(engine)
    creating = table.name in inspector.get_table_names()

    connection = engine.connect()
    trans = connection.begin()
    try:

        drop_create_table(connection, table)

        # data insert using COPY method
        force_not_null = ''
        if pks and pks != ['invalid']:
            force_not_null = ', FORCE_NOT_NULL ("%s")' % ('", "'.join([p.lower() for p in pks]))
        connection.execute("""COPY "%s"
FROM '%s'
WITH (FORMAT CSV, HEADER%s);
        """ % (table.name, csv_path, force_not_null))

        trans.commit()
    except OperationalError as oe:
        trans.rollback()
        if 'No such file or directory' in str(oe):
            if creating:
                log.warning('%s not found, no table created' % (csv_path))
            else:
                log.warning('%s not found, table kept as-is' % (csv_path))
            table.name = None
        else:
            raise

    return table.name, creating
