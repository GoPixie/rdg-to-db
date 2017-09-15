from sqlalchemy import MetaData, create_engine, Table, Column
from sqlalchemy.engine.reflection import Inspector
from sqlalchemy.types import String, Date, Time, Text
from sqlalchemy.exc import OperationalError
import logging
import json
import os
from multiprocessing import Pool
from time import time as t_time
from collections import defaultdict

from lib.util import json_comment_filter
from lib.fields import iterate_fields
from lib.config import get_dburi, get_download_dir
from .unzip import iterate_unzipped
from views.views import drop_views, create_views


def db(file_prefixes=None):
    """
    Transfer files extracted from ZIP to database
    according to schema defined in `file-fields.json`
    and `field-pks.json`
    Multi database support is provided by SqlAlchemy library,
    so PostgreSQL, MySQL/MariaDB and SQLite should be
    supported out of the box. Connection string is
    defined in local.cfg
    """
    log = logging.getLogger('targets_db')
    stime = t_time()
    dburi = get_dburi()
    engine = create_engine(dburi)
    engine.connect()  # trigger conn. related exceptions, e.g. if db doesn't exist
    metadata = MetaData()

    todo = []
    for fprefix, filename, file_path, file_fields in iterate_unzipped(file_prefixes):
        if False:
            # don't multiprocess
            tables, row_counts, new_tables = file_to_db(engine, metadata, fprefix, filename, file_path, file_fields)
            for record_type, table in tables.items():
                created_str = 'Recreated'
                if table in new_tables:
                    created_str = 'Created'
                log.info('%s table %s (%d rows)' % (created_str,
                                                    table.name, row_counts[table]))
        else:
            todo.append((fprefix, filename, file_path, file_fields))
    if todo:
        n = 1
        with Pool() as pool:
            for tables, row_counts, new_tables in pool.imap_unordered(file_to_db_tup, todo):
                log.info('Finished processing %s/%s (%d of %d)' % (
                    fprefix, filename, n, len(todo)))
                for record_type, table in tables.items():
                    created_str = 'Recreated'
                    if table in new_tables:
                        created_str = 'Created'
                    log.info('%s table %s (%d rows)' % (created_str,
                                                      table.name, row_counts[table]))
                n += 1

    log.debug('db: %ds total time' % (t_time()-stime))


def drop_create_table(connection, table):
    drop_views(connection, table.name)
    table.drop(
        connection,
        checkfirst=True,  # don't issue a DROP if no table exists
    )
    table.create(connection)
    create_views(connection, table.name)


def table_from_fields(
        engine, metadata,
        fprefix, filename, record_type, table_fields, pks=[]):
    log = logging.getLogger('targets_db_create_table')
    table_name = '_'.join(filter(None, [fprefix, filename, record_type])).lower()
    if not isinstance(table_fields[0], str) and len(table_fields[0]) == 2:
        column_names = [f[0] for f in table_fields]
        column_sizes = [f[1] for f in table_fields]
    else:
        column_names = table_fields
        column_sizes = [None] * len(table_fields)
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
        columns.append(Column(column_name.lower(), type_, primary_key=column_name in pks))
    table = Table(table_name, metadata, *columns)
    return table


def file_to_db_tup(tup):
    # required as we don't have pool.starmap_unordered
    dburi = get_dburi()
    engine = create_engine(dburi)  # each process needs it's own engine
    metadata = MetaData()
    tup_with_cx = (engine, metadata) + tup
    return file_to_db(*tup_with_cx)

def file_to_db(
        engine, metadata,
        fprefix, filename, file_path=None, file_fields=None, pks=[]):
    """
    WARNING: this drops and recreates tables
    A file can have multiple record types. Output separate
    tables for each one
    """
    log = logging.getLogger('targets_db_file_to_db')
    if file_path is None:
        file_path = os.path.join(get_download_dir(), fprefix, filename)

    if file_fields is None:
        file_fields = json_comment_filter(json.load(open('file-fields.json', 'r')))
    fields = file_fields[fprefix][filename]

    inspector = Inspector.from_engine(engine)

    connection = engine.connect()
    trans = connection.begin()
    tables = {}
    row_counts = defaultdict(int)
    new_tables = []
    batches = defaultdict(list)
    batch_size = 10000
    last_batches = []
    try:
        for record in iterate_fields(file_path, fields):
            record_type = record.get('RECORD_TYPE', '')

            if record_type not in tables:
                table = table_from_fields(engine, metadata, fprefix, filename,
                                   record_type, fields[record_type], pks)
                if table.name not in inspector.get_table_names():
                    new_tables.append(table)
                tables[record_type] = table
                drop_create_table(connection, table)
            else:
                table = tables[record_type]

            if record_type:
                del record['RECORD_TYPE']  # encapsulated in table name

            batches[table].append(record)
            if len(batches[table]) >= batch_size:
                log.debug('Inserting %d to %s' % (len(batches[table]), table.name))
                stime = t_time()
                connection.execute(
                    table.insert(),
                    batches[table]
                )
                batch_perf = (t_time() - stime) / batch_size
                last_batches.append((batch_size, batch_perf))
                if len(last_batches) == 1:
                    pass
                elif len(last_batches) == 2:
                    batch_size *= 2
                else:
                    # adaptively scale the batch size up or down
                    last_batch_size, last_batch_perf = last_batches[-2]
                    if batch_perf < last_batch_perf:
                        # better than last
                        if last_batch_size < batch_size:
                            batch_size *= 2
                        else:
                            batch_size /= 3
                    else:
                        if last_batch_size < batch_size:
                            batch_size /= 2
                        else:
                            batch_size *= 3
                    batch_size = max(1000, batch_size)

                row_counts[table] += len(batches[table])
                batches[table] = []

        for table, final_batch in batches.items():
            row_counts[table] += len(final_batch)
            log.debug('Inserting final %d to %s' % (len(final_batch), table.name))
            connection.execute(
                table.insert(),
                final_batch
            )
        trans.commit()
    except OperationalError as oe:
        raise

    return tables, row_counts, new_tables
