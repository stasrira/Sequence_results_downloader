from pathlib import Path
import os
import time
import xlrd
from utils import global_const as gc
from utils import common as cm
from utils import setup_logger_common
from utils import ConfigData, DictConfigData
from file_load import File  # , MetaFileExcel
from app_error import InquiryError
# from data_retrieval import DataSource, DBAccess
# import xlwt
import copy


class Inquiry(File):

    def __init__(self, filepath, conf_main=None, file_type=2, sheet_name=''):

        # load_configuration (main_cfg_obj) # load global and local configureations

        File.__init__(self, filepath, file_type)

        self.sheet_name = sheet_name  # .strip()

        if conf_main:
            self.conf_main = conf_main
        else:
            self.conf_main = ConfigData(gc.CONFIG_FILE_MAIN)

        self.error = InquiryError(self)

        self.log_handler = None
        self.logger = self.setup_logger(self.wrkdir, self.filename)
        self.logger.info('Start working with Sequence Results Download Inquiry file {}'.format(filepath))
        self.inq_match_arr = []  # TODO: check if needed
        self.columns_arr = []
        # self.inq_sources = {}
        # self.inq_line_sources = {}

        # load common for all programs dictionary config
        self.conf_dict = DictConfigData(gc.CONFIG_FILE_DICTIONARY)
        if not self.conf_dict.loaded:
            # disqualify the current inquiry file
            _str = 'Aborting processing of the inquiry file - the following common dictionary config file cannot ' \
                   'be loaded: {}.'.format(gc.CONFIG_FILE_MAIN)
            self.error.add_error(_str)
            self.logger.error(_str)
            return

        # save inquiry file structure into a dedicated variables
        self.file_structure_by_col_num = self.conf_dict.get_inqury_file_structure('by_col_num')
        self.file_structure_by_col_name = self.conf_dict.get_inqury_file_structure('by_col_name')

        self.processed_folder = gc.INQUIRY_PROCESSED_DIR
        # if a relative path provided, convert it to the absolute address based on the application working dir
        if not os.path.isabs(self.processed_folder):
            self.processed_folder = Path(self.wrkdir) / self.processed_folder
        else:
            self.processed_folder = Path(self.processed_folder)

        self.download_request_path = None  # TODO: check if needed

        self.disqualified_items = {}
        self.disqualified_inquiry_path = ''  # will store path to a inquiry file with disqualified sub-aliquots

        if not self.sheet_name or len(self.sheet_name) == 0:
            # if sheet name was not passed as a parameter, try to get it from config file
            self.sheet_name = gc.INQUIRY_EXCEL_WK_SHEET_NAME  # 'wk_sheet_name'
        # print (self.sheet_name)
        self.logger.info('Data will be loaded from worksheet: "{}"'.format(self.sheet_name))

        self.conf_process_entity = None  # TODO: check if needed

        # self.db_access = DBAccess(self.logger, self.conf_main, self.error)   # TODO: check if needed

        self.get_file_content()

    def get_file_content(self):
        if not self.columns_arr or not self.lines_arr:
            self.columns_arr = []
            self.lines_arr = []
            if cm.file_exists(self.filepath):
                self.logger.debug('Loading file content of "{}"'.format(self.filepath))

                with xlrd.open_workbook(self.filepath) as wb:
                    if not self.sheet_name or len(self.sheet_name) == 0:
                        # by default retrieve the first sheet in the excel file
                        sheet = wb.sheet_by_index(0)
                    else:
                        # if sheet name was provided
                        sheets = wb.sheet_names()  # get list of all sheets
                        if self.sheet_name in sheets:
                            # if given sheet name in the list of available sheets, load the sheet
                            sheet = wb.sheet_by_name(self.sheet_name)
                        else:
                            # report an error if given sheet name not in the list of available sheets
                            _str = ('Given worksheet name "{}" was not found in the file "{}". '
                                    'Verify that the worksheet name exists in the file.').format(
                                self.sheet_name, self.filepath)
                            self.error.add_error(_str)
                            self.logger.error(_str)

                            self.lines_arr = None
                            self.loaded = False
                            return self.lines_arr

                sheet.cell_value(0, 0)

                lines = []  # will hold content of the inquiry file as an array of arrays (rows)
                columns = []
                for i in range(sheet.ncols):
                    column = []
                    for j in range(sheet.nrows):
                        if i == 0:
                            lines.append([])  # adds an array for each new row in the inquiry file

                        # print(sheet.cell_value(i, j))
                        cell = sheet.cell(j, i)
                        cell_value = cell.value
                        # take care of number and dates received from Excel and converted to float by default
                        if cell.ctype == 2 and int(cell_value) == cell_value:
                            # the key is integer
                            cell_value = str(int(cell_value))
                        elif cell.ctype == 2:
                            # the key is float
                            cell_value = str(cell_value)
                        # convert date back to human readable date format
                        # print ('cell_value = {}'.format(cell_value))
                        if cell.ctype == 3:
                            cell_value_date = xlrd.xldate_as_datetime(cell_value, wb.datemode)
                            cell_value = cell_value_date.strftime("%Y-%m-%directory")
                        column.append(cell_value)  # adds value to the current column array
                        # lines[j].append('"' + cell_value + '"')  # adds value in "csv" format for a current row
                        lines[j].append(cell_value)

                    # self.columns_arr.append(','.join(column))
                    columns.append (column)  # adds a column to a list of columns

                # populate lines_arr and columns_arr properties
                self.lines_arr = lines
                self.columns_arr = columns

                # populate lineList value as required for the base class
                self.lineList = []
                for ln in lines:
                    self.lineList.append(','.join(str(ln)))

                wb.unload_sheet(sheet.name)

                # perform validation of the current inquiry file
                self.validate_inquiry_file()

                if self.error.exist():
                    # report that errors exist
                    self.loaded = False
                    # print(self.error.count)
                    # print(self.error.get_errors_to_str())
                    _str = 'Errors ({}) were identified during validating of the inquiry file. \nError(s): {}'.format(
                        self.error.count, self.error.get_errors_to_str())
                else:
                    self.loaded = True

            else:
                _str = 'Loading content of the file "{}" failed since the file does not appear to exist".'.format(
                    self.filepath)
                self.error.add_error(_str)
                self.logger.error(_str)

                self.columns_arr = None
                self.lines_arr = None
                self.loaded = False
        return self.lineList

    def validate_inquiry_file(self):
        self.logger.info('Start validating the current inquiry file "{}".'.format(self.filepath))
        row_count = 0
        failed_cnt = 0
        # valid_aliquot_flag = self.conf_main.get_value('Validate/aliquot_id_vs_manifest')  # TODO: check if needed
        valid_inquiry_values_flag = self.conf_main.get_value('Validate/inquiry_values_vs_dictionary')
        inquiry_min_number_columns = self.conf_main.get_value('Validate/inquiry_min_number_columns')
        inquiry_validate_number_columns = self.conf_main.get_value('Validate/inquiry_validate_number_columns')
        if not inquiry_min_number_columns or not isinstance(inquiry_min_number_columns, int):
            inquiry_min_number_columns = 5  # set a default value if it is not provided in the config file
        if not inquiry_validate_number_columns or not isinstance(inquiry_validate_number_columns, int):
            inquiry_validate_number_columns = 4  # set a default value if it is not provided in the config file

        for row in self.lines_arr:
            row_count += 1
            if row_count == self.header_row_num:  # 1
                # skip the first column as it is a header
                continue

            # check if inquiry file contain min number of columns
            if len(row) < inquiry_min_number_columns:
                # disqualify the current inquiry file
                _str = 'The current inquiry file has {} columns while {} are expected and will be disqualified.' \
                    .format(len(row), inquiry_min_number_columns)
                self.error.add_error(_str)
                self.logger.error(_str)
                return
            # create a local DictConfigData object and copy there a dictionary object
            conf_dict = DictConfigData(None, self.conf_dict.get_dictionary_copy())

            for i in range(len(row)):
                if i + 1 > inquiry_validate_number_columns:
                    # if number of columns in the inquiry file > expected maximum, exit the loop
                    break

                col_category = conf_dict.get_dict_value(str(i + 1), 'inquiry_file_structure')
                cur_val = str(row[i])

                if col_category in ('download_source', 'destination'):
                    # validate values of specified fields against dictionary with list of expected values
                    if not conf_dict.key_exists_in_dict(cur_val.lower(), col_category):
                        _str = 'Unexpected value "{}" was provided for "{}" (line #{}, column #{})' \
                            .format(cur_val, col_category, row_count, i + 1)
                        self.logger.critical(_str)
                        # disqualify an inquiry file row, if unexpected value was provided
                        self.disqualify_inquiry_item(row_count, _str, row)
                        failed_cnt += 1
                        break
                else:
                    # validate that give fields are not empty
                    if len(cur_val.strip()) == 0:
                        _str = 'Unexpected blank value was provided for "{}" (line #{}, column #{})' \
                            .format(col_category, row_count, i + 1)
                        self.logger.critical(_str)
                        # disqualify an inquiry file row, if unexpected value was provided
                        self.disqualify_inquiry_item(row_count, _str, row)
                        failed_cnt += 1
                        break

            # row_count +=1

        self.logger.info('Finish validating the inquiry file with{}.'
                         .format(' no errors'
                                    if failed_cnt == 0
                                    else ' errors; {} records were disqualified - see earlier log entries for details'
                                 .format(failed_cnt)
                                 ))

    def setup_logger(self, wrkdir, filename):

        # m_cfg = ConfigData(gc.CONFIG_FILE_MAIN)

        log_folder_name = gc.INQUIRY_LOG_DIR  # gc.LOG_FOLDER_NAME

        # m_logger_name = gc.MAIN_LOG_NAME
        # m_logger = logging.getLogger(m_logger_name)

        logger_name = gc.INQUIRY_LOG_NAME
        logging_level = self.conf_main.get_value('Logging/inquiry_log_level')

        # if a relative path provided, convert it to the absolute address based on the application working dir
        if not os.path.isabs(log_folder_name):
            log_folder_path = Path(wrkdir) / log_folder_name
        else:
            log_folder_path = Path(log_folder_name)

        lg = setup_logger_common(logger_name, logging_level,
                                 log_folder_path,  # Path(wrkdir) / log_folder_name,
                                 str(filename) + '_' + time.strftime("%Y%m%d_%H%M%S", time.localtime()) + '.log')

        self.log_handler = lg['handler']
        return lg['logger']

    def get_inquiry_value_by_field_name(self, field_name, inq_line, validate_by_dictionary = None):
        if validate_by_dictionary is None:
            validate_by_dictionary = True  # set default value to True

        if field_name in self.file_structure_by_col_name:
            col_num = self.file_structure_by_col_name[field_name]
            value = inq_line[col_num - 1].strip()
        else:
            value = ''
        # validate the provided program code through the dictionary
        if validate_by_dictionary:
            value = self.conf_dict.get_dict_value(str(value).lower(), field_name)
        return value

    # def process_inquiry_sources(self):
    #     cur_row = 0
    #     for inq_line in self.lines_arr:
    #         if cur_row == self.header_row_num - 1:
    #             # skip the header row
    #             cur_row += 1
    #             continue
    #
    #         # get program code assigned to the current row
    #         program_code = self.get_inquiry_value_by_field_name('program_code', inq_line)
    #         # get assay assigned to the current row
    #         assay = self.get_inquiry_value_by_field_name('assay', inq_line)
    #         # get source id assigned to the current row
    #         source_id = self.get_inquiry_value_by_field_name('source_id', inq_line)
    #
    #         # get source config file
    #         # 2 values are saved in tuple: program name specific path and default one.
    #         # if program name specific path does not exist, the default will be used
    #         cfg_source_path = (
    #             # configuration path for the current program by name
    #             gc.CONFIG_FILE_SOURCE_PATH\
    #                 .replace('{program}', program_code)\
    #                 .replace('{assay}', assay)\
    #                 .replace('{source_id}', source_id),
    #             # configuration path for the default program (used if no program specific path is present)
    #             gc.CONFIG_FILE_SOURCE_PATH \
    #                 .replace('{program}', 'default') \
    #                 .replace('{assay}', assay) \
    #                 .replace('{source_id}', source_id)
    #         )
    #         # get the source location config file path
    #         cfg_source_location_path = gc.CONFIG_FILE_SOURCE_LOCATION_PATH.replace('{source_id}', source_id)
    #
    #         # attempt to load configuration for the program specific path
    #         cfg_source = ConfigData(Path(cfg_source_path[0]))
    #         if not cfg_source.loaded:
    #             # if config was not loaded from the program specific path, load the default one
    #             cfg_source = ConfigData(Path(cfg_source_path[1]))
    #
    #         if cfg_source.loaded:
    #             # proceed here if the source config was loaded
    #             # load source location config with location specific settings for the current source
    #             cfg_source_location = ConfigData(Path(cfg_source_location_path))
    #             if cfg_source_location.loaded:
    #                 # if the source location config was loaded, update cfg_source config with the source location config
    #                 cfg_source.update(cfg_source_location.get_whole_dictionary())
    #
    #             # get unique id of the datasource and check if the same id was used already, reuse that in such case
    #             inq_line_datasource_id = self.get_inquiry_line_datasource_id(inq_line)
    #             self.logger.info('Current inquiry row #{} was identified with the following data source id: {}'
    #                              .format (cur_row, inq_line_datasource_id))
    #             # assign source id (inq_line_datasource_id) to the current inquiry line
    #             self.inq_line_sources[cur_row] = inq_line_datasource_id
    #             if inq_line_datasource_id in self.inq_sources:
    #                 # reuse existing datasource
    #                 self.logger.info('Identified data source id for the current inquiry row #{} was identified as '
    #                                  'already retrieved for one the earlier rows and will be re-used for '
    #                                  'the current row.'.format(cur_row))
    #             else:
    #                 # create a new datasource object
    #                 inq_line_datasource = DataSource(self, cfg_source, inq_line, inq_line_datasource_id)
    #                 self.inq_sources[inq_line_datasource_id] = inq_line_datasource
    #         else:
    #             sub_al = self.get_inquiry_value_by_field_name('sub-aliquot', inq_line, False)
    #             _str = 'Datasource config file for the row #{} (sub_aliquot: {}) cannot be loaded. ' \
    #                    'None of the expected to exist files is accessable: {}'\
    #                 .format(cur_row, sub_al, ' | '.join(cfg_source_path))
    #             self.logger.warning(_str)
    #             self.disqualify_inquiry_item(sub_al, _str, cur_row)
    #         cur_row += 1
    #
    #         # sources = self.conf_process_entity.get_value('sources')
    #     pass

    def process_inquiry(self):
        # self.conf_process_entity = self.load_source_config()
        #
        # #  self.data_source_locations = self.conf_process_entity.get_value('Datasource/locations')
        # self.process_inquiry_sources()
        # self.match_inquiry_items_to_sources()
        # self.create_download_request_file()
        self.create_inquiry_file_for_disqualified_entries()

        # check for errors and put final log entry for the inquiry.
        if self.error.exist():
            _str = 'Processing of the current inquiry was finished with the following errors: {}\n'.format(
                self.error.get_errors_to_str())
            self.logger.error(_str)
        else:
            _str = 'Processing of the current inquiry was finished successfully.\n'
            self.logger.info(_str)

    def disqualify_inquiry_item(self, id, disqualify_status, inquiry_item):
        # adds a sub aliquots to the dictionary of disqualified items
        # key = sub-aliquot, values: dictionary with 2 values:
        #       'status' - reason for disqualification
        #       'inquiry_item: array of values for inquiry row from an inquiry file
        details = {'status': disqualify_status, 'inquiry_item':inquiry_item}
        if not id in self.disqualified_items:
            self.disqualified_items[id]= details
            self.logger.warning('Row #{} was disqualified with the following status: "{}"'
                                .format(id, disqualify_status))
        else:
            self.logger.warning('Row #{} was already disqualified earlier. '
                                'The following disqualification call will be ignored: "{}"'
                                .format(id, disqualify_status))

    def create_inquiry_file_for_disqualified_entries(self):
        if self.disqualified_items:
            self.logger.info("Start preparing inquiry file for disqualified sub-aliquots.")
            # path for the script file being created

            wb = xlwt.Workbook()  # create empty workbook object
            sh = wb.add_sheet('Re-process_inquiry')  # sheet name can not be longer than 32 characters

            cur_row = 0  # first row for 0-based array
            cur_col = 0  # first col for 0-based array
            # write headers to the file
            headers = self.lines_arr[0]
            for val in headers:
                sh.write(cur_row, cur_col, val)
                cur_col += 1

            cur_row += 1

            for di in self.disqualified_items:
                fields = self.disqualified_items[di]['inquiry_item']
                cur_col = 0
                for val in fields:
                    sh.write(cur_row, cur_col, val)
                    cur_col += 1
                cur_row += 1

            if not os.path.isabs(gc.DISQUALIFIED_INQUIRIES):
                disq_dir = Path(self.wrkdir) / gc.DISQUALIFIED_INQUIRIES
            else:
                disq_dir = Path(gc.DISQUALIFIED_INQUIRIES)

            # if DISQUALIFIED_INQUIRIES folder does not exist, it will be created
            os.makedirs(disq_dir, exist_ok=True)

            # identify path for the disqualified inquiry file
            self.disqualified_inquiry_path = Path(str(disq_dir) + '/' +
                                                  time.strftime("%Y%m%d_%H%M%S", time.localtime()) +
                                                  '_reprocess_disqualified_' +
                                                # .stem method is used to get file name without an extension
                                                  Path(self.filename).stem.replace(' ', '') + '.xls')

            wb.save(str(self.disqualified_inquiry_path))

            self.logger.info("Successfully prepared the inquiry file for disqualified sub-aliquots and saved in '{}'."
                             .format(str(self.disqualified_inquiry_path)))
