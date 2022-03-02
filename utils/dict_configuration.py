from utils import ConfigData
from utils import common as cm, global_const as gc

class DictConfigData (ConfigData):
    def __init__(self, cfg_path, cfg_dict = None):
        ConfigData.__init__(self, cfg_path, cfg_dict)

    def convert_sub_aliq_to_aliquot(self, sa, assay):
        aliquot = sa
        assay_postfixes = self.get_value('assay_sub_aliquot_postfix/' + assay)  # get_item_by_key
        if assay_postfixes is not None:
            for assay_postfix in assay_postfixes:
                apf_len = len(assay_postfix)
                if sa[-apf_len:] == assay_postfix:
                    aliquot = sa[:len(sa) - apf_len]
                    break  # exit loop if a match was found
        return aliquot

    # get value for the given key from dict_config.yaml file
    def get_dict_value(self, key, section):
        # replace spaces and slashes with "_"
        key = cm.replace_unacceptable_chars(key, gc.ASSAY_CHARS_TO_REPLACE)
        if section and len(section) > 0:
            key_path = section + "/" + key
        else:
            key_path = key
        try:
            v = self.get_item_by_key(key_path)
            if v is not None:
                return v, True
            else:
                return key, False
        except Exception:
            return key, False

    # get value for the given key from dict_config.yaml file
    def get_dict_object(self, key, section):
        # replace spaces and slashes with "_"
        key = cm.replace_unacceptable_chars(key, gc.ASSAY_CHARS_TO_REPLACE)
        if section and len(section) > 0:
            key_path = section + "/" + key
        else:
            key_path = key
        try:
            v = self.get_value(key_path)
            if v is not None:
                return v
            else:
                return key
        except Exception:
            return key

    # checks if provided key exists in dict_config.yaml file
    def key_exists_in_dict(self, key, section):
        key = cm.replace_unacceptable_chars(key, gc.ASSAY_CHARS_TO_REPLACE)
        try:
            v = self.get_item_by_key(section + "/" + key)
            if v is not None:
                return True
            else:
                return False
        except Exception:
            return False

    # expected values for the "type" parameter: 'by_col_name' and 'by_col_num'
    def get_inqury_file_structure(self, type = None):
        inquiry_file_structure_out = {}
        if not type:
            type = 'by_col_name'
        # get file structure from the current dictionary config file
        inquiry_file_structure = self.get_dict_object('inquiry_file_structure', '')
        if type == 'by_col_name':

            for struct_item in inquiry_file_structure:
                inquiry_file_structure_out[inquiry_file_structure[struct_item]] = eval(struct_item)
        if type == 'by_col_num':
            for struct_item in inquiry_file_structure:
                inquiry_file_structure_out[eval(struct_item)] = inquiry_file_structure[struct_item]

        return inquiry_file_structure_out