from pathlib import Path
from jinja2 import Environment, FileSystemLoader
import os, traceback
from utils import global_const as gc


def get_project_root():
    # Returns project root folder.
    return Path(__file__).parent.parent


def file_exists(fn):
    try:
        with open(fn, "r"):
            return 1
    except IOError:
        return 0

def is_excel(file_path):
    ext = Path(file_path).suffix
    if 'xls' in ext:
        return True
    else:
        return False

def identify_delimeter_by_file_extension(file_path):
    ext = Path(file_path).suffix
    out_value = None

    if ext == 'csv':
        out_value = ','
    elif ext == 'tab':
        out_value = '   '
    elif 'xls' in ext:
        out_value = None
    else:
        out_value = ','

    return  out_value

def start_external_process_async (exec_path):
    from subprocess import Popen
    process = Popen(exec_path, shell=True)
    return process

def check_external_process(process):
    pr_out = process.poll()
    if pr_out is None:
        status = 'running'
        message = ''
    else:
        status = 'stopped'
        message = pr_out
    out = {'status': status, 'message': message}
    return out

def replace_unacceptable_chars (val, bad_chars = None):
    val_loc = str(val)
    if not bad_chars:
        bad_chars = ['/', ' ']
    # replace not allowed characters with "_"
    for ch in bad_chars:
        val_loc = val_loc.replace(ch, '_')
    # remove repeating "_" symbols
    while '__' in val_loc:
        val_loc = val_loc.replace('__', '_')
    return val_loc

def populate_email_template(template_name, template_feeder):
    file_loader = FileSystemLoader('templates')
    env = Environment(loader=file_loader)
    env.trim_blocks = True
    env.lstrip_blocks = True
    env.rstrip_blocks = True

    template = env.get_template(template_name)
    output = template.render(inquiry=template_feeder)
    # print(output)
    return output

def move_file_to_processed(file_path, new_file_name, processed_dir_path, log_obj, error_obj):
    if not os.path.exists(processed_dir_path):
        # if Processed folder does not exist in the current study folder, create it
        log_obj.info('Creating directory for processed files "{}"'.format(processed_dir_path))
        os.mkdir(processed_dir_path)

    file_name = Path(file_path).name
    file_name_new = new_file_name
    file_name_new_path = Path(processed_dir_path) / file_name_new
    cnt = 0
    #check if file with the same name was already saved in "processed" dir
    while os.path.exists(file_name_new_path):
        # if file exists, identify a new name, so the new file won't overwrite the existing one
        if cnt >= gc.PROCESSED_FOLDER_MAX_FILE_COPIES and gc.PROCESSED_FOLDER_MAX_FILE_COPIES >= 0:
            file_name_new_path = None
            break
        cnt += 1
        file_name_new = '{}({}){}'.format(os.path.splitext(file_name)[0], cnt, os.path.splitext(file_name)[1])
        file_name_new_path = Path(processed_dir_path) / file_name_new

    if not file_name_new_path is None:
        # new file name was successfully identified
        # move the file to the processed dir under the identified new name
        try:
            os.rename(file_path, file_name_new_path)
            log_obj.info('Processed file "{}" was moved to "{}" under {} name: "{}".'
                         .format(str(file_path), str(processed_dir_path)
                              ,('the same' if cnt == 0 else 'the new')
                              ,file_name_new_path))
        except Exception as ex:
            _str = 'Error occurred during moving the file "{}" to processed folder. \nError: {}\n{}'.format(
                str(file_path), ex, traceback.format_exc())
            log_obj.error(_str)
            error_obj.add_error(_str)
            file_name_new_path = None

    else:
        # new file name was not identified
        _str = 'Processed file "{}" cannot be moved to "{}" because {} copies of this file already exist in this ' \
               'folder that exceeds the allowed application limit of copies for the same file.'\
            .format(file_path, processed_dir_path, cnt + 1)
        log_obj.error (_str)
        error_obj.add_error(_str)

    return file_name_new_path