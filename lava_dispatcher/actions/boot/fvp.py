# Copyright (C) 2019 Arm Limited
#
# Author: Dean Arnold <dean.arnold@arm.com>
#
# This file is part of LAVA Dispatcher.
#
# LAVA Dispatcher is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# LAVA Dispatcher is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along
# with this program; if not, see <http://www.gnu.org/licenses>.

import os
import time

from lava_common.exceptions import JobError
from lava_dispatcher.action import Pipeline, Action
from lava_dispatcher.logical import Boot
from lava_dispatcher.actions.boot import BootAction, AutoLoginAction
from lava_dispatcher.shell import ExpectShellSession, ShellCommand, ShellSession


class BootFVP(Boot):
    compatibility = 4

    def __init__(self, parent, parameters):
        super().__init__(parent)
        self.action = BootFVPAction()
        self.action.section = self.action_type
        self.action.job = self.job
        parent.add_action(self.action, parameters)

    @classmethod
    def accepts(cls, device, parameters):
        if "fvp" not in device["actions"]["boot"]["methods"]:
            return False, '"fvp" was not in the device configuration boot methods'
        if parameters["method"] != "fvp":
            return False, '"method" was not "fvp"'
        if "image" not in parameters:
            return False, '"image" was not in boot parameters'
        return True, "accepted"


class BootFVPAction(BootAction):

    name = "boot-fvp"
    description = "boot fvp"
    summary = "boot fvp"

    def populate(self, parameters):
        self.pipeline = Pipeline(parent=self, job=self.job, parameters=parameters)
        self.pipeline.add_action(BootFVPMain())
        if self.has_prompts(parameters):
            self.pipeline.add_action(AutoLoginAction())
            if self.test_has_shell(parameters):
                self.pipeline.add_action(ExpectShellSession())


class BootFVPMain(Action):

    name = "boot-fvp-main"
    description = "boot fvp"
    summary = "boot fvp"

    def populate(self, parameters):
        self.pipeline = Pipeline(parent=self, job=self.job, parameters=parameters)
        self.pipeline.add_action(CheckFVPVersionAction())
        self.pipeline.add_action(StartFVPAction())
        self.pipeline.add_action(GetFVPSerialAction())


class BaseFVPAction(Action):

    name = "base-fvp-action"
    description = "call docker run with fvp entry point"
    summary = "base fvp action"

    def __init__(self):
        super().__init__()
        self.cleanup_required = False
        self.extra_options = ""
        self.container = ""
        self.fvp_image = None
        self.fvp_license = None
        self.docker_image = None
        self.local_docker_image = False

    def validate(self):
        super().validate()
        self.container = "lava-%s-%s" % (self.job.job_id, self.level)
        if "docker" not in self.parameters or "name" not in self.parameters["docker"]:
            self.errors = "Specify docker image name"
            raise JobError("Not specified 'docker' in parameters")
        self.docker_image = self.parameters["docker"]["name"]
        self.local_docker_image = self.parameters["docker"].get("local", False)

        options = self.job.device["actions"]["boot"]["methods"]["fvp"]["options"]

        if options["cpus"]:
            self.extra_options += " --cpus %s" % options["cpus"]
        if options["memory"]:
            self.extra_options += " --memory %s" % options["memory"]
        if options.get("privileged", False):
            self.extra_options += " --privileged"
        for device in options.get("devices", []):
            self.extra_options += " --device %s" % device
        for volume in options.get("volumes", []):
            self.extra_options += " --volume %s" % volume
        if "fvp_license_variable" in self.parameters:
            self.fvp_license = self.parameters["fvp_license_variable"]

    def construct_docker_fvp_command(self, docker_image, fvp_arguments):
        substitutions = {}
        cmd = "docker run --rm --interactive --tty --hostname lava"
        cmd += " --name %s" % self.container
        self.logger.debug(
            "Download action namespace keys are: %s",
            self.get_namespace_keys("download-action"),
        )
        for label in self.get_namespace_keys("download-action"):
            filename = self.get_namespace_data(
                action="download-action", label=label, key="file"
            )
            if label == "ramdisk":
                ramdisk = self.get_namespace_data(
                    action="compress-ramdisk", label="file", key="full-path"
                )
                # If overlay has been copied into the ramdisk, use that
                if ramdisk:
                    filename = ramdisk
            if filename is None:
                self.logger.warning(
                    "Empty value for action='download-action' label='%s' key='file'",
                    label,
                )
                continue

            location_in_container = self.fvp_image = os.path.join(
                "/", self.container, os.path.basename(filename)
            )
            substitutions[label.upper()] = location_in_container

            # Add downloaded images to container, ensuring they are all in a single
            # directory.  This is required for FVP libraries.
            cmd += " --volume %s:%s" % (filename, location_in_container)

        substitutions["ARTIFACT_DIR"] = os.path.join("/", self.container)
        if not self.fvp_license:
            self.logger.warning(
                "'fvp_license_variable' not set, model may not function."
            )
        else:
            cmd += " -e %s" % self.fvp_license
        fvp_image = self.parameters.get("image")
        cmd += self.extra_options
        cmd += " %s %s %s" % (docker_image, fvp_image, fvp_arguments)
        cmd = cmd.format(**substitutions)
        return cmd

    def cleanup(self, connection):
        super().cleanup(connection)
        self.logger.debug("Stopping container %s", self.container)
        return_value = self.run_cmd(["docker", "stop", self.container], allow_fail=True)
        if return_value == 0:
            self.logger.debug("Stopped container %s", self.container)
        self.cleanup_required = False


class CheckFVPVersionAction(BaseFVPAction):
    name = "check-fvp-version"
    description = "call docker run with fvp version entry point"
    summary = "check fvp version"

    def __init__(self):
        super().__init__()
        self.cleanup_required = False
        self.extra_options = ""
        self.container = ""
        self.fvp_image = None
        self.fvp_version_string = ""

    def validate(self):
        super().validate()
        self.fvp_version_string = self.parameters.get(
            "fvp_version_string", "Fast Models[^\\n]+"
        )

    def run(self, connection, max_end_time):
        start = time.time()

        if not self.local_docker_image:
            self.logger.debug("Pulling image %s", self.docker_image)
            self.run_cmd(["docker", "pull", self.docker_image])

        fvp_arguments = self.parameters.get("fvp_version_args", "--version")

        # Build the command line
        # The docker image is safe to be included in the command line
        cmd = self.construct_docker_fvp_command(self.docker_image, fvp_arguments)

        self.logger.debug("Boot command: %s", cmd)
        shell = ShellCommand(cmd, self.timeout, logger=self.logger)
        self.cleanup_required = True

        shell_connection = ShellSession(self.job, shell)
        shell_connection = super().run(shell_connection, max_end_time)

        # Wait for the version
        shell_connection.prompt_str = self.fvp_version_string
        self.wait(shell_connection)
        matched_version_string = shell_connection.raw_connection.match.group()
        result = {
            "definition": "lava",
            "case": "fvp-version",
            "level": self.level,
            "extra": {"fvp-version": matched_version_string},
            "result": "pass",
            "duration": "%.02f" % (time.time() - start),
        }
        self.logger.results(result)

        self.set_namespace_data(
            action="shared", label="shared", key="connection", value=shell_connection
        )
        return shell_connection


class StartFVPAction(BaseFVPAction):
    name = "run-fvp"
    description = "call docker run with fvp boot entry point"
    summary = "run fvp model"

    def __init__(self):
        super().__init__()
        self.cleanup_required = False
        self.extra_options = ""
        self.container = ""
        self.fvp_image = None
        self.fvp_console_string = ""

    def validate(self):
        super().validate()
        if "console_string" not in self.parameters:
            self.errors = "'console_string' is not set."
        else:
            self.fvp_console_string = self.parameters.get("console_string")
        if "fvp_arguments" not in self.parameters:
            self.errors = "'fvp_arguments' is not set."

    def run(self, connection, max_end_time):
        fvp_arguments = " ".join(self.parameters.get("fvp_arguments"))

        # Build the command line
        # The docker image is safe to be included in the command line
        cmd = self.construct_docker_fvp_command(self.docker_image, fvp_arguments)

        self.logger.debug("Boot command: %s", cmd)
        shell = ShellCommand(cmd, self.timeout, logger=self.logger)
        self.cleanup_required = True

        shell_connection = ShellSession(self.job, shell)
        shell_connection = super().run(shell_connection, max_end_time)

        # Wait for the console string
        shell_connection.prompt_str = self.fvp_console_string
        self.wait(shell_connection)
        # We should now have the matched output
        if "PORT" not in shell_connection.raw_connection.match.groupdict():
            raise JobError(
                "'console_string' should contain a regular expression section, such as '(?P<PORT>\\d+)' to extract the serial port of the FVP. Group name must be 'PORT'"
            )

        serial_port = shell_connection.raw_connection.match.groupdict()["PORT"]
        self.set_namespace_data(
            action=StartFVPAction.name,
            label="fvp",
            key="serial_port",
            value=serial_port,
        )
        self.logger.info("Found FVP port %s", serial_port)
        self.set_namespace_data(
            action=StartFVPAction.name,
            label="fvp",
            key="container",
            value=self.container,
        )
        self.set_namespace_data(
            action="shared", label="shared", key="connection", value=shell_connection
        )
        return shell_connection


class GetFVPSerialAction(Action):
    name = "fvp-serial-connect"
    description = "connect to the fvp serial connection via telnet"
    summary = "connect to the fvp serial output"

    def run(self, connection, max_end_time):
        serial_port = self.get_namespace_data(
            action=StartFVPAction.name, label="fvp", key="serial_port"
        )
        container = self.get_namespace_data(
            action=StartFVPAction.name, label="fvp", key="container"
        )
        cmd = "docker exec --interactive --tty %s telnet localhost %s" % (
            container,
            serial_port,
        )

        self.logger.debug("Connect command: %s", cmd)
        shell = ShellCommand(cmd, self.timeout, logger=self.logger)

        shell_connection = ShellSession(self.job, shell)
        shell_connection = super().run(shell_connection, max_end_time)

        self.set_namespace_data(
            action="shared", label="shared", key="connection", value=shell_connection
        )
        return shell_connection
