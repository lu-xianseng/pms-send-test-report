#!/usr/bin/env python3

"""
@Author: Lu Ye
@Time: 2023/4/20 上午11:50
@Desc:
    pms数据查询
"""
import json
import requests
from src.public.log_set import log
from config import config

session = requests.Session()


class Query:

    def __init__(self):
        self.__login()

    @classmethod
    def __login(cls):
        """
        pms登录
        Returns:
            None
        """
        res = session.post(
            url="https://pms.uniontech.com/zentao/user-login.json",
            data={"account": config.pms_user, "password": config.pms_passwd}
        )
        if not res.json().get("status") == "success":
            raise Exception(res.json().get('reason'))

    @staticmethod
    def str_to_json(data):
        try:
            data = json.loads(data)
            return data
        except Exception:
            data = None
        finally:
            return data

    def unicode_to_chinese(self, data):
        if isinstance(data, str):
            return data.encode('utf-8').decode('raw_unicode_escape')
        elif isinstance(data, list):
            return [self.unicode_to_chinese(item) for item in data]
        elif isinstance(data, dict):
            return {self.unicode_to_chinese(key): self.unicode_to_chinese(value) for key, value in data.items()}
        else:
            return data

    def get_data(self, post_data):
        for _ in range(5):
            try:
                query_url = "https://pms.uniontech.com/zentao/report-custom-1-0.json"
                session.post(url=query_url, data=post_data)
                data = session.get(query_url).json()
                return self.unicode_to_chinese(data)
            except requests.exceptions.ConnectionError as e:
                raise Exception(f"请求异常：{e}")
            except json.decoder.JSONDecodeError:
                self.__login()
                continue

    def query(self, sql: str):
        sql_data = {"sql": sql}
        for _ in range(3):
            result = self.get_data(sql_data)
            if not result:
                self.__login()
                continue
            data = self.str_to_json(result.get("data"))
            return data.get("dataList")


if __name__ == "__main__":
    q = Query()
    a = q.query('SELECT task.id,task.name,product.name,task.product,task.project,project.name,task.build  FROM zt_testtask task LEFT JOIN zt_product product ON task.product=product.id LEFT JOIN zt_project project ON task.project=project.id WHERE task.id=39445')
    print(a)
