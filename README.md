# Sage-Inspector


[![PyPI](https://img.shields.io/pypi/v/sageinspector.svg?style=flat-square)](https://pypi.org/project/sageinspector/)
[![GitHub](https://img.shields.io/github/license/awslabs/sageinspector.svg?style=flat-square)](./LICENSE)

A tool to inspect SageMaker resources more easily.

### CLI

`Sage-Inspector` provides an `si` command to quickly access resources such as logs.

Example:

    $ si logs tail -n 20 arn:aws:sagemaker:us-west-2:123456789012:training-job/my-job


### Authentication

When using `si`, the tool searches `~/.aws/config` for the account-id of the
provided arn.

For example, the below section would match for the arn used above, and thus
`si` would use `boto3.Session(profilen_name="my_account")` internally.

```
[profile my-account]
account = 123456789012
```

If it can't find account information, sage-inspector falls back to a default
session.
