import shutil
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
from file_load import file_utils as ft
import xlwt
import traceback
import uuid


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
        self.inq_processed_items = {}
        self.columns_arr = []

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

                col_category, match_found = conf_dict.get_dict_value(str(i + 1), 'inquiry_file_structure')
                cur_val = str(row[i])

                if col_category in ('download_source', 'destination_name'):
                    # validate values of specified fields against dictionary with list of expected values
                    if not conf_dict.key_exists_in_dict(cur_val.lower(), col_category):
                        _str = 'Unexpected value "{}" was provided for "{}" (line #{}, column #{}). ' \
                               'This entry was disqualified' \
                            .format(cur_val, col_category, row_count, i + 1)
                        # disqualify an inquiry file row, if unexpected value was provided
                        self.disqualify_inquiry_item(row_count, _str, row)
                        self.logger.error(_str)
                        failed_cnt += 1
                        break
                else:
                    # validate that given fields are not empty
                    if len(cur_val.strip()) == 0:
                        _str = 'Unexpected blank value was provided for "{}" (line #{}, column #{}). ' \
                               'This entry was disqualified.' \
                            .format(col_category, row_count, i + 1)
                        # disqualify an inquiry file row, if unexpected value was provided
                        self.disqualify_inquiry_item(row_count, _str, row)
                        self.logger.error(_str)
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
            value = str(inq_line[col_num - 1]).strip()
        else:
            value = ''
        # validate the provided value through the dictionary
        if validate_by_dictionary:
            value_dict, match_found = self.conf_dict.get_dict_value(str(value).lower(), field_name)
            if match_found:
                value = value_dict

        return value

    def process_inquiry(self):
        self.logger.info('Start processing inquiry file\'s rows.')
        cur_row = -1  # rows counter
        for inq_line in self.lines_arr:
            # # set default values for local variables
            # destination_path = None
            # downloaded_file = None
            # downloaded_file_unarchived = None
            # downloaded_file_copied = None
            # temp_file_deleted = None

            cur_row += 1
            if cur_row == self.header_row_num - 1:
                # skip the header row
                continue

            if cur_row + 1 in self.disqualified_items:
                # skip rows that were disqualified
                self.logger.info('Row #{} was skipped as disqualified'.format(cur_row + 1))
                continue

            inquiry_line_details = {
                # get download source assigned to the current row
                'dld_src': self.get_inquiry_value_by_field_name('download_source', inq_line),
                # get download source url/path assigned to the current row
                'dld_src_url': self.get_inquiry_value_by_field_name('url', inq_line, False),
                # get destination name assigned to the current row
                'dest_name': self.get_inquiry_value_by_field_name('destination_name', inq_line),
                # get destination directory path assigned to the current row
                'dest_path': self.get_inquiry_value_by_field_name('destination_dir_path', inq_line, False),
                # get unarchive_downloaded flag assigned to the current row
                'unarchive': self.get_inquiry_value_by_field_name('unarchive_downloaded', inq_line, False)
            }

            # get the source config file path
            cfg_source_path = gc.CONFIG_FILE_SOURCE_PATH.replace('{source_id}', inquiry_line_details['dld_src'])
            # get the source location config file path
            cfg_source_location_path = gc.CONFIG_FILE_SOURCE_LOCATION_PATH.replace('{source_id}', inquiry_line_details['dld_src'])
            # load configuration for the source
            cfg_source = ConfigData(Path(cfg_source_path))

            cfg_destination_path = gc.CONFIG_FILE_DESTINATION.replace('{destination_id}', inquiry_line_details['dest_name'])
            # get the destination location config file path
            cfg_destination_location_path = gc.CONFIG_FILE_DESTINATION_LOCATION_PATH\
                .replace('{destination_id}', inquiry_line_details['dest_name'])
            # load configuration for the destination
            cfg_destination = ConfigData(Path(cfg_destination_path))
            # cfg_destination = ConfigData(Path(cfg_destination_location_path))

            # validate that source config was loaded
            if not cfg_source.loaded:
                _str = 'Datasource config file for the row #{} (source: {}) cannot be loaded ' \
                       'and the row was disqualified. ' \
                       'The expected to exist file is not accessible: {}' \
                    .format(cur_row + 1, inquiry_line_details['dld_src'], cfg_source_path)
                self.disqualify_inquiry_item(cur_row, _str, inq_line)
                self.logger.warning(_str)
                continue

            # validate that destination config was loaded
            if not cfg_destination.loaded:
                _str = 'Destination config file for the row #{} (destination: {}) cannot be loaded ' \
                       'and the row was disqualified. ' \
                       'The expected to exist file is not accessible: {}' \
                    .format(cur_row + 1, inquiry_line_details['dest_name'], cfg_destination_path)
                self.disqualify_inquiry_item(cur_row, _str, inq_line)
                self.logger.warning(_str)
                continue

            if cfg_source.loaded:
                # load source location config with location specific settings for the current source
                cfg_source_location = ConfigData(Path(cfg_source_location_path))
                if cfg_source_location.loaded:
                    # if the source location config was loaded, update cfg_source config with the source location config
                    cfg_source.update(cfg_source_location.get_whole_dictionary())

            if cfg_destination.loaded:
                # load destination location config with location specific settings for the current source
                cfg_destination_location = ConfigData(Path(cfg_destination_location_path))
                if cfg_destination_location.loaded:
                    # if the source location config was loaded, update cfg_source config with the source location config
                    cfg_destination.update(cfg_destination_location.get_whole_dictionary())

            if cfg_source.loaded and cfg_destination.loaded:
                if inquiry_line_details['dld_src'] and inquiry_line_details['dld_src'].lower() == 'googledrive':

                    self.process_google_drive_inquiry(inquiry_line_details, cfg_source, cfg_destination,
                                                      cur_row, inq_line)
                # this checks if the current source is listed in the "local_network_sources" section of the dictionary
                elif inquiry_line_details['dld_src'] \
                        and self.conf_dict.get_dict_value (inquiry_line_details['dld_src'].lower(), 'local_network_sources')[1]:
                    self.process_local_network_inquiry(inquiry_line_details, cfg_source, cfg_destination,
                                                      cur_row, inq_line)
                else:
                    _str = 'Unexpected Download Source "{}" was provided for the row #{}; ' \
                           'the row was disqualified. ' \
                        .format(inquiry_line_details['dld_src'], cur_row + 1)
                    self.disqualify_inquiry_item(cur_row, _str, inq_line)
                    self.logger.warning(_str)
                    continue

        # if some inquiry rows were disqualified, create a file to re-process them
        self.create_inquiry_file_for_disqualified_entries()

        # check for errors and put final log entry for the inquiry.
        if self.error.exist():
            _str = 'Processing of the current inquiry was finished with the following errors: {}\n'.format(
                self.error.get_errors_to_str())
            self.logger.error(_str)
        else:
            _str = 'Processing of the current inquiry was finished successfully.\n'
            self.logger.info(_str)

    # processes inquiries that are qualified as the local network ones
    def process_local_network_inquiry(self, inquiry_line_details, cfg_source, cfg_destination, cur_row, inq_line):
        download_completed = False

        if cfg_destination:  # make sure destination config is loaded
            # prepare the source path of the downloaded data
            source_replace_path = cfg_source.get_value('Location/path_to_replace')
            source_mountpoint_path = cfg_source.get_value('Location/path_local_mountpoint')
            # apply local mount point settings to the destination path
            source_path = \
                str(Path(inquiry_line_details['dld_src_url'].replace(source_replace_path, source_mountpoint_path)))

            # prepare the destination path for the downloaded file
            dest_replace_path = cfg_destination.get_value('Location/path_to_replace')
            dest_mountpoint_path = cfg_destination.get_value('Location/path_local_mountpoint')
            # apply local mount point settings to the destination path
            destination_path = \
                str(Path(inquiry_line_details['dest_path'].replace(dest_replace_path, dest_mountpoint_path)))

            # get config value for dest_unique_dir flag
            dest_unique_dir = cfg_destination.get_value(
                'data_structure/save_in_unique_datetimestamp_dir')
            if dest_unique_dir:
                # modify destination path by adding datetime stamp folder to it
                destination_path = cm.get_unique_dir_name_with_datestamp(destination_path, source_path)

            if os.path.exists(source_path):
                if os.path.isdir(source_path):
                    # copy source directory to the destination
                    copy_out = cm.copy_dir(source_path, destination_path)
                    if not copy_out:
                        # no errors were reported during copying
                        download_completed = True
                        self.logger.info(
                            'Successfully copied the source content from {} to {}'
                                .format(source_path, destination_path))
                    else:
                        self.disqualify_inquiry_item(cur_row + 1, copy_out, inq_line)
                        self.logger.error('The following errors were reported during copying of '
                                          'the source content and the row #{} was disqualified. '
                                          'Source: {}; destination: {}'
                                          .format(cur_row + 1, copy_out,
                                                  source_path, destination_path))
                else:
                    # copy source file to the destination
                    download_completed = \
                        self.copy_donwloaded_file_to_destination(source_path, destination_path,
                                                                 cur_row, inq_line)

                processed_row_details = {
                    # 'row_num': cur_row + 1,
                    'dld_src': inquiry_line_details['dld_src'],
                    'dld_src_url': '{} (actual path:{})'.format(inquiry_line_details['dld_src_url'],source_path),
                    'dest_name': inquiry_line_details['dest_name'],
                    # 'dest_path': destination_path,
                    'unarchive': 'N/A',
                    'downloaded_file': 'N/A',
                    'destination_path': '{} --> actual path: {}'.format(inquiry_line_details['dest_path'],destination_path),
                    'downloaded_file_unarchived': 'N/A',
                    'downloaded_file_copied': download_completed,
                    'temp_file_deleted': 'N/A',
                    # 'disqualified': True if (cur_row + 1) in self.disqualified_items else False
                }
                self.inq_processed_items[cur_row + 1] = processed_row_details
            else:
                _str = 'Expected to exist source data at the following path was not present: {}'.format(source_path)
                self.disqualify_inquiry_item(cur_row + 1, _str, inq_line)
                self.logger.error('Row #{} was disqualified due to the following error - {}'
                                  .format(cur_row + 1, _str))
        pass

    # processes inquiries with the Google Drive source
    def process_google_drive_inquiry(self, inquiry_line_details, cfg_source, cfg_destination, cur_row, inq_line):
        # set default values for local variables
        destination_path = None
        downloaded_file = None
        downloaded_file_unarchived = None
        downloaded_file_copied = None
        temp_file_deleted = None

        # get temp directory where to save the received file
        dest_temp_dir = str(Path(cfg_source.get_value('Location/temp_dir')) / uuid.uuid4().hex)
        dest_temp_dir_unarchive = str(Path(dest_temp_dir) / uuid.uuid4().hex)
        # get file_id index position (in the google drive share link) if applicable
        file_id_index = cfg_source.get_value('url/file_id_index')
        # get flag defining if the temp files can be deleted after use
        delete_temp_file = ft.interpret_cfg_bool_value(cfg_source.get_value('temp_file/delete_after_use'))

        self.logger.info('Starting downloading. URL: {} | Destination: {}'
                         .format(inquiry_line_details['dld_src_url'], dest_temp_dir))

        # proceed with the actual downloading of the file from google drive
        downloaded_file, download_error = cm.gdown_get_file(
            inquiry_line_details['dld_src_url'], dest_temp_dir, file_id_index, self.logger)

        if download_error is None:
            self.logger.info('Downloading attempt was finished without errors. Downloaded file name: {}'
                             .format(downloaded_file))
            if downloaded_file:
                if cfg_destination:  # make sure destination config is loaded
                    # prepare the destination path for the downloaded file
                    dest_replace_path = cfg_destination.get_value('Location/path_to_replace')
                    dest_mountpoint_path = cfg_destination.get_value('Location/path_local_mountpoint')
                    # apply local mount point settings to the destination path
                    destination_path = \
                        str(Path(inquiry_line_details['dest_path'].replace(dest_replace_path, dest_mountpoint_path)))

                    # get config value for dest_unique_dir flag
                    dest_unique_dir = cfg_destination.get_value(
                        'data_structure/save_in_unique_datetimestamp_dir')
                    if dest_unique_dir:
                        # modify destination path by adding datetime stamp folder to it
                        destination_path = cm.get_unique_dir_name_with_datestamp(
                            destination_path, downloaded_file)

                    if ft.interpret_cfg_bool_value(inquiry_line_details['unarchive']):
                        # proceed here with un-archiving of the downloaded file
                        self.logger.info('Starting an un-archiving of the downloaded file.')

                        downloaded_file_unarchived = False
                        # verify the archive type
                        if downloaded_file.endswith(('zip', 'rar', 'tar', 'bzip2', 'gzip')):
                            # proceed here with supported files
                            self.logger.info('The downloaded file was recognized as a supported archive.')
                            arc_out = cm.unarchive(downloaded_file, dest_temp_dir_unarchive)
                            if not arc_out:
                                # no error reported during unzipping
                                self.logger.info('Un-archiving of the downloaded file to the following '
                                                 'temp location was successful: {}'
                                                 .format(dest_temp_dir_unarchive))

                                # copy un-archived content to the destination
                                copy_out = cm.copy_dir(dest_temp_dir_unarchive, destination_path)
                                if not copy_out:
                                    # no errors were reported during copying
                                    self.logger.info(
                                        'Successfully copied the un-archived content from {} to {}'
                                            .format(dest_temp_dir_unarchive, destination_path))
                                else:
                                    self.disqualify_inquiry_item(cur_row + 1, copy_out, inq_line)
                                    self.logger.error('The following errors were reported during copying of '
                                                      'un-archived content and the row #{} was disqualified. '
                                                      'Source dir: {}; destination dir: {}'
                                                      .format(cur_row + 1, copy_out,
                                                              dest_temp_dir_unarchive, destination_path))
                                downloaded_file_unarchived = True
                            else:
                                self.disqualify_inquiry_item(cur_row + 1, arc_out, inq_line)
                                self.logger.error('The following errors were reported during un-archiving '
                                                  'and the row #{} was disqualified: {}'
                                                  .format(cur_row + 1, arc_out))
                        else:
                            # provided format is not supported
                            _str = 'Archive format of the downloaded file is not supported - cannot ' \
                                   'perform un-archiving (as per config setting). The downloaded file ' \
                                   'will be copied instead.'
                            self.logger.warning(_str)
                            # since un-archiving cannot be performed, move the downloaded file to destination
                            downloaded_file_copied = \
                                self.copy_donwloaded_file_to_destination(downloaded_file, destination_path,
                                                                         cur_row, inq_line)
                        pass
                    else:
                        # proceed here with copying the file to the destination location
                        downloaded_file_copied = \
                            self.copy_donwloaded_file_to_destination(downloaded_file, destination_path,
                                                                     cur_row, inq_line)

                # based on the config settings, delete the temp file after it was used
                if delete_temp_file:
                    if cm.file_exists(dest_temp_dir):
                        try:
                            shutil.rmtree(dest_temp_dir)
                            self.logger.info('Downloaded file (with its temp directory) was deleted: {}'
                                             .format(dest_temp_dir))
                        except Exception as ex:
                            # report unexpected error during deleting the temp file
                            _str = 'Unexpected Error occurred (row #{}) during an attempt to delete the temp file {}: {}\n{} ' \
                                .format(cur_row + 1, downloaded_file, ex, traceback.format_exc())
                            self.logger.error(_str)

                    # verify that the file was actually delete and set the flag appropriately
                    if not cm.file_exists(downloaded_file):
                        temp_file_deleted = True
                    else:
                        temp_file_deleted = False

                processed_row_details = {
                    # 'row_num': cur_row + 1,
                    'dld_src': inquiry_line_details['dld_src'],
                    'dld_src_url': inquiry_line_details['dld_src_url'],
                    'dest_name': inquiry_line_details['dest_name'],
                    # 'dest_path': inquiry_line_details['dest_path'],
                    'unarchive': inquiry_line_details['unarchive'],
                    'downloaded_file': downloaded_file,
                    'destination_path': '{} --> actual path: {}'.format(inquiry_line_details['dest_path'],destination_path),
                    'downloaded_file_unarchived': downloaded_file_unarchived,
                    'downloaded_file_copied': downloaded_file_copied,
                    'temp_file_deleted': temp_file_deleted,
                    # 'disqualified': True if (cur_row + 1) in self.disqualified_items else False
                }
                self.inq_processed_items[cur_row + 1] = processed_row_details
            else:
                _str = 'Unexpectedly the path for the downloaded file was not received from the "gdown" ' \
                       'module, while no other errors were reported.'
                self.disqualify_inquiry_item(cur_row + 1, _str, inq_line)
                self.logger.error(_str)

        else:
            self.logger.warning('Downloading attempt was finished with errors')
            self.logger.error(download_error)
            # self.error.add_error(download_error)
            self.disqualify_inquiry_item(cur_row + 1, download_error, inq_line)

    def copy_donwloaded_file_to_destination(self, downloaded_file, destination_path, cur_row, inq_line):
        dld_file_name = Path(downloaded_file).name
        dest_file_path = str(Path(destination_path) / dld_file_name)
        move_out = None
        move_out = cm.move_file(downloaded_file, dest_file_path)
        if move_out is None:
            self.logger.info('The data/downloaded file: {} was moved to: {}'
                             .format(downloaded_file, dest_file_path))
            return True
        else:
            _str = 'An error was produced during moving the data/downloaded file and the row #{} ' \
                   'was disqualified. Source: {}; destination to: {}. \n Error: {}' \
                .format(cur_row + 1, downloaded_file, dest_file_path, move_out)
            self.disqualify_inquiry_item(cur_row + 1, _str, inq_line)
            self.logger.error(_str)
            return False

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
            # os.makedirs(disq_dir, exist_ok=True)
            cm.verify_and_create_dir(disq_dir)

            # identify path for the disqualified inquiry file
            self.disqualified_inquiry_path = Path(str(disq_dir) + '/' +
                                                  time.strftime("%Y%m%d_%H%M%S", time.localtime()) +
                                                  '_reprocess_disqualified_' +
                                                # .stem method is used to get file name without an extension
                                                  Path(self.filename).stem.replace(' ', '') + '.xls')

            wb.save(str(self.disqualified_inquiry_path))

            self.logger.info("Successfully prepared the inquiry file for disqualified sub-aliquots and saved in '{}'."
                             .format(str(self.disqualified_inquiry_path)))
