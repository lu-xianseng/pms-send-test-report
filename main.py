import os
import re
import sys
import base64

from src.public.log_set import log
from src.public.svn_report import SVNReport
from src.public.tools import template_html
from src.public.write_xlsx import WriteReport
from src.public.tools import send_email, robot_msg, get_cmd_argument

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import config
from src.business.cooperation_operation import Cooperation
from src.business.get_task_info import Task
from src.business.get_machine_info import MachineInfo

import traceback


def main(task_id: str = None, sender: str = None, passwd: str = None, email_send_all: bool = None,
         push_to_svn: bool = None, temp_review: str = None, temp_cc: str = None):
    """
    @param task_id: 测试单id
    @param sender: 发件人
    @param passwd: 密码
    @param email_send_all:    是否发送邮件
    @param push_to_svn:  是否归档svn
    @return:
    @param temp_cc: 临时抄送人
    @param temp_review: 临时接收人
    """
    all_task_id = re.split(r'[,|，]', task_id)
    for task_id in all_task_id:
        log.info(f"一共{len(all_task_id)}个测试单！")

        try:
            task = Task(task_id)
            # base
            task_url = task.url
            task_name = task.name
            task_project_name = task.project_name
            task_product_name = task.product_name
            task_product_id = task.product_id
            task_stories = task.stories
            # result
            task_new_bug = task.new_bug()
            task_regression_bug = task.regression_bug()
            task_test_time = task.test_time()
            task_close_user = task.close_user()
            task_result = task.result()
            # comment
            task_comment_risk = task.comment_risk
            task_comment_plan = task.comment_plan
            task_comment_link = task.comment_link
            task_comment_software = task.comment_software
            task_comment_ip = task.comment_ip

            cpt = Cooperation(task_product_id, task_project_name)
            cpt_svn_package = cpt.get_svn_package_by_cooperation()
            cpt_report_format = cpt.get_report_format_by_cooperation()
            cpt_project_email = cpt.get_project_email_by_cooperation()
            cpt_group_approver = cpt.get_group_approver_by_cooperation()
            cpt_hardware_env = cpt.get_hardware_env()

            task_legacy_bug = task.legacy_bug(
                exclude_project_id=cpt_svn_package.get('exclude_project_id'),
                base_line=cpt_svn_package.get('base_line'),
                exclude_words=cpt_svn_package.get('exclude_words'),
                words=cpt_svn_package.get('words'),
                legacy_check=cpt_svn_package.get('legacy_check')
            )

            svn = SVNReport(cpt_svn_package.get('svn'))

            test_packages = task_comment_software
            default_package = cpt_svn_package.get('package')
            if default_package:
                test_packages.update({default_package: ''})

            # 测试报告
            machine_info = MachineInfo(
                list(test_packages.keys()),
                task_comment_ip,
                cpt_hardware_env,
                test_packages
            )

            from_machine_info = machine_info.get_test_machine_info()
            if from_machine_info:
                test_packages = from_machine_info[0]["apps"].items()
            else:
                test_packages = test_packages.items()
            version = ("\n".join([f"{pac}: {ver}" for pac, ver in test_packages]))
            log.info(f"测试包版本信息：{version}")

            task_period = f"{task_test_time.started}-{task_test_time.closed}"

            report_name = cpt_report_format.format(project=task_project_name, task_name=task_name)
            report_file_path = os.path.join(config.local_path, report_name + ".xlsx")
            report = WriteReport(report_file_path)
            report.update_front_cover(
                task_product_name,
                task_close_user,
                task_test_time.closed,
                cpt_group_approver.get('reviewed'),
                cpt_group_approver.get('approver'),
            )
            # 测试报告 sheet
            report.update_test_report(
                task_project_name,
                version if version else "/",
                task_close_user,
                task_period,
                task_result.result,
                task_comment_plan,
                task_url,
                task_result.bug,
                task_result.case,
                task_legacy_bug.di,
                task_comment_link,
                task_comment_risk,
                task_new_bug + task_regression_bug.failed,
            )
            # 测试环境 sheet
            report.update_test_env(from_machine_info)
            # 遗留 bug list sheet
            report.update_unclosed_bug(task_legacy_bug.bug_list)
            del report

            if push_to_svn:
                svn.checkout_svn_file()
                svn.commit_report_file(report_file_path)
                del svn

            if email_send_all:
                # email
                to = cpt_project_email.get('to')
                cc = cpt_project_email.get('cc')
            else:
                to = [sender]
                cc = []

            if temp_review:
                tmp_review = re.split(r'[,|，]', temp_review)
                log.debug(f"----> {tmp_review}")
                to += tmp_review
                log.debug(f"----> {to}")

            if temp_cc:
                temp_cc = re.split(r'[,|，]', temp_cc)
                cc += temp_cc

            if cpt_svn_package.get('svn'):
                # 延迟归档则显示归档目录
                if push_to_svn:
                    url = cpt_svn_package.get('svn') + f"/{report_name}.xlsx"
                else:
                    url = cpt_svn_package.get('svn')
            else:
                url = "无归档地址"
            result_title = re.sub(r'(通过|不通过).*', r'\1', task_result.result)
            name_zh, name_en, position = config.user(sender)
            new_html = template_html().format(
                add_num=len(task_new_bug),
                task=task_name,
                result_title=result_title,
                result=task_result.result,
                url=url,
                app_name=task.product_name,
                version=version.replace("\n", "<br>"),
                test_time=task_test_time.closed,
                relevance_bugs=len(task_regression_bug.all),
                story_num=len(task_stories),
                reopen_num=len(task_regression_bug.failed),
                serious_legacy=len(task_legacy_bug.serious_list),
                all_bugs=len(task_legacy_bug.bug_list),
                legacy_di=task_legacy_bug.di,
                tactics=task_comment_plan,
                name_zh=name_zh,
                name_en=name_en,
                position=position
            )

            email_info = (
                base64.b64encode((str({
                    "theme": "{}-{}".format(task_name, result_title),
                    "new_html": new_html,
                    "cc": cc,
                    "to": to,
                    "from_user": name_zh,
                    "path": os.path.join(config.local_path, report_name + ".xlsx"),
                    "email_user": sender,
                    "email_password": passwd.replace("\n", ""),
                }).encode("utf-8"))).decode("utf-8")
            )

            try:
                send_email(email_info)
                # cpt.update_report_info(task_info_by_cpt.get('row_id'), report_info + url)
            except OSError as e:
                raise Exception(e)
        except Exception as e:

            log.error(traceback.format_exc())
            robot_msg(f'报告发送失败！请检查\n\t'
                      f'测试单：{task.url}\n\t'
                      f'{task.name}\n\n\t'
                      f'{e}\n@{task_close_user}', )
    else:
        log.info("完成！")


if __name__ == '__main__':
    if len(sys.argv) > 3:
        argument = get_cmd_argument()
    else:
        argument = {
            "task_id": "41085",
            "sender": "luye@uniontech.com",
            "passwd": "Lxs@00001",
            "email_send_all": False,
            "push_to_svn": False,
        }
    main(**argument)
