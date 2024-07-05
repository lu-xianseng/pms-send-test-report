import re

from src.public.cmdctl import CmdCtl
from src.public.log_set import log
from src.business.cooperation_operation import Cooperation
from config import config


class MachineInfo:
    def __init__(self, app_name: list, machine_ip: list, source_hardware: list, source_package: list):
        self.app_names = app_name
        self.machine_ip = machine_ip
        self.source_hardware = source_hardware
        self.source_package = source_package

    @staticmethod
    def _remote_cmd(
            ip,
            command,
            interrupt=True,
            timeout=25,
            out_debug_flag=True,
            command_log=True,
            password=False,
    ):
        users = ['uos']
        passwords = ['1', 'Qwer1234']
        commands = []

        for user in users:
            for passwd in passwords:
                _cmd = f"sshpass -p {passwd} ssh {user}@{ip} "
                _cmd += f'''"echo '{passwd}' | sudo -S {command}"''' if password else f'"{command} 2>/dev/null"'
                commands.append(_cmd)

        for cmd in commands:
            try:
                return CmdCtl.run_cmd(
                    cmd,
                    interrupt=interrupt,
                    timeout=timeout,
                    out_debug_flag=out_debug_flag,
                    command_log=command_log,
                )
            except ValueError:
                continue
        raise ConnectionError(f"测试机:{ip}，无法链接，或命令有误， {command}")

    def get_test_machine_info(self):
        if not self.machine_ip:
            return []
        CmdCtl.run_cmd("rm -rf ~/.ssh/known_hosts")
        CmdCtl.run_cmd(
            "echo asd | sudo -S sudo sed -i 's/#   "
            "StrictHostKeyChecking ask/   StrictHostKeyChecking no/g' /etc/ssh/ssh_config"
        )
        machine_info = []
        for ip in self.machine_ip:
            info = {
                "hardware": self.get_hardware_env(ip),
                "software": self.get_software_env(ip),
                "apps": self.get_app_version(ip),
                "image": self.get_image_mirror_version(ip)
            }
            machine_info.append(info)
        return machine_info

    def get_app_version(self, ip):
        CmdCtl.run_cmd("rm -rf ~/.ssh/known_hosts")
        CmdCtl.run_cmd(
            "echo asd | sudo -S sudo sed -i 's/#   "
            "StrictHostKeyChecking ask/   StrictHostKeyChecking no/g' /etc/ssh/ssh_config"
        )

        app_version = {}
        for app in self.app_names:
            if self.source_package[app]:
                app_version.update({app: self.source_package[app]})
            try:
                version = self._remote_cmd(ip, f"dpkg -l {app}|grep ^ii|awk '{{print \$3}}'")
                app_version.update({app: version.split('\n')[-1]})
            except ConnectionError:
                break
        return app_version

    def get_hardware_env(self, ip):

        product_name = self._remote_cmd(
            ip, "dmidecode 2> /dev/null|grep 'Product Name'", password=True
        )
        for hardware in self.source_hardware:
            if hardware["board"] in product_name:
                info = {
                    "cpu": hardware.get("cpu"),
                    "mem": hardware.get("mem"),
                    "gpu": hardware.get("gpu"),
                    "hard": hardware.get("hard"),
                    "net": hardware.get("net")
                }
                log.info(info)
                return info
        else:
            msg = f"{ip},无对应机器的硬件配置，请联系管理员添加，或自行上明道云添加"
            log.error(msg)
            raise TypeError(msg)

    def get_software_env(self, ip):
        assembly = self._remote_cmd(ip, "uname -m")
        kernel = self._remote_cmd(ip, "uname -a")
        sys_version = self._remote_cmd(ip, "cat /etc/product-info")
        build_time = re.findall("[0-9]{5,}", sys_version)
        minor_version = self._remote_cmd(
            ip,
            f"""cat /etc/os-version 2>/dev/null|grep 'MinorVersion=' |cut -d'=' -f2""",
        )
        system_name = self._remote_cmd(
            ip,
            f"""cat /etc/os-version 2>/dev/null|grep 'SystemName=' |cut -d'=' -f2""",
        )
        return {
            "assembly": assembly,
            "kernel": kernel,
            "image": f"{system_name}-{minor_version}-{build_time[0]}-{assembly}",
        }

    def get_image_mirror_version(self, ip):
        line = self._remote_cmd(
            ip,
            f"""cat /etc/os-version 2>/dev/null|grep 'EditionName\[zh_CN\]=' |cut -d'=' -f2""",
        )
        mirror = self._remote_cmd(
            ip,
            f"""cat /etc/os-version 2>/dev/null|grep 'MajorVersion=' |cut -d'=' -f2""",
        )
        minor_version = self._remote_cmd(
            ip,
            f"""cat /etc/os-version 2>/dev/null|grep 'MinorVersion=' |cut -d'=' -f2""",
        )
        image = f"V{mirror}{line}{minor_version}"
        return re.sub(r"\(.+?\)", "", image)


if __name__ == '__main__':
    a = MachineInfo(app_names=['deepin-music', 'deepin-movie'], machines=['10.8.11.37', "10.8.12.14"])
    config.Global_PMS["all_package_info"] = {'deepin-music': '', 'deepin-movie': ''}
    from pprint import pprint

    # pprint(a.get_test_machine_info())
    for machine in a.get_test_machine_info():
        app_height = version_height = len(machine.get("apps")) or 1
        replacements = {
            "{{CPU}}": machine.get("hardware").get("cpu"),
            "{{内存}}": machine.get("hardware").get("mem"),
            "{{显卡}}": machine.get("hardware").get("gpu"),
            "{{硬盘}}": machine.get("hardware").get("hard"),
            "{{网卡}}": machine.get("hardware").get("net"),
            "{{组件}}": machine.get("software").get("assembly"),
            "{{内核}}": machine.get("software").get("kernel"),
            "{{系统}}": machine.get("software").get("image"),
            "{{version}}": "\n".join(machine.get("apps").keys()),
            "{{package}}": "\n".join(machine.get("apps").values()),
        }
        pprint(replacements)
