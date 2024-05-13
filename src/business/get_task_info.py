import re
from decimal import Decimal
from datetime import datetime
from src.public.log_set import log
from src.business.sql_query import Query
from src.public.tools import ReturnAttr
from config import config


class TaskBase(Query):

    def __init__(self, task_id):
        super().__init__()
        self.task_id = task_id
        self.__task = self.__get_task_data
        if self.status in ['doing', 'wait']:
            raise Exception("测试单未关闭！")

    @property
    def __get_task_data(self):
        sql_title = """task.id as task_id,task.name as task_name,task.product as product_id,task.project as project_id,
                     task.build as build_id,task.status as task_status,task.deleted as task_deleted,
                     task.testResult as task_result,product.name as product_name,project.name as project_name, 
                     build.bugs as regression_bug, build.stories as stories, 
                     GROUP_CONCAT(DISTINCT bug.id ORDER BY bug.id SEPARATOR ',') as new_bugs """
        sql = f"""SELECT {sql_title} FROM zt_testtask task 
                LEFT JOIN zt_project project ON project.id=task.project 
                LEFT JOIN zt_product product ON product.id=task.product 
                LEFT JOIN zt_build build ON build.id=task.build 
                LEFT JOIN zt_bug bug ON build.id=bug.openedBuild and bug.deleted='0' and bug.activatedCount='0' 
                WHERE task.id={self.task_id} AND task.deleted='0' 
                GROUP BY task.id"""
        data = self.query(sql)[0]
        log.debug(data)
        return data

    @property
    def name(self):
        name = self.__task['task_name']
        log.info(f"测试单名称：{name}")
        if re.match(
                r'202[0-9]{5}-|^【.*?】202[0-9]{5}-|^202[0-9]-[0-9]{2}-[0-9]{2}-|^【.*?】202[0-9]-[0-9]{2}-[0-9]{2}-',
                name
        ) is None:
            raise TypeError("测试单名称格式有误，缺少时间戳或时间戳格式错误！")
        return name

    @property
    def build_id(self):
        build = self.__task['build_id']
        log.info(f"测试单版本号：{build}")
        return build

    @property
    def product_id(self):
        _id = self.__task['product_id']
        log.info(f"测试单所属产品id：{_id}")
        return _id

    @property
    def project_id(self):
        _id = self.__task['project_id']
        log.info(f"测试单所属项目id：{_id}")
        return _id

    @property
    def project_name(self):
        name = self.__task['project_name']
        log.info(f"测试单所属项目名称：{name}")
        return name

    @property
    def product_name(self):
        name = self.__task['product_name']
        log.info(f"测试单所属产品名称：{name}")
        return name

    @property
    def status(self):
        status = self.__task['task_status']
        log.info(f"测试单状态：{status}")
        return status

    @property
    def result(self):
        result = self.__task['task_result']
        log.info(f"测试单结果：{result}")
        return result

    @property
    def url(self):
        url = f"https://pms.uniontech.com/testtask-view-{self.task_id}.html"
        log.info(f"测试单链接：{url}")
        return url

    @property
    def regression(self):
        bug_list = list(filter(bool, self.__task['regression_bug'].split(',')))
        log.info(f"回归bug：{bug_list}")
        return bug_list

    @property
    def stories(self):
        stories = list(filter(bool, self.__task['stories'].split(',')))
        log.info(f"关联需求：{stories}")
        return stories

    @property
    def new_add(self):
        try:
            bug_list = self.__task['new_bugs'].split(',')
        except AttributeError:
            bug_list = []
        log.info(f"新增bug：{bug_list}")
        return bug_list


class TaskComment(TaskBase):

    def __init__(self, task_id):
        super().__init__(task_id)
        self.__comment = ''
        self.__get_comment()

    def __get_comment(self):
        __sql = (f"select comment from zt_action where objectID='{self.task_id}' and objectType='testtask' "
                 "and comment like '%【测试结果】%' ORDER BY id desc limit 1")
        try:
            self.__comment = self.query(__sql)[0]["comment"]
            self.__comment = re.sub("<.+?>", "", self.__comment)
            self.__comment = re.sub('&amp;', '&', self.__comment)
        except IndexError:
            raise Exception("测试单未备注测试结果！")

    @property
    def comment_risk(self):
        return re.findall("【测试风险】[：:]+?【(.*?)】", self.__comment)[0]

    @property
    def comment_result(self):
        result = {}
        info = re.findall("【测试结果】[：:]+?【(.*?)】", self.__comment)
        if (info[0] == '通过') or (info[0] == '不通过'):
            result["result"] = info[0]
            result["comment"] = ''
        else:
            info = re.findall("【测试结果】[：:]+?【([^,，;；]+)(.*?)】", self.__comment)[0]
            result["result"] = info[0]
            result["comment"] = info[1]
        return ReturnAttr(result)

    @property
    def comment_plan(self):
        return re.findall("【测试策略】[：:]+?【(.*?)】", self.__comment)[0]

    @property
    def comment_link(self):
        return re.findall("【专项链接】[：:]+?【(.*?)】", self.__comment)[0]

    @property
    def comment_regression_bug_id(self):
        try:
            bug = re.findall("【回归未关联bug】[：:]+?【(.*?)】", self.__comment)[0]
            return re.split('[,|，]', bug[0])
        except IndexError:
            return []

    @property
    def comment_ip(self):
        ip = re.findall("【测试机IP】[：:]+?【(.*?)】", self.__comment)
        try:
            return re.split('[,|，]', ip[0])
        except IndexError:
            return []

    @property
    def comment_software(self):
        software = re.findall("【软件&版本】[：:]+?【(.*?)】", self.__comment)
        package_and_version = {}
        if software:
            for package in re.split(r"[,|，]", software[0]):
                try:
                    _package, _version = re.split(r"[:|：]", package)
                except ValueError:
                    _package, _version = package, ''
                package_and_version.update({_package: _version})
        return package_and_version


class Task(TaskComment):
    __bug_type = {
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
    __bug_status = ("active", "resolved", "refused")
    __resolution_status = {
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
    __bug_status_map = {"active": "激活", "resolved": "已解决", "refused": "已拒绝", "closed": "关闭"}
    __bug_query_title = ("bug.id as bug_id,bug.title as bug_title,bug.severity as severity,"
                         "bug.status as bug_status,bug.activeReason as bug_activeReason,bug.type as bug_type")

    def new_bug(self):
        new_bugs = []

        for _id in self.new_add:
            sql = (f"SELECT {self.__bug_query_title} FROM zt_bug bug "
                   f"WHERE bug.id={_id} and bug.deleted='0' and bug.activatedCount='0'")
            bug = self.query(sql)[0]
            bug['bug_type'] = self.__bug_type.get(bug['bug_type'])
            bug['bug_status'] = self.__bug_status_map.get(bug['bug_status'])
            new_bugs.append(bug)
        return new_bugs

    def regression_bug(self):
        bug_list = {
            "all": [],
            "failed": []
        }
        regression_bugs = self.comment_regression_bug_id + self.regression
        for _id in regression_bugs:
            bug = self.query(f'SELECT {self.__bug_query_title} FROM zt_bug bug where id={_id}')
            bug[0]['bug_status'] = self.__bug_status_map.get(bug[0]['bug_status'])
            bug[0]['bug_type'] = self.__bug_type.get(bug[0]['bug_type'])
            if bug[0].get("bug_status") == '激活':
                bug_list['failed'].append(bug[0])
            bug_list['all'].append(bug[0])
        return ReturnAttr(bug_list)

    def case_execution(self):
        sql = (f"SELECT * FROM zt_testrun run "
               f"WHERE run.task={self.task_id}")
        case_info = {}
        case = self.query(sql)
        if not case:
            raise Exception("测试单未关联用例")

        def get_case_num(key, value):
            return len(list(filter(lambda x: x[key] == value, case)))

        if get_case_num('status', 'wait'):
            raise Exception("测试单存在未执行用例")

        case_info["all"] = len(case)
        case_info["passed"] = get_case_num('lastRunResult', 'pass')
        case_info["failed"] = get_case_num('lastRunResult', 'fail')
        case_info["blocked"] = get_case_num('lastRunResult', 'blocked')
        return ReturnAttr(case_info)

    def test_time(self):
        sql = (f"select action,date from zt_action "
               f"where objectID='{self.task_id}' and "
               f"objectType='testtask' and "
               f"action in ('started', 'blocked', 'closed')")
        task_list = self.query(sql)
        period = {}

        def format_time(_time):
            _date = datetime.strptime(_time, "%Y-%m-%d %H:%M:%S")
            return _date.strftime("%Y/%m/%d")

        for task in task_list:
            period[task["action"]] = format_time(task.get("date"))
        log.info(f"测试单周期: {period}")
        return ReturnAttr(period)

    def __get_realname(self, account):
        sql = f"select realname from zt_user where account='{account}'"
        name = self.query(sql)[0]["realname"]
        return name

    def close_user(self):
        sql = (f"select actor from zt_action where "
               f"objectID='{self.task_id}' and objectType='testtask' "
               "and action in ('closed','blocked')")
        actor = self.query(sql)[0]["actor"]
        name = self.__get_realname(actor)
        log.info(f"测试单关闭人: {name}")
        return name

    def result(self):
        conclusion = {
            "bug": "",
            "case": "",
            "result": "通过",
        }
        regression = self.regression_bug()
        case = self.case_execution()
        if len(regression.failed) > 0:
            active_rate = float(
                Decimal(len(regression.failed)) / Decimal(len(regression.all))
            )
        else:
            active_rate = 0

        sql = (f"select testResult from zt_testtask "
               f"where id='{self.task_id}'")
        task_result = self.query(sql)[0]["testResult"]
        if task_result != self.comment_result.result:
            raise Exception("测试单测试结果与备注结果不符")
        if any(
                [
                    active_rate > 0.1,
                    self.comment_result.result == "不通过"
                ]
        ):
            conclusion["result"] = "不通过" + f"{self.comment_result.comment}"
        conclusion["bug"] = (f'按测试单要求的镜像环境中，回归共 {len(regression.all)} 个，'
                             f'通过 {len(regression.all) - len(regression.failed)} 个，'
                             f'不通过 {len(regression.failed)} 个')

        conclusion["case"] = (f"按测试单要求的镜像环境中，共执行用例 {case.all} 条, "
                              f"通过 {case.passed} 条，失败 {case.failed} 条, "
                              f"阻塞 {case.blocked} 条，共新增 {len(self.new_bug())} 个bug")
        return ReturnAttr(conclusion)

    def legacy_bug(self, exclude_project_id, base_line, exclude_words, words):
        title = ("bug.id,CONCAT(product.name,'(#', product.id, ')') as product,branch.name branch,module.name module,"
                 "CONCAT(project.name, '(#', project.id, ')') project,story.title story,task.name task,bug.title,"
                 "bug.keywords,bug.severity,bug.pri,bug.type,bug.os,bug.browser,bug.baseline,bug.active,bug.trigger,"
                 "bug.affect,bug.repair,bug.reprt,bug.bugstage,bug.exttype,bug.symbol,bug.age,bug.source,"
                 "bug.returnEnvironment,bug.steps,bug.status,bug.hangup,bug.deadline,bug.activatedCount,"
                 "bug.confirmed,bug.mailto,openedByuser.realname openedBy,bug.openedDate,build.name openedBuild,"
                 "assignedTouser.realname assignedTo,bug.assignedDate,resolvedByuser.realname resolvedBy,"
                 "bug.resolution,bug.resolvedBuild,bug.resolvedDate,bug.refusedReson,bug.actualsolve,bug.closedBy,"
                 "bug.closedDate,bug.closedReson,bug.duplicateBug,bug.linkBug,bug.case,"
                 "lastEditedByuser.realname lastEditedBy,bug.lastEditedDate,bug.testtask,plan.title plan, "
                 "bug.activeReason as bug_activeReason")
        app_sql = f"""SELECT {title} FROM zt_bug bug 
                            LEFT JOIN zt_product product ON bug.product=product.id 
                            LEFT JOIN zt_branch branch ON branch.id=bug.branch  
                            LEFT JOIN zt_module module ON module.id=bug.module 
                            LEFT JOIN zt_story story ON story.id=bug.story 
                            LEFT JOIN zt_productplan plan ON plan.id=bug.plan 
                            LEFT JOIN zt_task task ON task.id=bug.task 
                            LEFT JOIN zt_project project ON project.id=bug.project 
                            LEFT JOIN zt_user openedByuser ON openedByuser.account=bug.openedBy 
                            LEFT JOIN zt_build build ON build.id=bug.openedBuild 
                            LEFT JOIN zt_user assignedTouser ON assignedTouser.account=bug.assignedTo 
                            LEFT JOIN zt_user resolvedByuser ON resolvedByuser.account=bug.resolvedBy 
                            LEFT JOIN zt_user lastEditedByuser ON lastEditedByuser.account=bug.lastEditedBy 
                            WHERE bug.deleted = '0' 
                            AND bug.status IN ('active','resolved','refused') 
                            AND bug.product = {self.product_id}"""
        if exclude_project_id:
            app_sql = app_sql + f" AND bug.project not in ({exclude_project_id})"
        if base_line:
            app_sql = app_sql + f" AND bug.baseline = '{base_line}'"
        if exclude_words:
            for i in exclude_words.split(","):
                app_sql = app_sql + f" AND bug.title not like '%{i}%'"
        if words:
            for i in words.split(","):
                app_sql = app_sql + f" AND bug.title like '%{i}%'"
        all_bugs = self.query(app_sql)

        info = {
            'di': Decimal("0"),
            'bug_list': [],
            'serious_list': [],
        }

        di_weight = {"1": "10", "2": "3", "3": "1", "4": "0.1"}

        for index, i in enumerate(all_bugs):
            if not i["branch"]:
                all_bugs[index]["branch"] = "所有"
            all_bugs[index]["module"] = "/" + i["module"] if i["module"] else "/"
            all_bugs[index]["type"] = self.__bug_type.get(i["type"], i["type"])
            all_bugs[index]["steps"] = re.sub("<.+?>", "", i["steps"])
            all_bugs[index]["status"] = self.__bug_status_map[i["status"]]
            all_bugs[index]["confirmed"] = "否" if i["confirmed"] == "0" else "是"
            if i["mailto"]:
                all_bugs[index]["mailto"] = ",".join(
                    [self.__get_realname(j) if j else "" for j in i["mailto"].split(",")]
                )
            if not i["openedBuild"]:
                all_bugs[index]["openedBuild"] = "主干"
            all_bugs[index]["linkBug"] = ""
            all_bugs[index]["case"] = ""
            if not i["duplicateBug"]:
                all_bugs[index]["duplicateBug"] = ""
            if i["resolution"]:
                all_bugs[index]["resolution"] = self.__resolution_status.get(
                    i["resolution"], i["resolution"]
                )
            if int(i['severity']) <= 2:
                info['serious_list'].append(i)
            info['di'] += Decimal(di_weight[i["severity"]])
        info['bug_list'] = all_bugs
        return ReturnAttr(info)


if __name__ == '__main__':
    # t = TaskBase(39591)
    t1 = Task(38813)
    print(t1.comment_software)
    # from src.business.cooperation_operation import Cooperation
    #
    # Cooperation(t1.product_id, t1.project_name)
    # print(t1.legacy_bugs)
