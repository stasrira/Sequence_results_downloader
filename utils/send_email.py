from utils import common as cm
from utils import ConfigData
from utils import global_const as gc
import yagmail
import os


def send_yagmail(emails_to, subject, message, email_from=None, attachment_path=None, smtp_server=None,
                 smtp_server_port=None):
    root_dir = cm.get_project_root()
    cnf_path = str(root_dir.joinpath(gc.CONFIG_FILE_MAIN))
    m_cfg = ConfigData(cnf_path)
    if not email_from:
        email_from = m_cfg.get_value('Email/default_from_email')
    if not smtp_server:
        smtp_server = os.environ.get('SRD_SMTP_SERVER')  # m_cfg.get_value('Email/smtp_server')
    if not smtp_server_port:
        # smtp_server_port = m_cfg.get_value('Email/smtp_server_port')
        if os.environ.get('SRD_SMTP_SERVER_PORT').isnumeric():
            smtp_server_port = os.environ.get('SRD_SMTP_SERVER_PORT')
        else:
            smtp_server_port = 25

    # receiver = emails_to  # 'stasrirak.ms@gmail.com, stasrira@yahoo.com, stas.rirak@mssm.edu'
    body = message
    filename = attachment_path  # 'test.png'

    yag = yagmail.SMTP(email_from,
                       host=smtp_server,
                       smtp_skip_login=True,
                       smtp_ssl=False,
                       soft_email_validation=False,
                       port=smtp_server_port)
    yag.send(
        to=emails_to,
        subject=subject,
        contents=body,
        attachments=filename,
    )


# if executed by itself, do the following
if __name__ == '__main__':
    # send_email ('stasrirak.ms@gmail.com, stasrira@yahoo.com, stas.rirak@mssm.edu',
    # 'Test Email #4.2', 'Body of the test email??.', None, 'test.png')

    send_yagmail('stasrirak.ms@gmail.com, stasrira@yahoo.com, stas.rirak@mssm.edu', 'Test Email #5.4',
                 '<font color ="blue">Body</font> of the <b>test</b> email!!.', None, 'test.png')
