import re
import requests
from datetime import datetime
from jsonpath import jsonpath
from src.public.log_set import log
from src.public.tools import ReturnAttr
from config import config


class Cooperation:
    def __init__(self, product_id, project_name):
        self.product_id = product_id
        self.project_name = project_name
        self.__public = {
            "appKey": "a935d3366d679685",
            "sign": "NzAxNDQzN2Q1YmI0MjVjYjNkY2RjNDI1YWUxZGEwODk3MjAzNWM4MmE0MmNhOTlhZDlhNzY3ODk4Y2JmNzY1NQ==",
            "pageSize": 2000,
            "pageIndex": 1,
        }
        self.__group_info = self.__get_group_info()
        self.__package_id = self.__get_package_id()
        self.__task_info = self.__get_task_info()

    def __get_group_info(self):
        group_conf = {
            "worksheetId": "csbgfsr",
            "viewId": "642166fadf643f9d31a1e04f",
        }
        group_conf.update(self.__public)
        return self.__request_data('get', group_conf)

    def __get_package_id(self):
        package_id_data = {
            "worksheetId": "csbggjpz_s_",
            "viewId": "642b9d42b811783e284c2e13",
        }
        package_id_data.update(self.__public)
        return self.__request_data('get', package_id_data)

    def __get_task_info(self):
        task_data = {
            "worksheetId": "rcrwpq",
            "viewId": "64c35664cc11a7bd3d7e4b68",
        }
        task_data.update(self.__public)
        return self.__request_data('get', task_data)

    @staticmethod
    def __request_data(action, data):
        headers = {
            "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
            "Content-Type": "application/json"
        }
        url = {
            'get': "https://cooperation.uniontech.com/api/v2/open/worksheet/getFilterRows",
            'update': "https://cooperation.uniontech.com/api/v2/open/worksheet/editRow"
        }
        try:
            if action == 'get':
                res = requests.post(url=url['get'], headers=headers, json=data).json()
                datas = res.get("data").get("rows")
            else:
                datas = requests.post(url=url['update'], headers=headers, json=data).json()
        except Exception as exc:
            log.error(f"明道云获取配置失败：{exc}")
            raise ConnectionError(f"明道云获取配置失败：{exc}")
        return datas

    def get_hardware_env(self):
        hardware_env_data = {
            "worksheetId": "csbggjpz_e_",
            "viewId": "642276f9672f05905b9c07cc",
        }
        hardware_env_data.update(self.__public)
        return self.__request_data('get', hardware_env_data)

    def get_svn_package_by_cooperation(self):
        svn_url = jsonpath(
            self.__package_id,
            expr=f"$..[?('{self.product_id}' == @.pms_product_id)]"
        )
        if not svn_url:
            log.error(f"无应用配置 {self.product_id}")
            raise KeyError(f"无应用配置 {self.product_id}")
        svn = svn_url[0].get("svn").strip().strip("/")
        package = svn_url[0].get("package").strip()
        exclude_project_id = svn_url[0].get("exclude_project_id").strip()
        base_line = svn_url[0].get("base_line").strip()
        words = svn_url[0].get("words").strip()
        exclude_words = svn_url[0].get("exclude_words").strip()
        legacy_check = svn_url[0].get("legacy_check").strip()
        log.info(f"legacy_check:{legacy_check}")
        package_info = {
            "svn": svn,
            "package": package,
            "exclude_project_id": exclude_project_id,
            "base_line": base_line,
            "words": words,
            "exclude_words": exclude_words,
            "legacy_check": True if legacy_check == "是" else False,
        }
        log.info(package_info)
        return package_info

    def get_report_format_by_cooperation(self):
        report_format = jsonpath(
            self.__group_info,
            expr=f"$..[?('{self.project_name}' in @.group && '报告' in @.group)].email")
        if not report_format:
            log.error("缺失 report format 配置")
            raise KeyError("缺失 report format 配置")
        log.info(f"报告标题格式：{report_format[0]}")
        return report_format[0]

    def get_project_email_by_cooperation(self):
        info = jsonpath(
            self.__group_info,
            expr=f"$..[?('{self.project_name}' in @.group && '抄送' not in @.group)].email"
        )
        to = [i for i in info if i.endswith("@uniontech.com")]

        cc = jsonpath(self.__group_info, expr=f"$..[?('抄送' in @.group && '{self.project_name}' in @.group)].email") or []
        for user in self.__group_info:
            if user['group'] == ['抄送']:
                cc.append(user['email'])
        return {"to": to, "cc": cc}

    def get_group_approver_by_cooperation(self):
        reviewed = jsonpath(
            self.__group_info,
            expr=f"$..[?('{self.project_name}' in @.group && '审核人' in @.group)].user_name"
        )
        approver = jsonpath(
            self.__group_info,
            expr=f"$..[?('{self.project_name}' in @.group && '批准人' in @.group)].user_name"
        )
        if not reviewed:
            log.error("项目未配置报告审核人")
            raise TypeError("项目未配置报告审核人")
        if not approver:
            log.error("项目未配置报告批准人")
            raise TypeError("项目未配置报告批准人")
        log.info(f"测试报告审批人：{reviewed[0]}")
        log.info(f"测试报告批准人：{approver[0]}")
        return {"reviewed": reviewed[0], "approver": approver[0]}

    # def get_task_for_id_by_cooperation(self):
    #     tasks = jsonpath(self.task, expr=f"$..[?('测试单' == @.job_type)]")
    #     for task in tasks:
    #         url = jsonpath(task, '$.url')[0]
    #         if re.search(rf'view-{self.task_id}.html', url):
    #             return {
    #                 'row_id': jsonpath(task, '$.rowid')[0],
    #                 'title': jsonpath(task, '$.title')[0],
    #                 'pms_url': url,
    #                 'report_info': jsonpath(task, '$.report_info')[0],
    #                 'owner': jsonpath(task, '$.owner')[0]
    #             }

    # def get_need_send_report_task_list(self):
    #     today = datetime.now().strftime('%Y-%m-%d')
    #     expr = (f"$..[?('多媒体23.7' == @.project && "
    #             f"'{today}' == @.rel_end_time)]")
    #     # f"'' == @.report_info)]")
    #     print(expr)
    #     tasks = jsonpath(self.task, expr=expr)
    #     if not tasks:
    #         raise Exception(f'当前无已完成，且待发报告的测试任务!')
    #     return [re.findall(r'view-(\d+).html', jsonpath(task, '$.url')[0])[0] for task in tasks]

    # def update_report_info(self, row_id, content):
    #     data = {
    #         'worksheetId': 'rcrwpq',
    #         'rowId': row_id,
    #         'controls': [
    #             {
    #                 "controlId": "report_info",
    #                 "value": f"{content}"
    #             }
    #         ]
    #     }
    #     data.update(self.public)
    #     del data['pageSize']
    #     del data['pageIndex']
    #     self.__request_data('update', data)


if __name__ == '__main__':
    test = Cooperation(product_id=357, project_name='多媒体23.7')
    print(test.get_project_email_by_cooperation())
    print(test.get_svn_package_by_cooperation())
    print(test.get_report_format_by_cooperation())
    print(test.get_group_approver_by_cooperation())
    for i in test.get_hardware_env:
        print(i['board'])
