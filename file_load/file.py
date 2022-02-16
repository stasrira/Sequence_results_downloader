import os
import time
from pathlib import Path
import logging
from app_error import FileError
from utils.log_utils import setup_logger_common, deactivate_logger_common
from utils import global_const as gc
from .file_utils import StudyConfig
from csv import reader
import re


#  Text file class (used as a base)
class File:

    def __init__(self, filepath, file_type=1, file_delim=',',
                 replace_blanks_in_header = None,
                 replace_single_quotes_in_header=None,
                 replace_slash_in_header = None,
                 replace_square_brackets_in_header = None):
        if not replace_blanks_in_header:
            replace_blanks_in_header = gc.DEFAULT_REPLACE_BLANKS_IN_HEADER
        if not replace_single_quotes_in_header:
            replace_single_quotes_in_header = gc.DEFAULT_REPLACE_SINGLE_QUOTES_IN_HEADER
        if not replace_slash_in_header:
            replace_slash_in_header = gc.DEFAULT_REPLACE_SLASH_IN_HEADER
        if not replace_square_brackets_in_header:
            replace_square_brackets_in_header = gc.DEFAULT_REPLACE_SQUARE_BRACKETS_IN_HEADER

        self.filepath = filepath
        self.wrkdir = os.path.dirname(os.path.abspath(filepath))
        self.filename = Path(os.path.abspath(filepath)).name
        self.file_type = file_type
        self.file_delim = file_delim
        self.error = FileError(self)
        self.lineList = []
        self.__headers = []
        self.sample_id_field_names = []
        self.loaded = False
        self.header_row_num = 1  # default header row number
        self.replace_blanks_in_header = replace_blanks_in_header
        self.replace_single_quotes_in_header = replace_single_quotes_in_header
        self.replace_slash_in_header = replace_slash_in_header
        self.replace_square_brackets_in_header = replace_square_brackets_in_header
        self.logger = None
        self.log_handler = None

    # @property
    def headers(self):
        if not self.__headers:
            self.get_headers()
        return self.__headers

    def setup_logger(self, wrkdir, filename):

        log_folder_name = gc.LOG_FOLDER_NAME

        lg = setup_logger_common(StudyConfig.study_logger_name, StudyConfig.study_logging_level,
                                 Path(wrkdir) / log_folder_name,
                                 filename + '_' + time.strftime("%Y%m%d_%H%M%S", time.localtime()) + '.log')

        self.log_handler = lg['handler']
        return lg['logger']

    def get_file_content(self):
        if not self.logger:
            loc_log = logging.getLogger(StudyConfig.study_logger_name)
        else:
            loc_log = self.logger

        if not self.lineList:
            if self.file_exists(self.filepath):
                loc_log.debug('Loading file content of "{}"'.format(self.filepath))
                with open(self.filepath, "r") as fl:
                    self.lineList = []
                    for line in fl:
                        ln1 = reader([line.rstrip('\n')], delimiter=self.file_delim, skipinitialspace=True)
                        for field_list in reader([line.rstrip('\n')], delimiter=self.file_delim, skipinitialspace=True):
                            # print ([field.lstrip('ï»¿') for field in field_list])
                            # remove BOF characters that are added for the UTF-8 files; see here:
                            # https://stackoverflow.com/questions/24568056/rs-read-csv-prepending-1st-column-name-with-junk-text/24568505
                            field_list = [field.lstrip('ï»¿') for field in field_list]
                            self.lineList.append(field_list)
                        # self.lineList.append(list(reader([line.rstrip('\n')], delimiter=self.file_delim, skipinitialspace=True)))

                    fl.close()
                    self.loaded = True
            else:
                _str = 'Loading content of the file "{}" failed since the file does not appear to exist or cannot be ' \
                       'opened due to lack of permissions or password protection".'.format(self.filepath)
                self.error.add_error(_str)
                loc_log.error(_str)
                self.lineList = None
                self.loaded = False
        return self.lineList

    def file_exists(self, fn):
        try:
            with open(fn, "r"):
                return 1
        except IOError:
            return 0
    """
    def get_headers(self):
        if not self.__headers:
            hdrs = self.get_row_by_number(1).split(self.file_delim)
            self.__headers = [hdr.strip().replace(' ', '_') for hdr in hdrs]
        return self.__headers
    """

    def get_headers(self):
        if not self.__headers:
            hdrs = self.get_row_by_number_to_list(self.header_row_num)

            if self.replace_blanks_in_header:
                hdrs = [hdr.strip().replace(' ', '_') for hdr in hdrs]

            if self.replace_single_quotes_in_header:
                hdrs = [hdr.strip().replace('\'', '_') for hdr in hdrs]

            if self.replace_slash_in_header:
                hdrs = [hdr.strip().replace('\\', '_') for hdr in hdrs]
                hdrs = [hdr.strip().replace('/', '_') for hdr in hdrs]

            if self.replace_square_brackets_in_header:
                hdrs = [hdr.strip().replace('[', '_') for hdr in hdrs]
                hdrs = [hdr.strip().replace(']', '_') for hdr in hdrs]

            # check if 3 or more repeating replacement characters (_) are present and replace those with a single _
            hdrs = [re.sub('___+', '_', hdr) for hdr in hdrs]

            self.__headers = hdrs

        return self.__headers

    def get_row_by_number(self, rownum):
        line_list = self.get_file_content()
        # check that requested row is withing available records of the file and >0
        if line_list is not None and len(line_list) >= rownum > 0:
            return line_list[rownum - 1]
        else:
            return []

    def get_row_by_number_to_list(self, rownum):
        # row = self.get_row_by_number(rownum)
        # row_list = list(reader([row], delimiter=self.file_delim, skipinitialspace=True))[0]
        row_list = self.get_row_by_number(rownum)
        return row_list

    def rows_count(self, exclude_header=None):
        # setup default parameters
        if not exclude_header:
            exclude_header = False
        line_list = self.get_file_content()
        if line_list:
            num = len(line_list)
            if exclude_header:
                num = num - 1
        else:
            num = 0
        return num

    def deactivate_logger(self):
        deactivate_logger_common(self.logger, self.log_handler)