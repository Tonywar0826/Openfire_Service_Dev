"""远程连接器：抽象 + 本机/SSH 实现（Agent/Docker TLS 后续接入）。

SSH 用系统 ssh/sshpass 命令（不依赖 paramiko，避免 cryptography 编译）。
"""
from __future__ import annotations

import shutil
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path


class Connector(ABC):
    """连接器抽象：部署平台通过它对目标服务器执行命令/传文件。"""

    @abstractmethod
    def run(self, cmd: str, workdir: str | None = None) -> tuple[int, str]:
        """执行命令，返回 (exit_code, output)。"""

    @abstractmethod
    def put_text(self, content: str, remote_path: str) -> None:
        """写入文本文件到目标服务器。"""


class LocalConnector(Connector):
    """本机连接器：直接在本机执行（P0 本地部署验证用）。"""

    def run(self, cmd: str, workdir: str | None = None) -> tuple[int, str]:
        try:
            r = subprocess.run(
                cmd, shell=True, cwd=workdir, capture_output=True, text=True, timeout=600
            )
            return r.returncode, (r.stdout or "") + (r.stderr or "")
        except subprocess.TimeoutExpired:
            return -1, "命令执行超时（>600s）"

    def put_text(self, content: str, remote_path: str) -> None:
        p = Path(remote_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")


class SshConnector(Connector):
    """SSH 连接器：通过系统 ssh 命令远程执行（密码用 sshpass，密钥用 -i）。"""

    def __init__(self, host: str, port: int = 22, user: str = "root",
                 password: str | None = None, key: str | None = None):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.key = key

    def _ssh(self) -> list[str]:
        """构建 ssh 命令前缀。"""
        return [
            "ssh",
            "-o", "StrictHostKeyChecking=no",
            "-o", "ConnectTimeout=15",
            "-p", str(self.port),
        ] + (["-i", self.key] if self.key else []) + [f"{self.user}@{self.host}"]

    def _run_remote(self, remote_cmd: str, input_text: str | None = None) -> tuple[int, str]:
        if self.password:
            if not shutil.which("sshpass"):
                return -1, "SSH 密码认证需要 sshpass（本机未安装），请改用密钥认证"
            cmd = ["sshpass", "-p", self.password] + self._ssh() + [remote_cmd]
        else:
            cmd = self._ssh() + [remote_cmd]
        try:
            r = subprocess.run(cmd, input=input_text, capture_output=True, text=True, timeout=600)
            return r.returncode, (r.stdout or "") + (r.stderr or "")
        except subprocess.TimeoutExpired:
            return -1, "SSH 命令执行超时（>600s）"

    def run(self, cmd: str, workdir: str | None = None) -> tuple[int, str]:
        remote = f"cd {workdir} && {cmd}" if workdir else cmd
        return self._run_remote(remote)

    def put_text(self, content: str, remote_path: str) -> None:
        remote = f"mkdir -p \"$(dirname {remote_path})\" && cat > {remote_path}"
        code, out = self._run_remote(remote, input_text=content)
        if code != 0:
            raise RuntimeError(f"上传文件失败: {out}")


def get_connector(target: dict | None) -> Connector:
    """根据目标服务器配置返回对应连接器。

    P0：connection_type=ssh 走 SSH；其余（agent/docker_tls/未指定）暂回退本机。
    """
    if target and target.get("connection_type") == "ssh":
        return SshConnector(
            host=target["host"],
            port=int(target.get("ssh_port") or 22),
            user=target.get("ssh_user") or "root",
            password=target.get("ssh_password"),
            key=target.get("ssh_key"),
        )
    return LocalConnector()
