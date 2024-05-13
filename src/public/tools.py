import base64
import os
import smtplib
from requests import post
from argparse import ArgumentParser
from ast import literal_eval
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config import config
from src.public.log_set import log


def get_cmd_argument():
    parser = ArgumentParser()
    parser.add_argument("--task_id", default="", help="测试单id")
    parser.add_argument("--sender", default="", help="发件人邮箱账户")
    parser.add_argument("--passwd", default="", help="发件人邮箱登录密码")
    parser.add_argument("--email_send_all", choices=["true", "false"], default="true", help="是否发送邮件")
    parser.add_argument("--push_to_svn", choices=["true", "false"], default="true", help="是否归档SVN")
    parser.add_argument("-i", "--jk_image", default="", help="镜像版本")
    args = parser.parse_args()
    return {
        "task_id": args.task_id,
        "sender": args.sender,
        "passwd": args.passwd,
        "email_send_all": args.email_send_all == "true" or False,
        "push_to_svn": args.push_to_svn == "true" or False,
        "jk_image": args.jk_image.strip(),
    }


def template_html():
    with open(f"{config.ROOT_DIR}/res/template.html", "r", encoding="utf-8") as f:
        return f.read()


def robot_msg(info, mentioned=''):
    headers = {
        'Content-Type': 'application/json',
    }
    data = {
        "msgtype": "text",
        "text": {
            "content": f"{info}",
            "mentioned_list": [f"{mentioned}"]
        }
    }
    post(
        url=config.robot_url,
        headers=headers, json=data)


def send_email(data: str):
    log.info("发送邮件")
    config_info = literal_eval(base64.b64decode(data).decode("utf-8"))
    from_user = config_info["from_user"]
    theme = config_info["theme"]
    new_html = config_info["new_html"]
    to = config_info["to"]
    cc = config_info["cc"]
    path = config_info["path"]
    email_user = config_info["email_user"]
    email_password = config_info["email_password"]
    reply_message = MIMEMultipart()
    reply_message["From"] = f"{from_user}<{email_user}>"
    reply_message["To"] = ";".join(to)
    reply_message["Subject"] = theme
    filename = os.path.basename(os.path.expanduser(path))

    with open(path, "rb") as f:
        info = f.read()

    attach_part = MIMEApplication(info)
    attach_part.add_header("Content-Disposition", "attachment", filename=filename)
    reply_message.attach(attach_part)
    if cc:
        reply_message["Cc"] = ";".join(cc)
        u = to + cc
    else:
        u = to
    # 添加原邮件内容到回复邮件中
    reply_body = new_html
    reply_message.attach(MIMEText(reply_body, "html", "utf-8"))

    # # 发送回复邮件
    smtp_server = smtplib.SMTP_SSL("smtp.exmail.qq.com", port=465)
    try:
        smtp_server.login(email_user, email_password)
    except smtplib.SMTPAuthenticationError as e:
        raise ConnectionError(e)
    smtp_server.sendmail(email_user, u, reply_message.as_string())
    smtp_server.quit()
    log.info('报告成功发送！')


class ReturnAttr:
    def __init__(self, dictionary):
        self.__dict__ = dictionary

    def __getattr__(self, name):
        value = self.__dict__.get(name)
        if isinstance(value, dict):
            return ReturnAttr(value)
        return value


