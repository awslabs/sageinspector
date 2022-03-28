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

import webbrowser
from urllib.parse import quote_plus

import click

from ..lib import Resource
from ._base import main, Arn


print_help = "Print link instead of opening it in the browser."


@main.command()
@click.argument("arn", required=True, type=Arn)
@click.option("--print", "-p", "print_", is_flag=True, help=print_help)
def open(arn, federate, print_):
    """Open a SageMaker training-job or HPO-job in the browser.

    ::

        si open arn:aws:sagemaker:us-east-1:123456789012:training-job/job-name

    The -p/--print option just prints the link, instead of opening it.
    """

    ResourceKind = Resource.class_for_arn(arn)

    destination = (
        f"sagemaker/home?region={arn.region}"
        f"#/{ResourceKind.url_prefix}/{arn.resource_id}"
    )

    url = f"https://{arn.region}.console.aws.amazon.com/{destination}"

    if print_:
        click.echo(url)
    else:
        webbrowser.open(url)
