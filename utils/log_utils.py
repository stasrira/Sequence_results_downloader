import os
import logging


def setup_logger_common(lg_name, lg_level, log_path, filename):
    os.makedirs(log_path, exist_ok=True)
    log_file = log_path / filename  # (filename + '_' + time.strftime("%Y%m%d_%H%M%S", time.localtime()) + '.log')

    if not lg_name and len(lg_name) == 0:
        lg_name = __name__

    mlog = logging.getLogger(lg_name)

    try:
        lev = eval('logging.' + lg_level)
    except Exception:
        lev = logging.INFO

    mlog.setLevel(lev)

    # create a file handler
    handler = logging.FileHandler(log_file)
    handler.setLevel(lev)  # logging.DEBUG

    # create a logging format
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)

    # add the file handler to the logger
    mlog.addHandler(handler)

    out = {'logger': mlog, 'handler': handler}

    return out


def deactivate_logger_common(logger, handler):
    logger.removeHandler(handler)
