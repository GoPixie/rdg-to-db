
from collections import OrderedDict
from time import time as t_time
import logging

UPDATE_MARKER_vals = 'RIAD'


class NotFixedFieldsException(Exception):
    pass


def field_sum(field_pairs):
    return sum(f[1] for f in field_pairs)


def iterate_fixed_fields(file_path, fields, full_only=True):
    log = logging.getLogger('iterate_fixed_fields')
    file_sig = '/'.join(file_path.split('/')[-2:])
    record_type_pos = False
    for v in fields.values():
        field_names = [vi[0] for vi in v]
        if 'RECORD_TYPE' not in field_names:
            record_type_pos = False
            break
        field_values = [vi[1] for vi in v]
        vpos = field_names.index('RECORD_TYPE')
        v_pos_tup = (sum(field_values[:vpos]), sum(field_values[:vpos])+field_values[vpos])
        if not record_type_pos:
            record_type_pos = v_pos_tup
        elif record_type_pos != v_pos_tup:
            raise Exception('%s Multiple positions for RECORD_TYPE field. Bug in file-fields.json'
                            ', or something the parser needs to handle?:\n%r' % (file_sig, fields))
            record_type_pos = False
            break
    csv_like = None  # undetermined
    with open(file_path, 'r') as fxf:
        last_fi = 0
        last_rtime = 0
        rstime = t_time()
        stime = t_time()
        for fi, line in enumerate(fxf.readlines()):
            if line.startswith('/'):
                continue
            line = line.rstrip('\n')
            if csv_like is None and ',' in line:
                raise NotFixedFieldsException()
            csv_like = False
            ld = OrderedDict()
            offset = 0
            if record_type_pos:
                record_type = line[record_type_pos[0]:record_type_pos[1]]
                field_names = [f[0] for f in fields[record_type]]
                field_lens = [f[1] for f in fields[record_type]]
            elif set(fields.keys()) == {''}:
                field_names = [f[0] for f in fields['']]
                field_lens = [f[1] for f in fields['']]
                if (line[0] in UPDATE_MARKER_vals and
                        len(line) == sum(field_lens) + 1):
                    if full_only and line[0] != 'R':
                        raise Exception('%s Expected full file, not '
                                        'changes Line "%s"' % (file_sig, line))
                    offset = 1
            else:
                if len(set(map(len, fields.keys()))) > 1:
                    raise Exception('%s Need to deal with mixed size RECORD_TYPE'
                                    'field lengths in the same file' % (file_sig))
                fkl = len(max(fields.keys()))
                if (line[0] in UPDATE_MARKER_vals and
                        line[1:][:fkl] in fields and
                        len(line) == field_sum(fields[line[1:][:fkl]]) + 1 + fkl):
                    record_type = line[1:][:fkl]
                    offset = 1 + fkl
                    if full_only and line[0] != 'R':
                        raise Exception('%s Expected full file, not'
                                        'changes Line "%s"' % (file_sig, line))
                elif (line[:fkl] in fields and
                        len(line) == field_sum(fields[line[:fkl]]) + fkl):
                    record_type = line[:fkl]
                    offset = fkl
                elif (line[0] in UPDATE_MARKER_vals and
                        line[1:][:fkl] in fields):
                    raise Exception('%s Line "%s" (len %d) doesn\'t match spec (len %d): %s %r' % (
                        file_sig, line, len(line), field_sum(fields[line[1:][:fkl]]),
                        line[1:][:fkl], fields[line[1:][:fkl]]))
                else:
                    raise Exception('%s Can\'t find a record type for line "%s" (len %d)' %
                                    (file_sig, line, len(line)))
                field_names = [f[0] for f in fields[record_type]]
                field_lens = [f[1] for f in fields[record_type]]
                ld['RECORD_TYPE'] = record_type
            if sum(field_lens) != len(line)-offset:
                raise Exception('%s Line "%s" (len %d) doesn\'t match spec (len %d): %s %r' % (
                    file_sig, line, len(line), sum(field_lens), record_type,
                    fields[record_type]))
            for i, l in enumerate(field_lens):
                fstart = sum(field_lens[:i]) + offset
                fend = sum(field_lens[:i]) + l + offset
                ld[field_names[i]] = line[fstart:fend].strip()
            yield ld

            # Some progress indication if things are taking a long time
            if fi % 1000 == 0:
                rtime = round((t_time() - rstime)/10)
                if last_rtime != rtime:  # at most every 10 seconds
                    lines_per_sec = (fi - last_fi)/(t_time() - stime)
                    if lines_per_sec > 1000:
                        per_sec = '%dK' % (lines_per_sec/1000)
                    elif lines_per_sec > 10:
                        per_sec = '%d' % (lines_per_sec)
                    else:
                        per_sec = '%.2f' % (lines_per_sec)
                    log.debug('%s %s lines per second %s %s %s %s' %
                              (file_sig, per_sec, last_fi, fi, last_rtime, rtime))
                    last_fi = fi
                    stime = t_time()
                    last_rtime = rtime
