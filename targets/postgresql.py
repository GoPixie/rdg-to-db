from sqlalchemy import MetaData, Table, create_engine, Column
from sqlalchemy.types import String, Date, Time, Text
from sqlalchemy.engine.reflection import Inspector
from sqlalchemy.exc import OperationalError
import logging
import json
import os
from time import time as t_time
from multiprocessing import Pool
import re

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
    drop_views(engine)
    for fprefix in sorted(file_prefixes):
        for filename in file_fields[fprefix]:
            for record_type, fields in file_fields[fprefix][filename].items():
                pks = field_pks.get(fprefix, {}).get(filename, {}).get(record_type, [])
                if not fields:
                    log.warning('%s: Missing spec for %s %s' % (fprefix, filename, record_type))
                    continue
                if False:
                    table_name, creating = csv_to_table(engine, metadata,
                                                        fprefix, filename, record_type, fields, pks)
                    if creating:
                        log.info('Finished recreating %s' % (table_name))
                    else:
                        log.info('Finished creating %s' % (table_name))
                else:
                    todo.append((fprefix, filename, record_type, fields, pks))
    if todo:
        n = 1
        with Pool() as pool:
            for table_name, creating in pool.imap_unordered(csv_to_table_tup, todo):
                if creating:
                    log.info('Finished recreating %s (%d of %d)' % (table_name, n, len(todo)))
                else:
                    log.info('Finished creating %s (%d of %d)' % (table_name, n, len(todo)))
                n += 1
    create_views(engine)
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
    WARNING: this drops and recreates tables (as specified in file-fields.json)
    """
    connection = engine.connect()
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
        columns.append(Column(column_name.lower(), type_, primary_key=column_name in pks))
    table = Table(table_name, metadata, *columns)

    creating = table_name in inspector.get_table_names()

    trans = connection.begin()
    try:
        table.drop(
            connection,
            checkfirst=True,  # don't issue a DROP if no table exists
        )
        table.create(connection)

        force_not_null = ''
        if pks and pks != ['invalid']:
            force_not_null = ', FORCE_NOT_NULL ("%s")' % ('", "'.join([p.lower() for p in pks]))
        connection.execute("""COPY "%s"
FROM '%s'
WITH (FORMAT CSV, HEADER%s);
        """ % (table_name, csv_path, force_not_null))

        trans.commit()
    except OperationalError as oe:
        trans.rollback()
        if 'No such file or directory' in str(oe):
            log.warning('%s not found, no table created' % (csv_path))
        else:
            raise

    return table_name, creating


VIEWS = [
    ('rjfa_rte_l_agg', """
    SELECT route_code, end_date,
    array_aggx(CASE WHEN incl_excl = 'I' THEN rjfa_rte_l.crs_code ELSE null END) AS crs_inclusions,
    array_aggx(CASE WHEN incl_excl = 'E' THEN rjfa_rte_l.crs_code ELSE null END) AS crs_exclusions,
    array_aggx(CASE WHEN incl_excl = 'I' THEN rjfa_rte_l.nlc_code ELSE null END) AS nls_inclusions,
    array_aggx(CASE WHEN incl_excl = 'E' THEN rjfa_rte_l.crs_code ELSE null END) AS nlc_exclusions
    FROM rjfa_rte_l
    GROUP BY route_code, end_date"""),

    ('rjrg_rgk_d_agg', """
    SELECT route_code,
    array_aggx(CASE WHEN entry_type = 'A' THEN rjrg_rgk_d.crs_code ELSE null END) AS rgk_crs_inclusions,
    array_aggx(CASE WHEN entry_type = 'I' THEN rjrg_rgk_d.crs_code ELSE null END) AS rgk_crs_anys,
    array_aggx(CASE WHEN entry_type = 'E' THEN rjrg_rgk_d.crs_code ELSE null END) AS rgk_crs_exclusions,
    array_aggx(CASE WHEN entry_type = 'T' THEN rjrg_rgk_d.toc_id ELSE null END) AS toc_inclusions,
    array_aggx(CASE WHEN entry_type = 'X' THEN rjrg_rgk_d.toc_id ELSE null END) AS toc_exclusions,
    array_aggx(CASE WHEN entry_type = 'L' THEN rjrg_rgk_d.mode_code ELSE null END) AS mode_inclusions,
    array_aggx(CASE WHEN entry_type = 'N' THEN rjrg_rgk_d.mode_code ELSE null END) AS mode_exclusions
    FROM rjrg_rgk_d
    GROUP BY route_code"""),

    ('route_code', """
    SELECT route_code, daterange(start_date, CASE WHEN end_date = '2999-12-31' THEN null ELSE end_date+1 END) AS date_range, quote_date, description,
    concat(atb_desc_1, atb_desc_2, atb_desc_3, atb_desc_4) AS atb_desc,
    crs_inclusions, crs_exclusions, rgk_crs_inclusions, rgk_crs_anys, rgk_crs_exclusions, rjrg_rgk_l.london_marker,
    toc_inclusions, toc_exclusions, mode_inclusions, mode_exclusions
    FROM rjfa_rte_r
    LEFT JOIN rjfa_rte_l_agg USING (route_code, end_date)
    LEFT JOIN rjrg_rgk_l USING (route_code)
    LEFT JOIN rjrg_rgk_d_agg USING (route_code)
    """),
]


def drop_views(engine):
    log = logging.getLogger('targets_postgresql_drop_views')
    log.info('Dropping %d views' % (len(VIEWS)))
    connection = engine.connect()
    for view_name, _ in reversed(VIEWS):
        connection.execute('DROP VIEW IF EXISTS %s;' % (view_name))


def create_views(engine):
    log = logging.getLogger('targets_postgresql_drop_views')
    connection = engine.connect()
    for view_name, view_select in VIEWS:
        # Some magic to remove boilerplate from above view definitions
        # could also define array_aggx as a database function (want to also remove nulls)
        view_select = re.sub('array_aggx\((.*?)\) AS ', r'array_remove(array_agg(\1), null) AS ', view_select)
        try:
            connection.execute('CREATE OR REPLACE VIEW %s AS %s;' % (view_name, view_select))
        except Exception as e:
            missing_relation = re.search('relation ".*?" does not exist', str(e))
            if missing_relation:
                log.error('Could not create view %s: required %s' % (view_name, missing_relation.group()))
            else:
                raise
        else:
            log.info('Created %s view' % (view_name))
