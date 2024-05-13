import os
from configparser import RawConfigParser
from os.path import dirname, abspath, join


class GetCfg:
    """Gets the value in the configuration file"""

    def __init__(self, config_file: str, option: [str, None] = None):
        self.config_file = config_file
        self.option = option
        self.conf = RawConfigParser()
        self.conf.read(self.config_file, encoding="utf-8")

    def get(self, key: str, op: [str, None] = None, default=None) -> str:
        if op is None and self.option is not None:
            op = self.option
        if op is None and self.option is None:
            raise ValueError("option is None")
        return self.conf.get(op, key, fallback=default)

    def get_bool(self, key: str, op: [str, None] = None, default=False) -> bool:
        if op is None and self.option is not None:
            op = self.option
        if op is None and self.option is None:
            raise ValueError("option is None")
        return self.conf.getboolean(op, key, fallback=default)


class GlobalConfig:
    """Basic framework global configuration"""

    # Root dir
    Global_PMS = {}
    Global_CPT = {}
    ROOT_DIR = dirname(dirname(abspath(__file__)))

    GLOBAL_CONFIG_FILE_PATH = join(ROOT_DIR, "config/project-config.ini")
    USER_CONFIG_FILE_PATH = join(ROOT_DIR, "config/user-config.ini")

    smtp = GetCfg(GLOBAL_CONFIG_FILE_PATH, "SMTP")
    smtp_host = smtp.get("host")
    smtp_port = smtp.get("post")

    pms = GetCfg(GLOBAL_CONFIG_FILE_PATH, "PMS")
    pms_user = pms.get('user')
    pms_passwd = pms.get('passwd')

    svn_ = GetCfg(GLOBAL_CONFIG_FILE_PATH, "SVN")
    svn_user = svn_.get('user')
    svn_passwd = svn_.get('passwd')

    robot = GetCfg(GLOBAL_CONFIG_FILE_PATH, "ROBOT")
    robot_url = robot.get('url')

    report_config = GetCfg(GLOBAL_CONFIG_FILE_PATH, "REPORT_CONF")
    local_path = report_config.get("local_path")
    if not os.path.exists(local_path):
        os.makedirs(local_path)

    EXCEL_PATH = join(ROOT_DIR, "res/template.xlsx")

    @classmethod
    def user(cls, account):
        info = GetCfg(cls.USER_CONFIG_FILE_PATH, account)
        return info.get('name_zh'), info.get('name_en'), info.get('position')


config = GlobalConfig()
