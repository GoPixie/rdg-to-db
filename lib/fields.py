
import logging

from .fixed_fields import iterate_fixed_fields


def iterate_fields(file_path, fields, full_only=True):
    for r in _iterate_fields(file_path, fields, full_only):
        if full_only and 'UPDATE_MARKER' in r:
            if r['UPDATE_MARKER'] != 'R':
                raise Exception('%s Expected full file, not'
                                'changes Line "%s"' % (file_sig, ''.join(r.values())))
            del r['UPDATE_MARKER']
        yield r


def _iterate_fields(file_path, fields, full_only=True):
    log = logging.getLogger('iterate_fields')
    file_sig = '/'.join(file_path.split('/')[-2:])
    if not fields or not sum(fields.values(), []):
        log.warning('No fields defined for %s' % (file_sig))
        return
    log.debug('ingesting %s' % (file_sig))

    # sniff definition to see if it looks like a fixed definition
    # e.g. [["CLUSTER_ID", 4], ["CLUSTER_NLC", 4], ...]
    random_val = next(iter(fields.values()))
    if not isinstance(random_val[0], str) and len(random_val[0]) == 2:
        for r in iterate_fixed_fields(file_path, fields, full_only):
            yield r
        return

    RECORD_TYPE_positions = None
    if len(fields) == 1 and list(fields.keys())[0] == '':
        field_names = list(fields.values())[0]
    else:
        RECORD_TYPE_positions = set(fv.index('RECORD_TYPE') for fv in fields.values())
    with open(file_path, 'r') as f:
        for fi, line in enumerate(f.readlines()):
            if line.startswith('/'):
                continue
            row = line.strip().split(',')
            if RECORD_TYPE_positions:
                for pos in RECORD_TYPE_positions:
                    if row[pos] in fields:
                        field_names = fields[row[pos]]
                        break
                else:
                    raise Exception('%s Unknown row type: %s' % (file_sig, line))
            if len(row) != len(field_names):
                raise Exception('%s Line "%s" (%d fields) doesn\'t match spec (%d fields): %r' % (
                    file_sig, line, len(row), len(field_names), field_names))
            yield dict(zip(field_names, row))
