# Copyright 2022 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License").
# You may not use this file except in compliance with the License.
# A copy of the License is located at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# or in the "license" file accompanying this file. This file is distributed
# on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either
# express or implied. See the License for the specific language governing
# permissions and limitations under the License.

import configparser
import re
import os
from pathlib import Path


ACCOUNT_ID_RE = re.compile(r"\b(\d{12})\b")

config_file = Path(
    os.environ.get("AWS_CONFIG_FILE", "~/.aws/config")
).expanduser()


def _get_profiles(config):
    for key, settings in config.items():
        if key == "default":
            yield key, dict(settings)

        elif key.startswith("profile "):
            name = key.split(" ", 1)[1]
            yield name, dict(settings)


def _find_account_id(settings):
    for value in settings.values():
        for match in ACCOUNT_ID_RE.finditer(value):
            return match.group(0)


def get_account_for_profiles(profiles):
    accounts = {}

    for profile, settings in profiles.items():
        account = _find_account_id(settings)
        if account is not None and account not in accounts:
            accounts[account] = profile

    return accounts


class Config:
    @classmethod
    def read(cls, path=config_file):
        path = Path(path)

        config = configparser.ConfigParser()

        if path.is_file():
            config.read(path)
        return cls(path, config)

    def __init__(self, path, config):
        self.path = path
        self.config = config
        self.profiles = dict(_get_profiles(config))
        self.accounts = get_account_for_profiles(self.profiles)
