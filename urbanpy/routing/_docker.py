"""Injectable, shell-free Docker command execution for OSRM."""

import json
import subprocess
from dataclasses import dataclass
from typing import Protocol, Sequence

from urbanpy.errors import UrbanPyError


class DockerError(UrbanPyError):
    """Base class for local Docker lifecycle failures."""


class DockerUnavailableError(DockerError):
    """The Docker CLI or daemon is unavailable."""


class DockerCommandError(DockerError):
    """A Docker command failed with sanitized diagnostic output."""

    def __init__(
        self, command: Sequence[str], returncode: int, stderr: str = ""
    ) -> None:
        self.command = tuple(command)
        self.returncode = returncode
        self.stderr = stderr[-2000:]
        executable = command[0] if command else "docker"
        super().__init__(f"{executable} command failed with exit code {returncode}.")


class DockerTimeoutError(DockerError):
    """A Docker command exceeded its explicit deadline."""


class CommandRunner(Protocol):
    def run(
        self,
        command: Sequence[str],
        *,
        timeout: float,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]: ...


@dataclass(frozen=True, slots=True)
class SubprocessRunner:
    """Run argument arrays with ``shell=False`` and captured diagnostics."""

    def run(
        self,
        command: Sequence[str],
        *,
        timeout: float,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        try:
            completed = subprocess.run(
                list(command),
                capture_output=True,
                check=False,
                shell=False,
                text=True,
                timeout=timeout,
            )
        except FileNotFoundError as error:
            raise DockerUnavailableError(
                "Docker CLI was not found; install Docker and ensure it is on PATH."
            ) from error
        except subprocess.TimeoutExpired as error:
            raise DockerTimeoutError(
                f"Docker command exceeded its {timeout:g}-second timeout."
            ) from error
        if check and completed.returncode != 0:
            raise DockerCommandError(command, completed.returncode, completed.stderr)
        return completed


def inspect_container(
    runner: CommandRunner, name: str, *, timeout: float
) -> dict[str, object] | None:
    result = runner.run(
        ["docker", "inspect", "--format", "{{json .}}", name],
        timeout=timeout,
        check=False,
    )
    if result.returncode != 0:
        return None
    try:
        value = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise DockerCommandError(
            ["docker", "inspect", name], 0, "Docker returned invalid inspect JSON."
        ) from error
    if not isinstance(value, dict):
        raise DockerCommandError(
            ["docker", "inspect", name], 0, "Docker inspect JSON is not an object."
        )
    return value


__all__ = [
    "CommandRunner",
    "DockerCommandError",
    "DockerError",
    "DockerTimeoutError",
    "DockerUnavailableError",
    "SubprocessRunner",
    "inspect_container",
]
