# -*- coding: utf-8 -*-
# Copyright (C) 2020 Linaro Limited
#
# Author: Stevan Radaković <stevan.radakovic@linaro.org>
#
# This file is part of LAVA.
#
# LAVA is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License version 3
# as published by the Free Software Foundation
#
# LAVA is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with LAVA.  If not, see <http://www.gnu.org/licenses/>.

import pytest
import sys

from io import StringIO
from django.core.management import call_command

from lava_scheduler_app.models import Alias, Device, DeviceType


@pytest.mark.django_db
def test_no_sync_to_lava(mocker):

    file_list = mocker.MagicMock(return_value=["qemu01"])
    mocker.patch("lava_server.files.File.list", file_list)

    sync_dict = mocker.MagicMock(return_value=None)
    mocker.patch(
        "lava_server.management.commands.sync.Command._get_sync_to_lava", sync_dict
    )

    out = StringIO()
    sys.stdout = out
    call_command("sync")
    assert (
        out.getvalue()
        == """Scanning devices:
* qemu01 [SKIP]
  -> missing 'sync_to_lava'
"""
    )


@pytest.mark.django_db
def test_invalid_template(mocker):

    file_list = mocker.MagicMock(return_value=["qemu01"])
    mocker.patch("lava_server.files.File.list", file_list)

    mocker.patch("lava_server.management.commands.sync.Command._get_sync_to_lava")

    parse_sync_dict = mocker.MagicMock(
        return_value={
            "device_type": "qemu",
            "worker": "worker-01",
            "aliases": ["foo", "bar"],
            "tags": ["one", "two"],
        }
    )
    mocker.patch(
        "lava_server.management.commands.sync.Command._parse_sync_dict", parse_sync_dict
    )

    # Do not patch jinja2.Environment.get_template so it raises error.

    out = StringIO()
    sys.stdout = out
    call_command("sync")
    assert (
        out.getvalue()
        == """Scanning devices:
* qemu01 [SKIP]
  -> invalid jinja2 template
  -> qemu01
"""
    )


@pytest.mark.django_db
def test_existing_non_synced_device(mocker):

    file_list = mocker.MagicMock(return_value=["qemu01"])
    mocker.patch("lava_server.files.File.list", file_list)

    mocker.patch("lava_server.management.commands.sync.Command._get_sync_to_lava")

    parse_sync_dict = mocker.MagicMock(
        return_value={
            "device_type": "qemu",
            "worker": "worker-01",
            "aliases": ["foo", "bar"],
            "tags": ["one", "two"],
        }
    )
    mocker.patch(
        "lava_server.management.commands.sync.Command._parse_sync_dict", parse_sync_dict
    )

    mocker.patch("jinja2.Environment.get_template")
    mocker.patch("yaml.load")

    dt = DeviceType.objects.create(name="qemu")
    Device.objects.create(hostname="qemu01", is_synced=False, device_type=dt)

    out = StringIO()
    sys.stdout = out
    call_command("sync")
    assert (
        out.getvalue()
        == """Scanning devices:
* qemu01 [SKIP]
  -> created manually
"""
    )


@pytest.mark.django_db
def test_missing_device_type(mocker):

    file_list = mocker.MagicMock(return_value=["qemu01"])
    mocker.patch("lava_server.files.File.list", file_list)

    mocker.patch("lava_server.management.commands.sync.Command._get_sync_to_lava")

    parse_sync_dict = mocker.MagicMock(
        return_value={
            "worker": "worker-01",
            "aliases": ["foo", "bar"],
            "tags": ["one", "two"],
        }
    )
    mocker.patch(
        "lava_server.management.commands.sync.Command._parse_sync_dict", parse_sync_dict
    )

    mocker.patch("jinja2.Environment.get_template")
    mocker.patch("yaml.load")

    out = StringIO()
    sys.stdout = out
    call_command("sync")
    assert (
        out.getvalue()
        == """Scanning devices:
* qemu01 [SKIP]
  -> 'device_type' is mandatory
"""
    )


@pytest.mark.django_db
def test_existing_alias(mocker):

    file_list = mocker.MagicMock(return_value=["qemu01"])
    mocker.patch("lava_server.files.File.list", file_list)

    mocker.patch("lava_server.management.commands.sync.Command._get_sync_to_lava")

    parse_sync_dict = mocker.MagicMock(
        return_value={
            "device_type": "qemu",
            "worker": "worker-01",
            "aliases": ["foo", "bar"],
            "tags": ["one", "two"],
        }
    )
    mocker.patch(
        "lava_server.management.commands.sync.Command._parse_sync_dict", parse_sync_dict
    )

    mocker.patch("jinja2.Environment.get_template")
    mocker.patch("yaml.load")

    dt = DeviceType.objects.create(name="qemu")
    Alias.objects.create(name="foo", device_type=dt)

    out = StringIO()
    sys.stdout = out
    call_command("sync")
    assert (
        out.getvalue()
        == """Scanning devices:
* qemu01
  -> create worker: worker-01
  -> alias: foo
  -> alias: bar
  -> tag: one
  -> tag: two
"""
    )


@pytest.mark.django_db
def test_output(mocker):

    file_list = mocker.MagicMock(return_value=["qemu01"])
    mocker.patch("lava_server.files.File.list", file_list)

    mocker.patch("lava_server.management.commands.sync.Command._get_sync_to_lava")

    parse_sync_dict = mocker.MagicMock(
        return_value={
            "device_type": "qemu",
            "worker": "worker-01",
            "aliases": ["foo", "bar"],
            "tags": ["one", "two"],
        }
    )
    mocker.patch(
        "lava_server.management.commands.sync.Command._parse_sync_dict", parse_sync_dict
    )

    mocker.patch("jinja2.Environment.get_template")
    mocker.patch("yaml.load")

    # Create non-related device in order to test its display value later.
    DeviceType.objects.create(name="bbb")

    out = StringIO()
    sys.stdout = out
    call_command("sync")
    assert (
        out.getvalue()
        == """Scanning devices:
* qemu01
  -> create device type: qemu
  -> create worker: worker-01
  -> alias: foo
  -> alias: bar
  -> tag: one
  -> tag: two
"""
    )

    # Test the device types display.
    assert DeviceType.objects.get(name="qemu").display
    assert DeviceType.objects.get(name="bbb").display


@pytest.mark.django_db
def test_retire(mocker):

    dt = DeviceType.objects.create(name="qemu")
    Device.objects.create(hostname="qemu01", device_type=dt, is_synced=True)

    dt = DeviceType.objects.create(name="bbb")
    Device.objects.create(hostname="bbb01", device_type=dt, is_synced=True)
    Device.objects.create(hostname="bbb02", device_type=dt, is_synced=False)

    file_list = mocker.MagicMock(return_value=[])
    mocker.patch("lava_server.files.File.list", file_list)

    out = StringIO()
    sys.stdout = out
    call_command("sync")

    assert Device.objects.get(hostname="qemu01").health == Device.HEALTH_RETIRED
    assert not DeviceType.objects.get(name="qemu").display

    assert Device.objects.get(hostname="bbb01").health == Device.HEALTH_RETIRED
    assert Device.objects.get(hostname="bbb02").health == Device.HEALTH_MAINTENANCE
    assert DeviceType.objects.get(name="bbb").display
