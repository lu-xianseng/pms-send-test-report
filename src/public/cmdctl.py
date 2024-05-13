#!/usr/bin/env python3
# _*_ coding:utf-8 _*_
"""
:Author: huangmingqiang@uniontech.com
:Date: 2021/10/28 下午6:14
"""
import subprocess
from src.public.log_set import log


class CmdCtl:
    """命令行工具"""

    # pylint: disable=too-many-arguments,too-many-locals,too-many-public-methods

    @staticmethod
    def _run(command, _input=None, timeout=None, check=False, **kwargs):
        """run"""
        with subprocess.Popen(command, **kwargs) as process:
            try:
                stdout, stderr = process.communicate(_input, timeout=timeout)
            except:  # Including KeyboardInterrupt, communicate handled that.
                process.kill()
                raise
            retcode = process.poll()
            if check and retcode:
                raise subprocess.CalledProcessError(
                    retcode, process.args, output=stdout, stderr=stderr
                )
        return subprocess.CompletedProcess(process.args, retcode, stdout, stderr)

    @classmethod
    def _getstatusoutput(cls, command, timeout):
        """getstatusoutput"""
        try:
            result = cls._run(
                command,
                shell=True,
                text=True,
                stderr=subprocess.STDOUT,
                stdout=subprocess.PIPE,
                timeout=timeout,
            )
            data = result.stdout
            exitcode = result.returncode
        except subprocess.CalledProcessError as ex:
            data = ex.output
            exitcode = ex.returncode
        except subprocess.TimeoutExpired as ex:
            # pylint: disable=unnecessary-dunder-call
            data = ex.__str__()
            exitcode = -1
        if data[-1:] == "\n":
            data = data[:-1]
        return exitcode, data

    @classmethod
    def run_cmd(
        cls, command, interrupt=True, timeout=25, out_debug_flag=True, command_log=True
    ):
        """
         执行shell命令
        :param command: shell 命令
        :param interrupt: 命令异常时是否中断
        :param timeout: 命令执行超时
        :param out_debug_flag: 命令返回信息输出日志
        :param command_log: 执行的命令字符串日志
        :return: 返回终端输出
        """
        status, out = cls._getstatusoutput(command, timeout=timeout)
        if command_log:
            log.debug(command)
        if status and interrupt:
            raise ValueError(out)
        if out_debug_flag and out:
            log.debug(out)
        return out
