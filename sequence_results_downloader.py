from dotenv import load_dotenv
import click
from os import walk, path
import os
from pathlib import Path
import time
import sys
import traceback
from utils import setup_logger_common, deactivate_logger_common, common as cm
from utils import ConfigData
from utils import global_const as gc
from utils import send_email as email
from file_load import Inquiry


basedir = path.abspath(path.dirname(__file__))
load_dotenv(path.join(basedir, '.env'))


@click.command()
@click.option("--unzip_download", "-u", default="no",
    help="Provides direction if the downloaded file has to be un-archived (un-zipped). "
         "Expected values: yes, no. If ommitted, the default value is 'no'.",
              )


def check_supplied_arguments(unzip_download):
    # TODO: Verify the need of the unzip_download parameter
    # functions will check if a particular command line arguments were provided
    if unzip_download and unzip_download == 'yes':
        # check if the unzip parameter was set to 'yes' and update global constant variable
        gc.UNZIP_DOWNLOAD = True
    elif unzip_download and unzip_download == 'no':
        # check if the unzip parameter was set to 'no' and update global constant variable
        gc.UNZIP_DOWNLOAD = False
    else:
        # f the unzip parameter was not passed. use default value of gc.UNZIP_DOWNLOAD
        pass
    process_sequence_download_inquiries()


def process_sequence_download_inquiries():
    # load main config file and get required values
    m_cfg = ConfigData(gc.CONFIG_FILE_MAIN)
    if not m_cfg.loaded:
        print('Specified main config file ({}) was not loaded. Aborting execution.'.format(gc.CONFIG_FILE_MAIN))
        return 1

    # load location config file (with local value specific for the location)
    cfg_location = ConfigData(gc.CONFIG_FILE_LOCATION)
    if not cfg_location.loaded:
        print('Specified location config file ({}) was not loaded. Aborting execution.'.format(
            gc.CONFIG_FILE_LOCATION))
        return 1
    # if both configs were loaded, update the main config with the location config
    m_cfg.update(cfg_location.get_whole_dictionary())
    # print ('m_cfg = {}'.format(m_cfg.cfg))
    # assign values
    common_logger_name = gc.MAIN_LOG_NAME  # m_cfg.get_value('Logging/main_log_name')

    # get path configuration values
    logging_level = m_cfg.get_value('Logging/main_log_level')
    # path to the folder where all new inquiry files will be posted
    inquiries_loc = m_cfg.get_value('Location/inquiries')

    # get path configuration values and save them to global_const module
    # path to the folder where all application level log files will be stored (one file per run)
    gc.APP_LOG_DIR = m_cfg.get_value('Location/app_logs')
    # path to the folder where all log files for processing inquiry files will be stored
    # (one file per inquiry)
    gc.INQUIRY_LOG_DIR = m_cfg.get_value('Location/inquiry_logs_relative_path')
    # path to the folder where all processed (and renamed) inquiries will be stored
    gc.INQUIRY_PROCESSED_DIR = m_cfg.get_value('Location/inquiries_processed_relative_path')
    # get config setting for the processed_add_datestamp and save it to global const module
    processed_add_datestamp = m_cfg.get_value('Location/processed_add_datestamp')
    if processed_add_datestamp:
        gc.PROCESSED_ADD_DATESTAMP = processed_add_datestamp
    # # path to the folder where created submission packages will be located. One package sub_folder per inquiry.
    # gc.OUTPUT_REQUESTS_DIR = m_cfg.get_value('Location/output_requests')
    # # path to dir with dynamically created inquiry files for disqualified aliquots
    gc.DISQUALIFIED_INQUIRIES = m_cfg.get_value('Location/inquiries_disqualified_path')

    log_folder_name = gc.APP_LOG_DIR  # gc.LOG_FOLDER_NAME

    # # this variable define if Data Downloader app will be executed at the end of processing inquiries
    # run_data_download = m_cfg.get_value('Execute/run_data_downloader')
    # # path to the Data Downloader tool
    # gc.DATA_DOWNLOADER_PATH = m_cfg.get_value('Location/data_downloader_path')

    prj_wrkdir = os.path.dirname(os.path.abspath(__file__))

    email_msgs = []
    # email_attchms = []

    inquiries_path = Path(inquiries_loc)

    # get current location of the script and create Log folder
    # if a relative path provided, convert it to the absolute address based on the application working dir
    if not os.path.isabs(log_folder_name):
        logdir = Path(prj_wrkdir) / log_folder_name
    else:
        logdir = Path(log_folder_name)
    # logdir = Path(prj_wrkdir) / log_folder_name  # 'logs'
    lg_filename = time.strftime("%Y%m%d_%H%M%S", time.localtime()) + '.log'

    lg = setup_logger_common(common_logger_name, logging_level, logdir, lg_filename)  # logging_level
    mlog = lg['logger']

    mlog.info('Start processing Sequence Results download inquiries in "{}"'.format(inquiries_path))

    try:

        (root, source_inq_dirs, _) = next(walk(inquiries_path))

        inq_proc_cnt = 0
        errors_present = 'OK'

        for inq_dir in source_inq_dirs:
            source_inquiry_path = Path(root) / inq_dir
            mlog.info('Selected for processing inquiry source: "{}", full path: {}'
                      .format(inq_dir, source_inquiry_path))

            (_, _, inq_files) = next(walk(source_inquiry_path))

            # filter only excel files for processing as inquiries
            inquiries = [fl for fl in inq_files if fl.endswith(('xlsx', 'xls'))]
            # filter out temp files (starting with '~$') created when an excel file is open
            inquiries = [fl for fl in inquiries if not fl.startswith('~$')]

            mlog.info('Inquiry files presented (count = {}): "{}"'.format(len(inquiries), inquiries))

            for inq_file in inquiries:
                inq_path = Path(source_inquiry_path) / inq_file

                try:
                    # print('--------->Process file {}'.format(inq_path))
                    mlog.info('The following Inquiry file was selected: "{}".'.format(inq_path))

                    # save timestamp of beginning of the file processing
                    ts = time.strftime("%Y%m%d_%H%M%S", time.localtime())

                    inq_obj = Inquiry(inq_path, m_cfg)

                    if inq_obj and inq_obj.loaded:
                        # proceed processing inquiry
                        mlog.info('Inquiry file was successfully loaded.')
                        mlog.info('Starting processing Download Inquiry file: "{}".'.format(inq_path))

                        inq_obj.process_inquiry()

                        mlog.info('Processing of Download Inquiry was finished for {}'.format(inq_path))

                    inq_proc_cnt += 1

                    # identify if any errors were identified and set status variable accordingly
                    if not inq_obj.error.exist():
                        if not inq_obj.disqualified_items:
                            # no disqualified sub-aliquots present
                            fl_status = 'OK'
                            _str = 'Processing status: "{}". Download Inquiry: {}'.format(fl_status, inq_path)
                            # errors_present = 'OK'  # this variable is set to OK by default, no update needed
                        else:
                            # some disqualified sub-aliquots are presetn
                            fl_status = 'OK_with_Disqualifications'
                            _str = 'Processing status: "{}". Download Inquiry: {}'.format(fl_status, inq_path)
                            if not errors_present == 'ERROR':
                                errors_present = 'DISQUALIFY'
                    else:
                        fl_status = 'ERROR'
                        _str = 'Processing status: "{}". Check processing log file for this inquiry: {}' \
                            .format(fl_status, inq_obj.logger.handlers[0])
                        errors_present = 'ERROR'

                    if fl_status == "OK":
                        mlog.info(_str)
                    else:
                        mlog.warning(_str)

                    processed_dir = inq_obj.processed_folder  # 'Processed'
                    # combine the name of the processed file
                    inq_processed_name = fl_status + '_' + str(inq_file).replace(' ', '_').replace('__', '_')
                    if gc.PROCESSED_ADD_DATESTAMP:
                        inq_processed_name = ts + '_' + inq_processed_name
                    # move processed files to Processed folder
                    fl_processed_name = cm.move_file_to_processed(inq_path, inq_processed_name, processed_dir,
                                                                  inq_obj.logger, inq_obj.error)
                    if fl_processed_name:
                        mlog.info('Processed file "{}" was moved(renamed) to: "{}"'
                                  .format(inq_path, processed_dir / fl_processed_name))
                    else:
                        errors_present = errors_present + '|MoveProcessedError'
                        mlog.warning('Moving the processed file "{}" was not successful due to some errors '
                                     'reported in the request\'s log file {}.'
                                     .format(inq_path, inq_obj.log_handler.baseFilename))

                    # preps for email notification
                    # create a dictionary to feed into template for preparing an email body
                    template_feeder = {
                        'file_num': inq_proc_cnt,
                        'file_path': str(inq_path),
                        'file_path_new':
                            (str(processed_dir / fl_processed_name) if processed_dir and fl_processed_name else None),
                        'inq_obj_errors_cnt': inq_obj.error.count,
                        'log_file_path': inq_obj.log_handler.baseFilename,
                        'dld_request_file_path': str(inq_obj.download_request_path),
                        'inq_sources': inq_obj.inq_sources,
                        'inq_match_aliquots': inq_obj.inq_match_arr,
                        'inq_disqul_aliquots': inq_obj.disqualified_items,
                        'inq_disqul_reprocess_path': str(inq_obj.disqualified_inquiry_path)
                    }
                    email_body_part = cm.populate_email_template('processed_inquiry.html', template_feeder)
                    email_msgs.append(email_body_part)

                    # deactivate the current Inquiry logger
                    deactivate_logger_common(inq_obj.logger, inq_obj.log_handler)
                    inq_obj = None

                except Exception as ex:
                    # report an error to log file and proceed to next file.
                    mlog.error('Error "{}" occurred during processing file: {}\n{} '
                               .format(ex, inq_path, traceback.format_exc()))
                    raise

        mlog.info('Number of successfully processed Inquiries = {}'.format(inq_proc_cnt))

        mlog.info('Preparing to send notificatoin email.')

        email_to = m_cfg.get_value('Email/send_to_emails')
        email_subject = 'processing of download inquiry. '

        if inq_proc_cnt > 0:  # inquiries and len(inquiries) > 0:
            # collect final details and send email about this study results

            err_present = errors_present.split('|') # get all statuses into an array; 1st element is the main status
            if err_present:
                # set email subject based on the main status err_present[0]
                if err_present[0] == 'OK':
                    email_subject = 'SUCCESSFUL ' + email_subject
                elif err_present[0] == 'DISQUALIFY':
                    email_subject = 'SUCCESSFUL (with disqualifications) ' + email_subject
                else:
                    email_subject = 'ERROR(s) present during ' + email_subject
            if len(err_present) > 1:
                if err_present[1] == 'MoveProcessedError':
                    email_subject = email_subject + ' Error moving inquiry to processed.'

            # create a dictionary to feed into template for preparing an email body
            template_feeder = {
                'inq_cnt': inq_proc_cnt,
                # 'run_data_download': run_data_download,
                'downloader_path': gc.DATA_DOWNLOADER_PATH,
                'downloader_start_status': dd_status['status'].lower(),
                'processed_details': '<br/>'.join(email_msgs)
            }
            email_body = cm.populate_email_template('processed_inquiries.html', template_feeder)

            # remove return characters from the body of the email, to keep just clean html code
            email_body = email_body.replace("\r", "")
            email_body = email_body.replace("\n", "")

            # print ('email_subject = {}'.format(email_subject))
            # print('email_body = {}'.format(email_body))

            mlog.info('Sending a status email with subject "{}" to "{}".'.format(email_subject, email_to))

            try:
                if m_cfg.get_value('Email/send_emails'):
                    email.send_yagmail(
                        emails_to=email_to,
                        subject=email_subject,
                        message=email_body
                        # commented adding attachements, since some log files go over 25GB limit and fail email sending
                        # ,attachment_path=email_attchms
                    )
            except Exception as ex:
                # report unexpected error during sending emails to a log file and continue
                _str = 'Unexpected Error "{}" occurred during an attempt to send email upon ' \
                       'finishing processing "{}" study: {}\n{} ' \
                    .format(ex, inq_path, os.path.abspath(__file__), traceback.format_exc())
                mlog.critical(_str)

            mlog.info('End of processing of download inquiries in "{}".'.format(inquiries_path))

    except Exception as ex:
        # report unexpected error to log file
        _str = 'Unexpected Error "{}" occurred during processing file: {}\n{} ' \
            .format(ex, os.path.abspath(__file__), traceback.format_exc())
        mlog.critical(_str)
        raise

    sys.exit()

# if executed by itself, do the following
if __name__ == '__main__':
    check_supplied_arguments()