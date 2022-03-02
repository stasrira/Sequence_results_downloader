import zipfile

import requests
from utils import common as cm
from pathlib import  Path
import re
import os
from zipfile import *  # ZipFile, BadZipfile
import gdown


def test_gdown(file_id, destination_dir = None, file_name = None):
    # import gdown
    import gdown_local
    # url = 'https://drive.google.com/uc?id=0B9P1L--7Wd2vNm9zMTJWOGxobkU'
    # url = 'https://drive.google.com/file/d/1ZvekhXpv31zdF83CeCkY9Qqra47lItlt/view?usp=sharing'
    # id = '1ZvekhXpv31zdF83CeCkY9Qqra47lItlt'
    prj_wrkdir = os.path.dirname(os.path.abspath(__file__))

    if destination_dir is None:
        destination_dir = prj_wrkdir

    if not os.path.exists(destination_dir):
        mode = 0o666  # read and write for all users and groups
        os.mkdir(destination_dir, mode)

    if file_name is None:
        output = destination_dir
    else:
        output = str(Path(destination_dir) / file_name)

    final_file = gdown_local.download(id = file_id, output = output, quiet=False)
    # print (final_file)
    return final_file

def unzip(file_path, destination_dir = None):
    err_str = ''
    if not destination_dir is None:
        # if destination dir is provided, create it if it does not exist
        if not os.path.exists(destination_dir):
            mode = 0o666  # read and write for all users and groups
            os.mkdir(destination_dir, mode)

    if is_zipfile(file_path):
        # if zip file is good to go
        try:
            # Create a ZipFile Object and load sample.zip in it
            with ZipFile(file_path, 'r') as zipObj:
                if destination_dir is None:
                    # extract into the current directory
                    zipObj.extractall()
                else:
                    # Extract all the contents of zip file in different directory
                    zipObj.extractall(destination_dir)
        except (zipfile.BadZipfile, zipfile.LargeZipFile, IOError) as e:
            err_str = 'Exception caught in ZipFile: {}}'.format(e)
    else:
        err_str = 'Bad zip file: {}'.format(file_path)

    print (err_str)
    return err_str
# -----------------------------------------
# def download_file_from_google_drive(id, destination_dir = None, file_name = None):
#     URL = "https://docs.google.com/uc?export=download"
#
#     session = requests.Session()
#
#     response = session.get(URL, params = { 'id' : id }, stream = True)
#     token = get_confirm_token(response)
#
#     if token:
#         params = { 'id' : id, 'confirm' : token }
#         response = session.get(URL, params = params, stream = True)
#
#     original_file_name = re.search(r'filename\=\"(.*)\"', response.headers['Content-Disposition']).group(1)
#     prj_wrkdir = os.path.dirname(os.path.abspath(__file__))
#
#     if destination_dir is None:
#         destination_dir = prj_wrkdir
#
#     if not os.path.exists(destination_dir):
#         # if Processed folder does not exist in the current study folder, create it
#         # log_obj.info('Creating directory for processed files "{}"'.format(processed_dir_path))
#         mode = 0o666  # read and write for all users and groups
#         os.mkdir(destination_dir, mode)
#
#     # if Path.is_dir(Path(dld_dest_dir)):
#     #     dld_dest_dir = str(Path(dld_dest_dir) / original_file_name)
#
#     if file_name is None:
#         file_name = original_file_name
#
#     dld_dest_dir = str(Path(destination_dir) / original_file_name)
#
#     save_response_content(response, dld_dest_dir)
#
# def get_confirm_token(response):
#     for key, value in response.cookies.items():
#         if key.startswith('download_warning'):
#             return value
#
#     return None
#
# def save_response_content(response, dld_dest_dir):
#     CHUNK_SIZE = 32768
#
#     with open(dld_dest_dir, "w+b") as f:
#         for chunk in response.iter_content(CHUNK_SIZE):
#             if chunk: # filter out keep-alive new chunks
#                 f.write(chunk)
# -----------------------------------------

if __name__ == '__main__':



    # -----------------------------------
    # file_id = '1ZvekhXpv31zdF83CeCkY9Qqra47lItlt'
    # url = 'https://drive.google.com/file/d/1ZvekhXpv31zdF83CeCkY9Qqra47lItlt/view?usp=sharing'  # small test link
    url = 'https://drive.google.com/file/d/1Cts3g1YXarLMADTCEv_k6fk9VrQ0zLZc/view?usp=sharing'  # actual example link
    # dld_dest_dir_path = 'D:\MounSinai\Darpa\Programming\GDrive_download\\temp_3'  # local path example
    # dld_dest_dir_path = '\\researchsan02a.mssm.edu\shr1\neurology\Sealfon_Lab\misc\Temp_stas\temp\gdown_test'  # network path example
    dld_dest_dir_path = r'J:\misc\Temp_stas\temp\gdown_test_1'  # network path example
    unzip_dest_dir_path = r'J:\misc\Temp_stas\temp\gdown_unzip'  # network example
    delete_zip_file = False

    file_id = url.split("/")[5]

    dld_dest_dir = str(Path(dld_dest_dir_path))  # / destination_fn
    unzip_dest_dir = str(Path(unzip_dest_dir_path))

    import time
    print (time.strftime("%Y%m%d_%H%M%S", time.localtime()))

    # download_file_from_google_drive(file_id, dld_dest_dir)
    download_fn = test_gdown(file_id, dld_dest_dir)

    print ('Downloaded file: {}'.format(download_fn))

    print (time.strftime("%Y%m%d_%H%M%S", time.localtime()))

    zip_out = unzip(download_fn, unzip_dest_dir)

    if len(zip_out.strip()) == 0:
        # no errors reported in unzip function
        if delete_zip_file:
            os.remove(download_fn)
            print ('zip file was deleted: {}'.format(download_fn))
    pass

