import logging
from collections import OrderedDict
import os
import re
from lib.config import get_root_path


def get_view_defs(connection):
    views = OrderedDict()
    db_type = str(connection.engine.url).split(':')[0]
    views_dir = get_root_path('views')
    for view_file in os.listdir(views_dir):
        if (view_file.count('.') == 1 and view_file.endswith('.sql')) or \
           view_file.endswith('.' + db_type + '.sql'):
            with open(os.path.join(views_dir, view_file), 'r') as v:
                curr_view_name = None
                for l in v.readlines():
                    if l.startswith('CREATE VIEW'):
                        curr_view_name = l.split('CREATE VIEW ')[1].split(' AS')[0]
                        views[curr_view_name] = ''
                    elif curr_view_name:
                        views[curr_view_name] += l
    return views


def filter_dependent_views(views, table_name=None):
    dependent_views = set()
    for view_name, view_def in views.items():
        if view_name == table_name:
            continue
        if 'from ' + table_name in view_def.lower() or \
           'join ' + table_name in view_def.lower():
            dependent_views.add(view_name)
            rest = {vn: vd for vn, vd in views.items() if vn != view_name}
            recurse = filter_dependent_views(rest, view_name)
            dependent_views.update(recurse.keys())
    # Maintain original order
    ret = OrderedDict()
    for vn, vd in views.items():
        if vn in dependent_views:
            ret[vn] = vd
    return ret


def drop_views(connection, table_name=False):
    log = logging.getLogger('drop_views')
    views = get_view_defs(connection)
    if table_name:
        views = filter_dependent_views(views, table_name)
    if views:
        for_table_msg = ''
        if table_name:
            for_table_msg = ' for table %s' % (table_name)
        if len(views) <= 4:
            view_names = list(views.keys())
            log.info('Dropping %s%s' % (', '.join(view_names[:-2] + [' & '.join(view_names[-2:])]),
                                        for_table_msg))
        else:
            log.info('Dropping %d views%s' % (len(views), for_table_msg))
        for view_name, _ in reversed(views.items()):
            connection.execute('DROP VIEW IF EXISTS %s;' % (view_name))


def create_views(connection, table_name=False):
    log = logging.getLogger('create_views')
    views = get_view_defs(connection)
    if table_name:
        views = filter_dependent_views(views, table_name)
    for view_name, view_select in views.items():
        try:
            connection.execute('CREATE OR REPLACE VIEW %s AS %s;' %
                               (view_name, view_select))
        except Exception as e:
            missing_relation = re.search('relation ".*?" does not exist', str(e))
            if missing_relation:
                log.error('Could not create view %s: required %s' %
                          (view_name, missing_relation.group()))
            else:
                raise
        else:
            log.info('Created %s view' % (view_name))
