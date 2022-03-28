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

import click

from ._base import main, AliasedGroup, Resource


@main.group(cls=AliasedGroup)
def logs():
    """Interact with cloudwatch logs of a training-job, processing-job,
    endpoint, hyperparameter-tuning-job, notebook-instance or a
    transform-job."""
    pass


@logs.command()
@click.argument("arn", required=True, type=Resource)
@click.option("-n", type=int)
def head(arn, n):
    for log in arn.logs:
        click.secho(log.stream_name, bold=True, color="blue", err=True)
        for line in log.head(n=n):
            click.echo(line)
        click.echo()


@logs.command()
@click.argument("arn", required=True, type=Resource)
@click.option("-n", type=int, default=10)
@click.option("-f", "follow", is_flag=True)
@click.option("-i", "--interval", default=10)
def tail(arn, n, follow, interval):
    for log in arn.logs:
        click.secho(log.stream_name, bold=True, color="blue", err=True)
        if follow:
            lines = log.follow(limit=n, start_at_top=False, interval=interval)
        else:
            lines = log.tail(n)

        for line in lines:
            click.echo(line)
        click.echo()


@logs.command()
@click.argument("arn", required=True, type=Resource)
@click.option("-f", "follow", is_flag=True)
@click.option("-i", "--interval", default=10)
def cat(arn, follow, interval):
    for log in arn.logs:
        click.secho(log.stream_name, bold=True, color="blue", err=True)

        if follow:
            lines = log.follow(interval=interval)
        else:
            lines = log.cat()

        for line in lines:
            click.echo(line)
        click.echo()


@logs.command()
@click.option("--expression", "-e", required=True)
@click.argument("arn", required=True, type=Resource)
def filter(arn, expression):
    for name, logfilterevents in arn.logfilter.filter(expression).items():
        click.secho(name, bold=True, color="blue", err=True)
        for evt in logfilterevents:
            click.secho(evt.message)
        click.echo()
