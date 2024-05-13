import os
import shutil
import svn
import svn.remote
import svn.exception
from src.public.log_set import log
from config import config


class SVNReport:
    def __init__(self, svn_base_url):
        self.svn_username = config.svn_user
        self.svn_password = config.svn_passwd
        self.svn_base_url = svn_base_url
        self.tmp_path = os.path.join("/tmp", "svn_reports")
        if not os.path.exists(self.tmp_path) or not os.path.isdir(self.tmp_path):
            os.makedirs(os.path.expanduser(self.tmp_path))

    def checkout_svn_file(self):
        svn_url = self.svn_base_url.replace(" ", "%20")
        # 将目录checkout下来
        svn_client = svn.remote.RemoteClient(
            svn_url, username=self.svn_username, password=self.svn_password
        )
        try:
            svn_client.checkout(os.path.expanduser(self.tmp_path))
        except svn.exception.SvnException as e:
            raise Exception(f"svn归档失败：{e}")

    # 执行提交操作
    def commit_report_file(self, local_file):
        log.info("归档svn")
        # 如果本地文件不存在，就不用提交了
        local_file = os.path.expanduser(local_file)
        if os.path.exists(local_file) and os.path.isfile(local_file):
            shutil.copy(local_file, self.tmp_path)
            local_file = os.path.join(self.tmp_path, os.path.split(local_file)[-1])
        else:
            raise Exception("要向SVN仓库提交的本地文件不存在")
        # 提交SVN报告
        svn_url = self.svn_base_url.replace(" ", "%20")
        svn_client = svn.remote.RemoteClient(
            svn_url, username=self.svn_username, password=self.svn_password
        )
        # 先执行add操作
        svn_sub_command_add = "add"
        command_args_add = ["--force", local_file]
        svn_client.run_command(svn_sub_command_add, command_args_add)
        # 再执行commit操作
        svn_sub_command_commit = "commit"
        command_args_commit = [
            local_file,
            "-m",
            "python3程序提交文件：" + os.path.split(local_file)[-1],
        ]
        svn_client.run_command(svn_sub_command_commit, command_args_commit)
        log.info("svn归档成功！")

    def __del__(self):
        shutil.rmtree(self.tmp_path)
