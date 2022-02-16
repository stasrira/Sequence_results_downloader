import yaml
from utils import common as cm
import copy


class ConfigData:

    def __init__(self, cfg_path, cfg_dict = None):
        self.loaded = False

        if cfg_dict is None:
            if cm.file_exists(cfg_path):
                with open(cfg_path, 'r') as ymlfile:
                    self.cfg = yaml.safe_load(ymlfile)
                # self.prj_wrkdir = os.path.dirname(os.path.abspath(cfg_path))
                self.loaded = True
            else:
                self.cfg = None
                # self.prj_wrkdir = None
        elif isinstance(cfg_dict, dict):
            self.cfg = cfg_dict
            self.loaded = True
        else:
            self.cfg = None

    def get_value(self, yaml_path, delim='/'):
        path_elems = yaml_path.split(delim)

        # loop through the path to get the required key
        val = self.cfg
        for el in path_elems:
            # make sure "val" is not None and continue checking if "el" is part of "val"
            if val and el in val:
                try:
                    val = val[el]
                except Exception:
                    val = None
                    break
            else:
                val = None

        return val

    def get_item_by_key(self, key_name):
        v = self.get_value(key_name)
        if v is not None:
            return str(self.get_value(key_name))
        else:
            return v

    # this will pass the dictionary content by reference
    def get_whole_dictionary(self):
        return self.cfg

    # this will provide a copy of the configuration dictionary to path it by value instead of by reference
    def get_dictionary_copy(self):
        return copy.deepcopy(self.cfg)

    # this will update the current configuration dictionary with the values from a given dictionary
    # it is used for loading values of local dictionaries into the main dictionary common for all locations
    def update (self, dictionary):
        if isinstance(dictionary, dict):
            self.cfg.update(dictionary)