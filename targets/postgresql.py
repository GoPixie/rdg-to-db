from sqlalchemy import MetaData, Table, create_engine, Column
from sqlalchemy.types import String, Date, Time, Text
from sqlalchemy.engine.reflection import Inspector
from sqlalchemy.exc import OperationalError
import logging
import json
import os
from time import time as t_time
from multiprocessing import Pool

from lib.util import json_comment_filter
from lib.config import get_dburi, get_remote_csv_dir


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
    db and readable by the postgres process
    """
    log = logging.getLogger('targets_postgresql')
    stime = t_time()
    dburi = get_dburi()
    engine = create_engine(dburi)
    connection = engine.connect()  # trigger conn. related exceptions, e.g. if db doesn't exist
    metadata = MetaData()

    file_fields = json_comment_filter(json.load(open('file-fields.json', 'r')))
    if not file_prefixes:
        file_prefixes = file_fields.keys()
    todo = []
    for fprefix in sorted(file_prefixes):
        for filename in file_fields[fprefix]:
            for record_type, fields in file_fields[fprefix][filename].items():
                if not fields:
                    log.warning('%s: Missing spec for %s %s' % (fprefix, filename, record_type))
                    continue
                if False:
                    csv_to_table(engine, connection, metadata,
                                 fprefix, filename, record_type, fields)
                else:
                    todo.append((fprefix, filename, record_type, fields))
    if todo:
        n = 1
        with Pool() as pool:
            for table_name, creating in pool.imap_unordered(csv_to_table_tup, todo):
                if creating:
                    log.info('Finished recreating %s (%d of %d)' % (table_name, n, len(todo)))
                else:
                    log.info('Finished creating %s (%d of %d)' % (table_name, n, len(todo)))
                n += 1
    log.debug('csv to postgresql: %ds total time' % (t_time()-stime))


def csv_to_table_tup(tup):
    # required as we don't have pool.starmap_unordered
    dburi = get_dburi()
    engine = create_engine(dburi)
    connection = engine.connect()  # trigger conn. related exceptions, e.g. if db doesn't exist
    metadata = MetaData()
    tup_with_cx = (engine, connection, metadata) + tup
    return csv_to_table(*tup_with_cx)


def csv_to_table(
        engine, connection, metadata,
        fprefix, filename, record_type, fields,
        csv_path=None):
    """
    WARNING: this drops and recreates tables (as specified in file-fields.json)
    """
    log = logging.getLogger('targets_postgresql_csv_to_table')
    if csv_path is None:
        csv_path = os.path.join(get_remote_csv_dir(),
                                '-'.join(filter(None, [fprefix, filename, record_type])) + '.csv')
    table_name = '_'.join(filter(None, [fprefix, filename, record_type])).lower()
    inspector = Inspector.from_engine(engine)
    if not isinstance(fields[0], str) and len(fields[0]) == 2:
        column_names = [f[0] for f in fields]
        column_sizes = [f[1] for f in fields]
    else:
        column_names = fields
        column_sizes = [None] * len(fields)
    columns = []
    for column_size, column_name in zip(column_sizes, column_names):
        if column_name in ['RECORD_TYPE', 'UPDATE_MARKER']:
            continue
        if column_name.endswith('_DATE') and not column_name.endswith('_BY_DATE'):
            type_ = Date()
        elif column_name.endswith('_TIME'):
            type_ = Time()
        elif column_size is None:
            type_ = Text()
        else:
            type_ = String(column_size)
        columns.append(Column(column_name.lower(), type_))
    table = Table(table_name, metadata, *columns)

    creating = table_name in inspector.get_table_names()

    trans = connection.begin()
    try:
        table.drop(
            engine,
            checkfirst=True,  # don't issue a DROP if no table exists
        )
        table.create(engine)
        connection.execute("""COPY "%s"
FROM '%s'
WITH (FORMAT CSV, HEADER);
        """ % (table_name, csv_path))
        trans.commit()
    except OperationalError as oe:
        trans.rollback()
        if 'No such file or directory' in str(oe):
            log.warning('%s not found, no table created' % (csv_path))
        else:
            raise

    return table_name, creating
