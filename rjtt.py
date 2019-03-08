#!/usr/bin/env python3

from datetime import datetime
import os
import shutil
import logging
from glob import glob
from zipfile import ZipFile
from collections import defaultdict, OrderedDict
from lib.config import get_download_dir, get_unzip_dir

"""
https://www.raildeliverygroup.com/our-services/rail-data/timetable-data.html
has a link to the PDF "RSPS5046 Timetable information data feed interface specification v03-00"
which contains details on the field names and how changesets are applied

This script invents a new convention `RJTTMxxx.ZIP` which is the output of a base
`RJTTFxxx.ZIP` after a series of `RJTTCxxx.ZIP` changesets have been applied to it
"""

update_directory_files = True  # update in place.  assumes a files have been extracted
# and versioning stripped (the `download --unzip` command)
# so that the filename is just their suffix, like the following folder structure:
"""
/RJTT/
    .version.RJTT
    DAT
    MCA
    FLF
    MSN
    REJ
    SET
    ZTR
    CFAs/   # intermediary extracts are placed here, useful for debugging
    mca-cfa-check/  # for verification of update process
"""

# for testing the main CFA->MCA patch process. Skip unzipping and moving around other files
mca_only = False


def apply_changesets(allow_skips=False):
    log = logging.getLogger('rjtt_apply_changesets')
    download_dir = get_download_dir()
    unzip_dir = get_unzip_dir()
    working_dir = os.path.join(unzip_dir, 'RJTT')

    full_version = open(os.path.join(working_dir, '.version.RJTT'), 'r').read().strip()
    orig_full_version = full_version
    forig = os.path.join(download_dir, 'RJTTF' + full_version + '.ZIP')
    if not os.path.exists(forig):
        # working_dir files may have been generated from a changeset
        forig = os.path.join(download_dir, 'RJTTC' + full_version + '.ZIP')
    full_mt = datetime.fromtimestamp(os.path.getmtime(forig))
    changeset_mt_files = []
    for f in glob(os.path.join(download_dir, 'RJTTC*.ZIP')):
        changeset_mt = datetime.fromtimestamp(os.path.getmtime(f))
        if changeset_mt > full_mt:
            changeset_mt_files.append((changeset_mt, f))
    changeset_mt_files.sort()
    prev_version = int(full_version)
    for changeset_mt, changeset_file in changeset_mt_files:
        changeset_version = int(changeset_file.split('/')[-1][5:8])
        if changeset_version == int(full_version):
            # might happen to have been downloaded after the full one
            # but is only for bringing a prior series to the full version
            # we've already got
            continue
        discontinuity = changeset_version != prev_version + 1
        if discontinuity and prev_version == 999 and changeset_version in [0, 1]:
            # not sure whether it resets to 000 or 001
            discontinuity = False
        if discontinuity:
            skip_count = (changeset_version - prev_version) - 1
            if skip_count < 0:
                # digit reset over skipped portion?
                skip_count = 'all'
            if allow_skips:
                log.error('Skipping %s versions before'
                          ' RJTTC%03d' % (skip_count, changeset_version))
            else:
                log.error('Halting as missing RJTTC%03d'
                          '(next one is RJTTC%03d)' % (prev_version + 1, changeset_version))
                break
        prev_version = changeset_version
        full_version = apply_changeset(working_dir, changeset_file, full_version)

    if not mca_only and full_version != orig_full_version:
        incremental_version = os.path.join(download_dir, 'RJTTM' + full_version + '.ZIP')
        log.info('Writing latest to %s' % (incremental_version))
        latest_zip = ZipFile(incremental_version, 'w')
        # todo: read this list from the DAT file
        for suffix in ['ZTR', 'REJ', 'SET', 'FLF', 'MCA', 'MSN', 'DAT']:
            latest_zip.write(
                os.path.join(working_dir, suffix),
                'RJTTF' + full_version + '.' + suffix)
        latest_zip.close()
        latest_path = os.path.join(download_dir, 'RJTT-FULL-LATEST.ZIP')
        if os.path.exists(latest_path):
            os.unlink(latest_path)
        os.symlink(incremental_version, latest_path)
        log.info('Also linked this at  %s' % (latest_path))
    else:
        log.debug('No new changeset updates')


def get_record_key(line):
    # how deletions can be done between files. Also unique within a given file
    if line[:2] == 'BS':
        if line[79] not in 'CNOP' or line[79] != line.strip()[-1]:
            raise Exception('unexpected BS line')
        # 5.3.3.3 A train schedule can be uniquely identified by
        # UID, Start-date & Overlay indicator.
        return line[3:15] + line[79]
    if line[:2] in ['TI', 'TD', 'TA']:
        # based on the fact that the 'TD' (TIPLOC Delete)
        # record is blank after character 9
        return line[2:9]
    if line[:2] == 'AA':
        if line[79] not in 'CNOP' or line[79] != line.strip()[-1]:
            raise Exception('unexpected AA line')
        # undocumented? combination of the 2 train ids + start_date
        return line[3:][:18] + line[79]
    return None  # should not matter for this line?


def apply_changeset(working_dir, changeset_file, full_version):
    log = logging.getLogger('rjtt_apply_changesets')
    out_dir = working_dir
    changeset_zip = ZipFile(changeset_file, 'r')
    new_version = None
    directory_version = open(os.path.join(working_dir, '.version.RJTT'), 'r').read().strip()
    to_move = {}
    for member in changeset_zip.infolist():
        if new_version is None:
            new_version = member.filename[5:].split('.')[0]
        elif new_version != member.filename[5:].split('.')[0]:
            raise Exception('multiple versions within zip')

        member_out_dir = out_dir
        if member.filename.endswith('.CFA'):
            suffix = 'MCA'
            member_out_dir = os.path.join(out_dir, 'CFAs')
            if not os.path.exists(member_out_dir):
                os.makedirs(member_out_dir)
        else:
            suffix = member.filename.split('.', 1)[-1]

        if mca_only and suffix != 'MCA':
            continue

        changeset_zip.extract(member, member_out_dir)
        working_file = os.path.join(member_out_dir, member.filename)
        if member.filename.startswith('RJTTF') or member.filename.endswith('.DAT'):
            if update_directory_files:
                # overwrite the directory
                shutil.move(working_file, os.path.join(out_dir, suffix))
            continue

        if not update_directory_files:
            existing_full = os.path.join(out_dir, 'RJTTF' + full_version + '.' + suffix)
            if os.path.exists(existing_full):
                incremental_file = existing_full
            else:
                raise Exception('couldn\'t find starting file for %s,'
                                ' expecting %s' % (suffix, existing_full))
        else:
            if directory_version == full_version:
                incremental_file = os.path.join(out_dir, suffix)
            else:
                raise Exception('mismatch between versioning file'
                                '%s and expected %s' % (directory_version, full_version))
        outf = []
        deletions = set()
        insertions = defaultdict(OrderedDict)
        done_zz_check = False
        current_insertion = False
        seen_keys = defaultdict(set)  # check that we're creating keys correctly
        for change_line in open(working_file, 'r').readlines():
            record_identity = change_line[:2]
            record_key = get_record_key(change_line)
            if record_key:
                if record_key in seen_keys[record_identity]:
                    if record_key in insertions.get(record_identity, {}) and (
                            (record_identity in ['BS', 'AA'] and change_line[2] in 'DR') or
                            record_identity in ['TD', 'TA']
                    ):
                        # seen in wild and can only interpret as
                        # cancellation of an accidental insertion
                        del insertions[record_identity][record_key]
                        continue
                    elif (record_identity, record_key) in deletions:
                        # seen in wild with AAD (P) -> AAN (O) -> AAN (P)
                        pass  # let the deletion plus insertion happen
                    else:
                        raise Exception('Unexpected duplicate key %s in file' % (record_key))
                seen_keys[record_identity].add(record_key)
            if record_identity == 'HD':
                # off by one here (docs are incorrect and say 47)
                if change_line[46] != 'U':
                    raise Exception('Expected to apply a changeset, header row'
                                    ' in %s seems to indicate otherwise' % (working_file))
                outf.append(change_line[:46] + 'F' + change_line[47:])
                continue
            if record_identity == 'ZZ':
                if not change_line.strip() == 'ZZ':
                    raise Exception('Junk after ZZ?: ' + change_line)
                done_zz_check = True
                continue
            elif done_zz_check:
                raise Exception('something after ZZ row in %s' % (working_file))
            if record_identity in ['BS', 'AA']:
                if change_line[2] in 'DR':
                    deletions.add((record_identity, record_key))
                    current_insertion = False
                if change_line[2] in 'NR':
                    line = change_line[:2] + 'N' + change_line[3:]
                    insertions[record_identity][record_key] = [line]
                    if current_insertion:
                        cii, cik = current_insertion
                        if insertions[cii][cik][-1].startswith('BSN'):
                            pass  # there are single line BSN records, contrary to spec
                        elif insertions[cii][cik][-1].startswith('AAN'):
                            pass  # expected; these are single line
                        elif False:
                            # gonna be liberal and not raise here but is unexpected
                            raise Exception('Unfinished insertion?')
                    current_insertion = record_identity, record_key
            elif current_insertion:
                insertions[current_insertion[0]][current_insertion[1]].append(change_line)
                if current_insertion[0] == 'BS' and record_identity == 'LT':
                    current_insertion = False
            else:
                if record_identity in ['TI', 'TA']:
                    insertions['TI'][record_key] = ['TI' + change_line[2:]]
                if record_identity in ['TD', 'TA']:
                    # using 'TI' here as that's the lines that we'll be looking up
                    # as to whether they need deletion
                    deletions.add(('TI', record_key))
                if record_identity not in ['ZZ', 'TI', 'TA', 'TD']:
                    raise Exception('Unknown or unexpected record'
                                    ' identity: %s' % (record_identity))
                pass
        total = 0
        prev_major_record_type = False
        deleting = False
        seen_keys = defaultdict(set)
        for orig_line in open(incremental_file, 'r').readlines():
            record_identity = orig_line[:2]
            record_key = get_record_key(orig_line)
            if record_key:
                if record_key in seen_keys[record_identity]:
                    raise Exception('Duplicate record key'
                                    ' - are we creating keys correctly? %s' % (record_key))
                seen_keys[record_identity].add(record_key)

            total += 1
            if record_identity == 'HD':
                if orig_line[46] != 'F':
                    raise Exception('Expected to work on top of full file, header row'
                                    'in %s seems to indicate otherwise' % (incremental_file))
                continue  # skip as we've already included the one from the change file instead

            if record_identity in ['BS', 'BX', 'LO', 'LI', 'CR', 'LT']:
                major_record_type = 'BS'
            else:
                major_record_type = record_identity
            major_section_change = prev_major_record_type != major_record_type

            if record_identity in insertions:
                if record_identity == 'BS':
                    bs_date = datetime.strptime(orig_line[9:][:6], '%y%m%d')
                elif record_identity == 'AA':
                    aa_date = datetime.strptime(orig_line[15:][:6], '%y%m%d')
                to_delete = []
                for key in insertions[record_identity]:
                    # default to ascii sort order. presumably ordering can be important for correct
                    # parsing but more practically, is needed for verifying via diff (see the
                    # mca-cfa-check folder) that we are applying changesets correctly
                    insert_before = insertions[record_identity][key][0] < orig_line
                    if record_identity == 'BS':
                        # sort order based on start date
                        # but where there is a reference to the same record (trainuic/startdate)
                        # then there is also a defined ordering
                        if key[:-1] == record_key[:-1]:
                            insert_before = 'PONC'.index(key[-1]) < 'PONC'.index(record_key[-1])
                        else:
                            insertion_date = datetime.strptime(key[6:][:6], '%y%m%d')
                            if insertion_date != bs_date:
                                insert_before = insertion_date < bs_date
                    elif record_identity == 'AA':
                        # TODO: should probably apply PONC precedence as per BS above
                        # but haven't come across a problem in the wild
                        insertion_date = datetime.strptime(key[12:][:6], '%y%m%d')
                        if insertion_date != aa_date:
                            insert_before = insertion_date < aa_date
                    if insert_before:
                        for insertion_line in insertions[record_identity][key]:
                            outf.append(insertion_line)
                        to_delete.append(key)  # Python 3.5 doesn't let you delete during iteration
                    else:
                        break
                for key in to_delete:
                    del insertions[record_identity][key]  # don't insert twice
            if (record_identity, record_key) in deletions:
                if record_identity in ['BS', 'AA'] and orig_line[2] != 'N':
                    raise Exception('trying to delete a non creation line %s %s %s' %
                                    (orig_line[:3], record_key,
                                     'is the intended deletion target '
                                     'BSN/AAN line later in the file?'))
                if record_identity == 'BS':
                    deleting = True  # multi-line delete
                deletions.remove((record_identity, record_key))
                if record_key in insertions.get(record_identity, {}):
                    # a revision ; reinsert in same place
                    for insertion_line in insertions[record_identity][record_key]:
                        outf.append(insertion_line)
                    del insertions[record_identity][record_key]
                continue  # skip (don't append)
            elif deleting:
                if record_identity in ['BX', 'LO', 'LI', 'CR', 'LT']:
                    if record_identity == 'LT':
                        deleting = False
                    continue  # skip
                deleting = False

            if major_section_change and prev_major_record_type in insertions:
                log.debug('%s %s -> %s' % (
                    member.filename, prev_major_record_type, major_record_type))
                # insert remaining at end before record type changes
                to_delete = []
                for key, insertion_list in insertions[prev_major_record_type].items():
                    for insertion_line in insertion_list:
                        outf.append(insertion_line)
                    to_delete.append(key)
                for key in to_delete:
                    del insertions[prev_major_record_type][key]  # mark as done
            prev_major_record_type = major_record_type
            outf.append(orig_line)
        for k in insertions:
            if insertions[k]:
                if deletions:
                    raise Exception('Remaining insertions and deletions from %s' % (working_file))
                else:
                    raise Exception('Remaining insertions in %s' % (working_file))
        if deletions:
            # should be all cleared out - maybe we've missed how to make the record_key for them?
            raise Exception('Remaining deletions in %s' % (working_file))
        new_file = os.path.join(out_dir, 'RJTTF' + new_version + '.' + suffix)
        if update_directory_files:
            to_move[new_file] = os.path.join(out_dir, suffix)
        open(new_file, 'w').writelines(outf)

        if suffix == 'MCA':
            corresponding_full = os.path.join(out_dir, '..', 'RJTTF' + new_version + '.ZIP')
            if os.path.exists(corresponding_full):
                check_dir = os.path.join(out_dir, 'mca-cfa-check')
                if not os.path.exists(check_dir):
                    os.makedirs(check_dir)
                    with open(os.path.join(check_dir, 'README.txt'), 'w') as readme:
                        readme.write("""This folder contains full and incrementally updated
versions of the main RJTT MCA file.  If the incremental update process is working correctly,
files with the same versioning should differ in only their header line""")
                check_file = os.path.join(check_dir, 'RJTTM' + new_version + '.' + suffix)
                log.info('Outputting for checking: ' + check_file + ' vs. RJTTF' +
                         new_version + '.' + suffix + ' (only the header line should differ)')
                shutil.copyfile(new_file, check_file)
                corresponding_zip = ZipFile(corresponding_full, 'r')
                for cmember in corresponding_zip.infolist():
                    if cmember.filename.endswith('.'+suffix):
                        corresponding_zip.extract(cmember, check_dir)
                        break
                # TODO: actually do a diff and raise an exception if there is a mismatch

    # be a bit transactional by moving files and delaying
    # updating the version until after everything has succeeded
    if update_directory_files:
        for src, dst in to_move.items():
            shutil.move(src, dst)
        open(os.path.join(working_dir, '.version.RJTT'), 'w').write(new_version + '\n')
    return new_version
