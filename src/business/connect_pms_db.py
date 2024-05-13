import json
import re
from decimal import Decimal
from datetime import datetime
import requests

from src.public.log_set import log
from src.business.sql_query import Query
from src.public.tools import robot_msg
from src.public.tools import ReturnAttr


class RequestX:
    def __init__(self, user, passwd):
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/109.0"
        }
        loginurl = "https://pms.uniontech.com/zentao/user-login.json"
        datauser = {"account": user, "password": passwd}
        self.session = requests.Session()
        self.session.post(loginurl, data=datauser, headers=headers)

    def open_url(self, url, data=None):
        """
         访问url
        :param url:
        :return:
        """
        response = self.session.get(url, data=data)
        return response


class ConnectPms:
    bug_type = {
        "experience": "用户体验/易用性",
        "page_display": "页面显示",
        "standard": "标准规范",
        "function": "功能问题",
        "codeerror": "程序算法错误问题",
        "app": "应用相关",
        "compatible": "compatible",
        "install": "程序打包问题",
        "desktop": "桌面相关",
        "designdefect": "设计缺陷",
        "automation": "automation",
        "reliable": "可靠性问题",
        "system": "系统相关",
        "security": "安全相关",
        "可靠性问题": "可靠性问题",
        "interface": "接口问题",
        "config": "配置相关",
        "performance": "性能问题",
        "baselineedition": "基线版本问题",
        "newfeature": "新增需求",
        "docerror": "文档规范",
        "operation_prompt": "用户操作提示信息问题",
        "not_involve": "不涉及",
        "kernel": "内核相关",
        "modifyimport": "修改引入",
    }
    status = ("active", "resolved", "refused")
    bug_status = {"active": "激活", "resolved": "已解决", "refused": "已拒绝", "closed": "关闭"}
    resolution_status = {
        "not_involve": "不涉及",
        "fixed": "已解决",
        "checked": "已验证",
        "totask": "已集成",
        "tempcheck": "临时方案已验证",
        "tempfix": "临时方案已解决",
        "postponed": "延期处理",
        "notrepro": "无法复现",
        "noproblem": "非问题",
        "custom_checkd": "定制方案已验证",
        "bydesign": "设计如此",
        "external": "外部问题",
        "demand": "需求问题",
        "willnotfix": "不予解决",
        "tostory": "已转需求",
    }

    def __init__(self, user, passwd, task_id):
        self.user = user
        self.rx = RequestX(self.user, passwd)
        self.task_id = task_id
        self.task_url = f"https://pms.uniontech.com/testtask-view-{self.task_id}.json"
        self.task_info = self._get_undone_task()
        self.actions = list(self.task_info["actions"].keys())[::-1]
        self.exclude_project_id = ""
        self.query = Query()
        self.build_info = self.__get_build_info

    @property
    def __get_build_info(self):
        build_info = self.query.query(f"select * from zt_testtask where id={self.task_id}")[0]
        return ReturnAttr(build_info)

    def _get_undone_task(self):
        res = self.rx.open_url(self.task_url)
        res_str = res.json()

        try:
            res_dict = json.loads(res_str.get("data"))
        except json.decoder.JSONDecodeError as exc:
            raise KeyError(f"登陆失败或获取数据失败，请检查账号和密码, {exc}")
        return res_dict

    def get_undone_build(self, build_id):
        url = f"https://pms.uniontech.com/build-view-{build_id}.json"
        res = self.rx.open_url(url)
        if '无权访问' in res.text:
            robot_msg(f'测试单：{self.task_id}，报告发送失败！{self.user}无权访问pms项目！')
            raise Exception('账户无权访问pms项目！')
        res_str = res.json()
        try:
            res_dict = json.loads(res_str.get("data"))
        except json.decoder.JSONDecodeError as exc:
            log.error(exc)
            raise KeyError("登陆失败或获取数据失败，请检查账号和密码")
        return res_dict

    def get_undone_case(self, task_id):
        url = f"https://pms.uniontech.com/testtask-cases-{task_id}-all-0-id_desc-1000-10000-1.json"
        res = self.rx.open_url(url)
        res_str = res.json()
        try:
            res_dict = json.loads(res_str.get("data"))
        except json.decoder.JSONDecodeError as exc:
            raise KeyError("登陆失败或获取数据失败，请检查账号和密码")
        return res_dict

    def get_user_name(self, account):
        sql = f'select realname from zt_user where account="{account}"'
        return self.query.query(sql)[0]["realname"]

    def get_user_email(self, ldap):
        sql = f'select email from zt_user where ldap="{ldap}"'
        return self.query.query(sql)[0]["email"]

    @property
    def get_project_name(self):
        sql = f'select name from zt_project where id="{self.build_info.project}"'
        return self.query.query(sql)[0]["name"]

    @property
    def get_product_name(self):
        sql = f'select name from zt_product where id={self.build_info.product}'
        product = self.query.query(sql)[0].get('name')
        return product

    @property
    def get_test_comment(self):
        comment_dict = {}
        sql = (f"select comment from zt_action where objectID='{self.task_id}' and objectType='testtask' "
               "and comment like '%【测试结果】%' ORDER BY id desc limit 1")
        comment = re.sub("<.+?>", "", self.query.query(sql)[0]["comment"])
        comment = re.sub('&amp;', '&', comment)
        comment_dict["risk"] = re.findall("【测试风险】[：:]+?【(.*?)】", comment)[0]
        result = re.findall("【测试结果】[：:]+?【(.*?)】", comment)
        if (result[0] == '通过') or (result[0] == '不通过'):
            comment_dict["result"] = result[0]
        else:
            result = re.findall("【测试结果】[：:]+?【([^,，;；]+)(.*?)】", comment)[0]
            comment_dict["result"] = result[0]
            comment_dict["result_comment"] = result[1]
        comment_dict["plan"] = re.findall("【测试策略】[：:]+?【(.*?)】", comment)[0]
        comment_dict["link"] = re.findall("【专项链接】[：:]+?【(.*?)】", comment)[0]
        ip = re.findall("【测试机IP】[：:]+?【(.*?)】", comment)
        comment_dict["ip"] = re.split('[,|，]', ip[0]) if ip[0] else []
        software = re.findall("【软件&版本】[：:]+?【(.*?)】", comment)
        package_and_version = {}
        if not software:
            comment_dict["software"] = package_and_version
        if software:
            for package in re.split(r"[,|，]", software[0]):
                try:
                    _package, _version = re.split(r"[:|：]", package)
                except ValueError:
                    _package, _version = package, ''
                package_and_version.update({_package: _version})
        comment_dict["software"] = package_and_version
        return ReturnAttr(comment_dict)

    @property
    def get_test_title(self):
        sql = f"select name from zt_testtask where id='{self.task_id}'"
        name = self.query.query(sql)[0]["name"]
        if re.match(
                r'202[0-9]{5}-|^【.*?】202[0-9]{5}-|^202[0-9]-[0-9]{2}-[0-9]{2}-|^【.*?】202[0-9]-[0-9]{2}-[0-9]{2}-',
                name
        ) is None:
            raise TypeError("测试单名称格式有误，缺少时间戳或时间戳格式错误！")
        return name

    def get_test_url(self):
        task_url = self.task_url.replace("json", "html")
        return task_url

    @property
    def get_test_close_user(self):
        sql = (f"select actor from zt_action where ("
               f"(objectID='{self.task_id}' and objectType='testtask') "
               "and (action='closed' or action='blocked'))")
        actor = self.query.query(sql)[0]["actor"]
        return self.get_user_name(actor)

    @property
    def get_test_time(self):
        sql = f"select action,date from zt_action where objectID='{self.task_id}' and objectType='testtask'"
        task_list = self.query.query(sql)
        period = {}
        for task in task_list:
            if task.get("action") == "started":
                date = datetime.strptime(task.get("date"), "%Y-%m-%d %H:%M:%S")
                period["begin"] = date.strftime("%Y/%m/%d")
            if task.get("action") == "closed":
                date = datetime.strptime(task.get("date"), "%Y-%m-%d %H:%M:%S")
                period["end"] = date.strftime("%Y/%m/%d")
        return ReturnAttr(period)

    def get_bug_by_ids(self, _ids: tuple):
        if len(_ids) == 1:
            search = f"id = {_ids[0]}"
        elif len(_ids) == 0:
            return []
        else:
            search = f"id in {_ids}"
        sql = f"select * from zt_bug where {search}"
        bugs = self.query.query(sql)
        return bugs

    def legacy_bugs(self, product_id):
        title = "bug.id,CONCAT(product.name,'(#', product.id, ')') as product,branch.name branch,module.name module,CONCAT(project.name, '(#', project.id, ')') project,story.title story,task.name task,bug.title,bug.keywords,bug.severity,bug.pri,bug.type,bug.os,bug.browser,bug.baseline,bug.active,bug.trigger,bug.affect,bug.repair,bug.reprt,bug.bugstage,bug.exttype,bug.symbol,bug.age,bug.source,bug.returnEnvironment,bug.steps,bug.status,bug.hangup,bug.deadline,bug.activatedCount,bug.confirmed,bug.mailto,openedByuser.realname openedBy,bug.openedDate,build.name openedBuild,assignedTouser.realname assignedTo,bug.assignedDate,resolvedByuser.realname resolvedBy,bug.resolution,bug.resolvedBuild,bug.resolvedDate,bug.refusedReson,bug.actualsolve,bug.closedBy,bug.closedDate,bug.closedReson,bug.duplicateBug,bug.linkBug,bug.case,lastEditedByuser.realname lastEditedBy,bug.lastEditedDate,bug.testtask,plan.title plan"
        app_sql = f"""SELECT {title}
                        FROM zt_bug bug
                        LEFT JOIN zt_product product
                            ON bug.product=product.id
                        LEFT JOIN zt_branch branch
                            ON branch.id=bug.branch
                        LEFT JOIN zt_module module
                            ON module.id=bug.module
                        LEFT JOIN zt_story story
                            ON story.id=bug.story
                        LEFT JOIN zt_productplan plan
                            ON plan.id=bug.plan
                        LEFT JOIN zt_task task
                            ON task.id=bug.task
                        LEFT JOIN zt_project project
                            ON project.id=bug.project
                        LEFT JOIN zt_user openedByuser
                            ON openedByuser.account=bug.openedBy
                        LEFT JOIN zt_build build
                            ON build.id=bug.openedBuild
                        LEFT JOIN zt_user assignedTouser
                            ON assignedTouser.account=bug.assignedTo
                        LEFT JOIN zt_user resolvedByuser
                            ON resolvedByuser.account=bug.resolvedBy
                        LEFT JOIN zt_user lastEditedByuser
                            ON lastEditedByuser.account=bug.lastEditedBy
                        WHERE bug.deleted = '0'
                                AND bug.status IN {self.status}
                                AND bug.product = {product_id}"""
        if len(self.exclude_project_id) == 1:
            app_sql = app_sql + f" AND bug.project != {self.exclude_project_id[0]}"
        elif len(self.exclude_project_id) > 1:
            app_sql = app_sql + f" AND bug.project not in {self.exclude_project_id}"
        all_bugs = self.query.query(app_sql)
        for index, i in enumerate(all_bugs):
            if not i["branch"]:
                all_bugs[index]["branch"] = "所有"
            all_bugs[index]["module"] = "/" + i["module"] if i["module"] else "/"
            all_bugs[index]["type"] = self.bug_type.get(i["type"], i["type"])
            all_bugs[index]["steps"] = re.sub("<.+?>", "", i["steps"])
            all_bugs[index]["status"] = self.bug_status[i["status"]]
            all_bugs[index]["confirmed"] = "否" if i["confirmed"] == "0" else "是"
            if i["mailto"]:
                all_bugs[index]["mailto"] = ",".join(
                    [self.get_user_name(j) if j else "" for j in i["mailto"].split(",")]
                )
            if not i["openedBuild"]:
                all_bugs[index]["openedBuild"] = "主干"
            all_bugs[index]["linkBug"] = ""
            all_bugs[index]["case"] = ""
            if not i["duplicateBug"]:
                all_bugs[index]["duplicateBug"] = ""
            if i["resolution"]:
                all_bugs[index]["resolution"] = self.resolution_status.get(
                    i["resolution"], i["resolution"]
                )
        return all_bugs

    @staticmethod
    def legacy_di(all_bugs):
        overall_di = Decimal("0")
        DIWeight = {"1": "10", "2": "3", "3": "1", "4": "0.1"}
        for bug_id in all_bugs:
            overall_di += Decimal(DIWeight[bug_id["severity"]])
        return overall_di

    def get_serious_bug(self, product_id):
        title = "id,title,severity,status,type"
        app_sql = f"""SELECT {title}
                        FROM zt_bug
                        WHERE deleted = '0'
                            AND status IN {self.status}
                            AND product = {product_id}
                            AND severity <3"""
        all_bugs = self.query.query(app_sql)
        for index, i in enumerate(all_bugs):
            all_bugs[index]["type"] = self.bug_type.get(i["type"], i["type"])
            all_bugs[index]["status"] = self.bug_status[i["status"]]
        return all_bugs


if __name__ == '__main__':
    # t = ConnectPms('ut001652', 'Lxs@00001', '38979')
    # print(t.get_test_title)
    title = "bug.id,CONCAT(product.name,'(#', product.id, ')') as product,branch.name branch,module.name module,CONCAT(project.name, '(#', project.id, ')') project,story.title story,task.name task,bug.title,bug.keywords,bug.severity,bug.pri,bug.type,bug.os,bug.browser,bug.baseline,bug.active,bug.trigger,bug.affect,bug.repair,bug.reprt,bug.bugstage,bug.exttype,bug.symbol,bug.age,bug.source,bug.returnEnvironment,bug.steps,bug.status,bug.hangup,bug.deadline,bug.activatedCount,bug.confirmed,bug.mailto,openedByuser.realname openedBy,bug.openedDate,build.name openedBuild,assignedTouser.realname assignedTo,bug.assignedDate,resolvedByuser.realname resolvedBy,bug.resolution,bug.resolvedBuild,bug.resolvedDate,bug.refusedReson,bug.actualsolve,bug.closedBy,bug.closedDate,bug.closedReson,bug.duplicateBug,bug.linkBug,bug.case,lastEditedByuser.realname lastEditedBy,bug.lastEditedDate,bug.testtask,plan.title plan"
    app_sql = f"""SELECT {title}
                            FROM zt_bug bug
                            LEFT JOIN zt_product product
                                ON bug.product=product.id
                            LEFT JOIN zt_branch branch
                                ON branch.id=bug.branch
                            LEFT JOIN zt_module module
                                ON module.id=bug.module
                            LEFT JOIN zt_story story
                                ON story.id=bug.story
                            LEFT JOIN zt_productplan plan
                                ON plan.id=bug.plan
                            LEFT JOIN zt_task task
                                ON task.id=bug.task
                            LEFT JOIN zt_project project
                                ON project.id=bug.project
                            LEFT JOIN zt_user openedByuser
                                ON openedByuser.account=bug.openedBy
                            LEFT JOIN zt_build build
                                ON build.id=bug.openedBuild
                            LEFT JOIN zt_user assignedTouser
                                ON assignedTouser.account=bug.assignedTo
                            LEFT JOIN zt_user resolvedByuser
                                ON resolvedByuser.account=bug.resolvedBy
                            LEFT JOIN zt_user lastEditedByuser
                                ON lastEditedByuser.account=bug.lastEditedBy
                            WHERE bug.deleted = '0'
                                    AND bug.status IN open
                                    AND bug.product = 88888"""
    print(app_sql)