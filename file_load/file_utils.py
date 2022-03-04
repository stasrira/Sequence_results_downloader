class StudyConfig:
    config_loc = None
    config_glb = None
    study_logger_name = ''  # 'file_processing_log'
    study_logging_level = ''  # 'INFO'


class FieldIdMethod:
    field_id_methods = ['name', 'number']
    name = field_id_methods[0]
    number = field_id_methods[1]

def setup_common_basic_file_parameters(file_ob):
    replace_blanks_in_header = interpret_cfg_bool_value(file_ob.cfg_file.get_item_by_key('replace_blanks_in_header'))
    if replace_blanks_in_header:
        file_ob.replace_blanks_in_header = replace_blanks_in_header

    replace_single_quotes_in_header = \
        interpret_cfg_bool_value(file_ob.cfg_file.get_item_by_key('replace_single_quotes_in_header'))
    if replace_single_quotes_in_header:
        file_ob.replace_single_quotes_in_header = replace_single_quotes_in_header

    replace_slash_in_header = interpret_cfg_bool_value(file_ob.cfg_file.get_item_by_key('replace_slash_in_header'))
    if replace_slash_in_header:
        file_ob.replace_slash_in_header = replace_slash_in_header

    replace_square_brackets_in_header = \
        interpret_cfg_bool_value(file_ob.cfg_file.get_item_by_key('replace_square_brackets_in_header'))
    if replace_square_brackets_in_header:
        file_ob.replace_square_brackets_in_header = replace_square_brackets_in_header

    # set header_row_number value, if provided in the config
    header_row_num = file_ob.cfg_file.get_item_by_key('header_row_number')
    if header_row_num and header_row_num.isnumeric():
        file_ob.header_row_num = int(header_row_num)

def interpret_cfg_bool_value (value):
    out = None
    if value:
        if isinstance(value, bool):
            out = value
        elif str(value).lower() in ['true', 'yes']:
            out = True
        elif str(value).lower() in ['false', 'no']:
            out = False
    return out