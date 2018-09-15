
import logging

from .fixed_fields import iterate_fixed_fields, NotFixedFieldsException


# not 'RESTRICTED_BY_DATE'
DATE_FIELDS = ['START_DATE', 'END_DATE', 'QUOTE_DATE', 'LAST_VALID_DATE', 'LAST_VALID_DAY']

# FARE is in cents, not decimal
INT_FIELDS = ['FARE', 'ADULT_FARE', 'CHILD_FARE',
              'ROUTE_CODE', 'OUT_DAYS', 'OUT_MONTHS',
              'RET_DAYS', 'RET_MONTHS', 'RET_AFTER_DAYS', 'RET_AFTER_MONTHS',
              'MAX_PASSENGERS', 'MIN_PASSENGERS', 'MAX_ADULTS', 'MIN_ADULTS',
              'MAX_CHILDREN', 'MIN_CHILDREN', 'MAX_HOLDERS', 'MIN_HOLDERS',
              'MAX_ACC_ADULTS', 'MIN_ACC_ADULTS', 'DAYS_TRAVEL', 'MONTHS_VALID', 'DAYS_VALID']


def iterate_fields(file_path, fields, convert_dates=True, full_only=True):
    file_sig = '/'.join(file_path.split('/')[-2:])
    for r in _iterate_fields(file_path, fields, full_only):
        if full_only and 'UPDATE_MARKER' in r:
            if r['UPDATE_MARKER'] != 'R':
                raise Exception('%s Expected full file, not'
                                'changes Line "%s"' % (file_sig, ''.join(r.values())))
            del r['UPDATE_MARKER']
        if convert_dates:
            for k in r.keys():
                if k in DATE_FIELDS and r[k]:
                    if len(r[k]) != 8:
                        raise Exception('%s Unexpected size for apparant date field %s %s %d' %
                                        (file_sig, k, r[k], len(r[k])))
                    r[k] = '-'.join([r[k][4:], r[k][2:4], r[k][:2]])
        for k in ['ROUTE_CODE']:
            if k in r and r[k] == '*' * len(r[k]):
                r[k] = '-1'  # can't be null in case it's needed to form a composite primary key
        yield r


def _iterate_fields(file_path, fields, full_only=True):
    log = logging.getLogger('iterate_fields')
    file_sig = '/'.join(file_path.split('/')[-2:])
    if not fields or not sum(fields.values(), []):
        log.warning('No fields defined for %s' % (file_sig))
        return
    log.debug('ingesting %s' % (file_sig))

    # sniff definition to see if it looks like a fixed definition

    random_val = next(iter(fields.values()))
    RECORD_TYPE_positions = None
    if not isinstance(random_val[0], str) and len(random_val[0]) == 2:
        try:
            # Old convention was that presence of char length indicated fixed width:
            # [["CLUSTER_ID", 4], ["CLUSTER_NLC", 4], ...]
            for r in iterate_fixed_fields(file_path, fields, full_only):
                yield r
            return
        except NotFixedFieldsException:
            # However, CSV style files now also include field width for specifying db col size
            pass
        # Throw away field width info for the purposes of the rest of the import:
        fields = dict([(k, [f[0] for f in fv]) for k, fv in fields.items()])
    if fields.keys() == {''}:
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
