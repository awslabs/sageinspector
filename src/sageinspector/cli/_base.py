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

import re

import boto3
import click

import sageinspector


class ArnParamType(click.ParamType):
    name = "arn"

    def convert(self, value, param, ctx):
        try:
            return sageinspector.Arn.parse(value)

        except AssertionError:
            self.fail(f"{value!r} is not a valid arn", param, ctx)


Arn = ArnParamType()


class ResourceParamType(click.ParamType):
    name = "resource"

    def convert(self, value, param, ctx):
        try:
            arn = sageinspector.Arn.parse(value)

            profile = sageinspector.env.aws_config.accounts.get(arn.account)

            sageinspector.env._push(
                boto_session=boto3.Session(
                    profile_name=profile, region_name=arn.region
                )
            )

            return sageinspector.Resource.from_arn(arn)

        except AssertionError:
            self.fail(f"{value!r} is not a valid arn", param, ctx)


Resource = ResourceParamType()


class AliasedGroup(click.Group):
    def get_command(self, ctx, cmd_name):
        rv = click.Group.get_command(self, ctx, cmd_name)
        if rv is not None:
            return rv
        matches = [
            x for x in self.list_commands(ctx) if x.startswith(cmd_name)
        ]
        if not matches:
            return None
        elif len(matches) == 1:
            return click.Group.get_command(self, ctx, matches[0])

        ctx.fail(
            f"Too many matches `{cmd_name}` could mean: \n"
            + "\n".join([f"  * {match}" for match in sorted(matches)])
        )


@click.group(cls=AliasedGroup)
def main():
    pass
