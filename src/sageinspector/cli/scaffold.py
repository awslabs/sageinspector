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

import json
from pathlib import Path, PurePath
from urllib.parse import urlparse

import click
from toolz import valmap

from sageinspector import env
from ._base import main, Resource


def get_data_channels(description):
    return {
        channel["ChannelName"]: channel["DataSource"]["S3DataSource"]["S3Uri"]
        for channel in description["InputDataConfig"]
    }


@main.command()
@click.option("--arn", type=Resource)
@click.argument("destination", type=click.Path())
def scaffold(arn, destination):
    """Generate a scaffold for a training job."""
    if arn is not None:
        hyperparameters = arn._description["HyperParameters"]
        channels = get_data_channels(arn._description)
    else:
        hyperparameters = {}
        channels = {"train": None, "test": None}

    destination = Path(destination)
    make_config(destination, hyperparameters, channels)
    download_data(destination, channels)


def make_config(destination, hyperparameters, channels):
    config = destination / "input" / "config"
    config.mkdir(parents=True, exist_ok=True)

    # hyperparameters
    hyperparameters = valmap(str, hyperparameters)
    with open(config / "hyperparameters.json", "w") as hp_file:
        json.dump(hyperparameters, hp_file)

    # inputdataconfig
    input_data_config = {
        channel: {"ContentType": "auto"} for channel in channels
    }
    with open(config / "inputdataconfig.json", "w") as idc_file:
        json.dump(input_data_config, idc_file)


def download_data(destination, channels):
    data = destination / "input" / "data"
    data.mkdir(parents=True, exist_ok=True)

    for channel_name, s3path in channels.items():
        channel_path = data / channel_name
        channel_path.mkdir(exist_ok=True)

        if s3path is not None:
            download_files(s3path, channel_path)


def download_files(s3path, channel_path):
    s3 = env.boto_session.resource("s3")

    url = urlparse(s3path)
    bucket = s3.Bucket(url.netloc)
    path = url.path.lstrip("/")

    for path in bucket.objects.filter(Prefix=path):
        name = PurePath(path.key).name

        bucket.download_file(path.key, str(channel_path / name))
