"""Opt-in chart planning contracts; plan output never contains SVG or executable code."""
from typing import Literal

from pydantic import Field

from .base import Payload, Result
from .common import SessionParams
from .registry import event, method

ChartMode = Literal['off', 'always', 'smart']


class TableChartPolicy(Result):
    mode: ChartMode


class TableChartPlanParams(SessionParams):
    source: str = Field(min_length=1, max_length=8192)


class TableChartPlanResult(Result):
    kind: Literal['bar', 'line', 'none']


class TableChartPolicyPayload(Payload):
    mode: ChartMode


method('table_chart.policy', params=SessionParams, result=TableChartPolicy)
method('table_chart.plan', params=TableChartPlanParams, result=TableChartPlanResult)
event('table_chart.policy', TableChartPolicyPayload)
