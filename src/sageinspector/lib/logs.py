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

import functools
import re
import time
from collections import defaultdict
from typing import List, NamedTuple, Iterator, Optional

from toolz import concat, take

from ..util import ignore_nones


class LogEvent(NamedTuple):
    message: str
    timestamp: int
    ingestion_time: int

    @classmethod
    def from_raw(cls, raw):
        return cls(
            message=raw["message"],
            timestamp=raw["timestamp"],
            ingestion_time=raw["ingestionTime"],
        )

    def __str__(self):
        return self.message


class LogFilterEvent(NamedTuple):
    message: str
    timestamp: int
    ingestion_time: int
    # additional fields compared to `LogEvent`
    stream_name: str
    event_id: str

    @classmethod
    def from_raw(cls, raw):
        return cls(
            message=raw["message"],
            timestamp=raw["timestamp"],
            ingestion_time=raw["ingestionTime"],
            stream_name=raw["logStreamName"],
            event_id=raw["eventId"],
        )

    def __str__(self):
        return self.message


class LogStream(NamedTuple):
    logs: object
    group: str
    stream_name: str

    @property
    def _kwargs(self):
        return {"logGroupName": self.group, "logStreamName": self.stream_name}

    def iter_log_events(
        self, start_at_top=None, limit=None, forever=False
    ) -> Iterator[dict]:
        """Stream over log-events.

        This method is used by all other methods to access logs.
        """

        get_log_events = functools.partial(
            ignore_nones(self.logs.get_log_events),
            startFromHead=start_at_top,
            limit=limit,
            **self._kwargs,
        )

        token = None

        while True:
            response = get_log_events(nextToken=token)
            yield map(LogEvent.from_raw, response["events"])

            if token == response["nextForwardToken"]:
                if forever:
                    yield None
                else:
                    break

            token = response["nextForwardToken"]

    def head(self, n):
        assert n <= 10_000
        stream = concat(self.iter_log_events(start_at_top=True, limit=n))
        yield from take(n, stream)

    def tail(self, n):
        assert n <= 10_000
        stream = concat(self.iter_log_events(start_at_top=False, limit=n))
        yield from take(n, stream)

    def cat(self):
        stream = concat(self.iter_log_events(start_at_top=True))
        yield from stream

    def follow(self, start_at_top=True, limit=None, interval=30):
        for page in self.iter_log_events(
            start_at_top=start_at_top, forever=True, limit=limit
        ):
            if page is None:
                time.sleep(interval)
                continue

            yield from page


class LogStreamFilter(NamedTuple):
    logs: object
    group: str
    stream_names: Optional[List[str]] = None
    prefix: Optional[str] = None

    def iter_log_events(self, pattern: str, limit=None):
        assert (
            self.stream_names is None
            or self.prefix is None
            and self.stream_names != self.prefix
        ), "Provide either `stream_names` or `prefix`, and not both."

        filter_log_events = functools.partial(
            ignore_nones(self.logs.filter_log_events),
            logGroupName=self.group,
            logStreamNamePrefix=self.prefix,
            logStreamNames=self.stream_names,
            filterPattern=pattern,
            limit=limit,
        )

        token = None

        while True:
            response = filter_log_events(nextToken=token)
            token = response.get("nextToken")
            yield map(LogFilterEvent.from_raw, response["events"])

            if not token:
                break

    def iter_filter(self, pattern: str):
        for page in self.iter_log_events(pattern):
            yield from page

    def filter(self, pattern: str) -> dict:
        events_by_job = defaultdict(list)

        for event in self.iter_filter(pattern):
            events_by_job[event.stream_name].append(event)
        return events_by_job

    def iter_match(self, pattern: str, regex: str):
        for page in self.iter_log_events(pattern):
            for event in page:
                match = re.match(regex, event.message)
                if match is not None:
                    yield match, event

    def match(self, pattern: str, regex: str) -> dict:
        events_by_job = defaultdict(list)

        for match, event in self.iter_match(pattern, regex):
            events_by_job[event.stream_name].append(match.group(0))

        return events_by_job

    def iter_find(self, pattern: str, regex: str):
        for page in self.iter_log_events(pattern):
            for event in page:
                results = re.findall(regex, event.message)
                if results:
                    yield results, event

    def find(self, pattern: str, regex: str):
        events_by_job = defaultdict(list)

        for match, event in self.iter_find(pattern, regex):
            events_by_job[event.stream_name].append(match[0])

        return events_by_job


class TextFilter(NamedTuple):
    text: str

    def iter_log_events(self, pattern: str, limit=None):
        yield [
            LogFilterEvent(
                message=line,
                timestamp=idx,
                ingestion_time=idx,
                stream_name="",
                event_id=str(idx),
            )
            for idx, line in enumerate(self.text.splitlines())
        ]

    def iter_filter(self, pattern: str):
        for page in self.iter_log_events(pattern):
            yield from page

    def filter(self, pattern: str) -> dict:
        events_by_job = defaultdict(list)

        for event in self.iter_filter(pattern):
            events_by_job[event.stream_name].append(event)
        return events_by_job

    def iter_match(self, pattern: str, regex: str):
        for page in self.iter_log_events(pattern):
            for event in page:
                match = re.match(regex, event.message)
                if match is not None:
                    yield match, event

    def match(self, pattern: str, regex: str) -> dict:
        events_by_job = defaultdict(list)

        for match, event in self.iter_match(pattern, regex):
            events_by_job[event.stream_name].append(match.group(0))

        return events_by_job

    def iter_find(self, pattern: str, regex: str):
        for page in self.iter_log_events(pattern):
            for event in page:
                results = re.findall(regex, event.message)
                if results:
                    yield results, event

    def find(self, pattern: str, regex: str):
        events_by_job = defaultdict(list)

        for match, event in self.iter_find(pattern, regex):
            events_by_job[event.stream_name].append(match[0])

        return events_by_job
