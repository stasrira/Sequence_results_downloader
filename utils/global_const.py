# ========== config file names
# main config file name
CONFIG_FILE_MAIN = 'configs/main_config.yaml'
CONFIG_FILE_LOCATION = 'configs/location_config.yaml'
CONFIG_FILE_DICTIONARY = 'configs/dict_config.yaml'
CONFIG_FILE_DICTIONARY_PROGRAM = 'configs/programs/{program}/dict_program_config.yaml'
CONFIG_FILE_SOURCE_PATH = 'configs/download_sources/{source_id}/default/source_config.yaml'
CONFIG_FILE_SOURCE_LOCATION_PATH = 'configs/download_sources/{source_id}/source_location_config.yaml'
CONFIG_CUSTOM_SOFT_MATCH = None

# default values of flags affecting replacing special characters in field's headers
DEFAULT_REPLACE_BLANKS_IN_HEADER = True
DEFAULT_REPLACE_SINGLE_QUOTES_IN_HEADER = True
DEFAULT_REPLACE_SLASH_IN_HEADER = False
DEFAULT_REPLACE_SQUARE_BRACKETS_IN_HEADER = True

UNZIP_DOWNLOAD = False

# name for the each type of log
MAIN_LOG_NAME = 'main_log'
INQUIRY_LOG_NAME = 'inquiry_processing_log'

# default folder names for logs and processed files
# following variables will be defined at the start of execution based on the config values from main_config.yaml
APP_LOG_DIR = ''  # path to the folder where all application level log files will be stored (one file per run)
INQUIRY_LOG_DIR = ''  # path to the folder where all log files for processing inquiry files will be stored
                          # (one file per inquiry)
INQUIRY_PROCESSED_DIR = ''  # path to the folder where all processed (and renamed) inquiries will be stored
DISQUALIFIED_INQUIRIES = '' # path to dir with dynamically created inquiry files for disqualified aliquots
OUTPUT_REQUESTS_DIR = ''  # path to the folder where all processed (and renamed) inquiries will be stored

DATA_DOWNLOADER_PATH = '' # path to the location of Data Downloader app, set based on the main config value

# name of the sheet name in the inquiry file (excel file) where from data should be retrieved.
# If omitted, the first sheet in array of sheets will be used
INQUIRY_EXCEL_WK_SHEET_NAME = ''  # 'Submission_Request'

ASSAY_CHARS_TO_REPLACE = [' ', '/', '\\']

PROCESSED_FOLDER_MAX_FILE_COPIES = -1  # reflects number of copies allowed in addition to the file itself,
                                        # i.e. 'abc.xlsx' and its copies 'abc(1).xlsx', etc.,
                                        # negative value stands for no limit of copies,
                                        # this value can be overwritten by the Location/processed_file_copies_max_number
                                        # parameter from the main config
PROCESSED_ADD_DATESTAMP = True  # this default value will be used if it is not explicitly set in the locations config
