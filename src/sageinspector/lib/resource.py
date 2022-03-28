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
from typing import List

from toolz import dissoc

from .. import env
from ..util import ignore_nones

from .arn import Arn
from .logs import LogStream, LogStreamFilter, TextFilter


def snake_case(s, sep="_"):
    """Tranform a string from CamelCase to snake_case.

    >>> snake_case("TrainingJob")
    "training_job"

    """
    return re.sub(r"(?<!^)(?=[A-Z])", sep, s).lower()


class Resource:
    _resource_map = {}

    def __init_subclass__(cls, *args, **kwargs):
        cls._resource_map[cls.arn_resource_name()] = cls
        return cls

    @classmethod
    def class_for_arn(cls, arn):
        return cls._resource_map[arn.resource_type]

    @classmethod
    @env._inject("sagemaker", "cw_logs")
    def from_arn(cls, arn, *, sagemaker, cw_logs):
        if isinstance(arn, str):
            arn = Arn.parse(arn)

        ty = cls.class_for_arn(arn)

        return ty.from_name(
            arn.resource_id, sagemaker=sagemaker, cw_logs=cw_logs
        )

    @classmethod
    def kind(cls):
        # E.g. `TrainingJob` for `class TrainingJob`
        return cls.__name__

    @classmethod
    def arn_resource_name(cls):
        # E.g. `training-job` for `class TrainingJob`
        return snake_case(cls.kind(), "-")

    @classmethod
    def name_field(cls):
        # E.g. `TrainingJobName` for `class TrainingJob`
        return f"{cls.kind()}Name"

    @classmethod
    def Arn(cls, name, *, account, region):
        return Arn(
            service="sagemaker",
            region=region,
            account=account,
            resource=f"{cls.arn_resource_name()}/{name}",
        )

    @classmethod
    def _describe(cls, name, sagemaker):
        describe_op = f"describe_{snake_case(cls.kind())}"
        describe_fn = getattr(sagemaker, describe_op)
        return describe_fn(**{cls.name_field(): name})

    def log_group_name(self):
        return f"/aws/sagemaker/{self.kind()}s"

    @classmethod
    @env._inject("sagemaker", "cw_logs")
    def from_name(cls, name, *, sagemaker, cw_logs):
        "Calls `describe` using `name`."
        return cls(
            cls._describe(name, sagemaker),
            sagemaker=sagemaker,
            cw_logs=cw_logs,
        )

    def __init__(self, description, *, sagemaker: object, cw_logs: object):
        self._description = description
        self._sagemaker = sagemaker
        self._cw_logs = cw_logs
        self._log_streams = None

    @property
    def name(self):
        return self._description[self.name_field()]

    def description(self, full=False):

        omit_fields = ["ResponseMetadata"]
        if not full:
            omit_fields += self.description_omit_fields()

        description = dissoc(self._description, *omit_fields)
        return self.postprocess_description(description)

    def description_omit_fields(self):
        return []

    def postprocess_description(self, description):
        return description

    def log_stream_name_prefix(self):
        return self.name + "/"

    def _describe_log_streams(self, nextToken=None):
        return ignore_nones(self._cw_logs.describe_log_streams)(
            logGroupName=self.log_group_name(),
            logStreamNamePrefix=self.log_stream_name_prefix(),
            nextToken=nextToken,
        )

    def _get_log_streams(self):
        if self._log_streams is None:
            self._log_streams = {}
            token = None
            while True:
                response = self._describe_log_streams(token)
                token = response.get("nextToken")
                for stream in response["logStreams"]:
                    self._log_streams[stream["logStreamName"]] = stream
                if token is None:
                    break
        return self._log_streams

    def _log_stream_names(self):
        streams = self._get_log_streams()
        return list(streams)

    @property
    def logs(self) -> List[LogStream]:
        return [
            LogStream(self._cw_logs, self.log_group_name(), stream_name)
            for stream_name in self._log_stream_names()
        ]

    @property
    def logfilter(self) -> LogStreamFilter:
        return LogStreamFilter(
            logs=self._cw_logs,
            group=self.log_group_name(),
            stream_names=self._log_stream_names(),
        )


class TextResource:
    def __init__(self, text):
        self.text = text

    @property
    def logfilter(self):
        return TextFilter(self.text)


class Endpoint(Resource):
    url_prefix = "endpoints"

    def log_stream_name_prefix(self):
        """In contrast to every other Resource every Endpoint gets its own
        LogGroup. Thus, all LogStreams are returned for an Endpoint.
        """
        return None

    def log_group_name(self):
        return f"/aws/sagemaker/Endpoints/{self.name}"

    def description_omit_fields(self):
        return ["CreationTime", "LastModifiedTime"]


class NotebookInstance(Resource):
    url_prefix = "notebook-instances"


class TrainingJob(Resource):
    url_prefix = "jobs"

    def description_omit_fields(self):
        return [
            "SecondaryStatusTransitions",
            "StoppingCondition",
            "RoleArn",
            "CreationTime",
            "TrainingStartTime",
            "TrainingEndTime",
            "LastModifiedTime",
            "EnableNetworkIsolation",
            "EnableInterContainerTrafficEncryption",
            "EnableManagedSpotTraining",
            "BillableTimeInSeconds",
            "OutputDataConfig",  # same info as ModelArtifacts
        ]

    def postprocess_description(self, description):
        description["InputDataConfig"] = {
            channel["ChannelName"]: channel["DataSource"]["S3DataSource"][
                "S3Uri"
            ]
            for channel in description["InputDataConfig"]
        }

        if "ModelArtifacts" in description:
            description["ModelArtifacts"] = description["ModelArtifacts"][
                "S3ModelArtifacts"
            ]
        description["TrainingImage"] = description.pop(
            "AlgorithmSpecification"
        )["TrainingImage"]

        if "FinalMetricDataList" in description:
            description["FinalMetricDataList"] = {
                metric["MetricName"]: metric["Value"]
                for metric in description["FinalMetricDataList"]
            }

        description["ResourceConfig"] = dissoc(
            description["ResourceConfig"], "VolumeSizeInGB", "VolumeKmsKeyId"
        )
        return dict(sorted(description.items()))


class ProcessingJob(Resource):
    url_prefix = "processing-jobs"


class TransformJob(Resource):
    url_prefix = "transform-jobs"


class HyperParameterTuningJob(Resource):
    url_prefix = "hyper-tuning-jobs"

    def log_stream_name_prefix(self):
        return self._description[self.name_field()]

    def log_group_name(self):
        return "/aws/sagemaker/TrainingJobs"
