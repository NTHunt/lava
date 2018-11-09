# -*- coding: utf-8 -*-
# Copyright (C) 2010-2018 Linaro Limited
#
# Author: Neil Williams <neil.williams@linaro.org>
#         Remi Duraffort <remi.duraffort@linaro.org>
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

"""
Obtain or generate secret key on first use.
"""

import random

from lava_server.settings.config_file import ConfigFile


def _make_secret_key():
    """
    Generate a value that can be used as SECRET_KEY in Django settings
    """
    return "".join(
        [
            random.SystemRandom().choice(
                "abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)"
            )
            for i in range(50)
        ]
    )


def _write_secret_key(pathname, secret_key):
    """
    Write a configuration file with the specified key
    """
    with open(pathname, "w") as stream:
        stream.write(
            """
# This file was automatically generated by the lava_server.settings package, upon
# first access, by the application that attempted to load it.  You can
# regenerate it at any time by removing this file or the SECRET_KEY variable
# defined below

# This key is used by Django to ensure the security of various cookies and
# one-time values. To learn more please visit:
# http://docs.djangoproject.com/en/1.2/ref/settings/#secret-key.

# Note: DO NOT PUBLISH THIS FILE.

SECRET_KEY='%s'
"""
            % secret_key
        )


def get_secret_key(pathname):
    """
    Get Django secret key value from a file _or_ generate it on first use
    """
    try:
        return ConfigFile.load(pathname).SECRET_KEY
    except (AttributeError, OSError, ValueError) as ex:
        _write_secret_key(pathname, _make_secret_key())
    return ConfigFile.load(pathname).SECRET_KEY
