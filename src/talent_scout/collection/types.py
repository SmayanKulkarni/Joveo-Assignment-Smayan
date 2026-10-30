from typing import Literal

from talent_scout.kernel.types import Model


# Stub at its final module path: checkpoints store class paths. The Collection LLD owns these fields.
class LowDataPayload(Model):
    count: int
    target: int


class LowDataAnswer(Model):
    action: Literal["broaden", "continue", "abort"]
