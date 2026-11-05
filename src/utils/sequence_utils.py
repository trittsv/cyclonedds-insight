"""
 * Copyright(c) 2026 Sven Trittler
 *
 * This program and the accompanying materials are made available under the
 * terms of the Eclipse Public License v. 2.0 which is available at
 * http://www.eclipse.org/legal/epl-2.0, or the Eclipse Distribution License
 * v. 1.0 which is available at
 * http://www.eclipse.org/org/documents/edl-v10.php.
 *
 * SPDX-License-Identifier: EPL-2.0 OR BSD-3-Clause
"""

import copy
import math

from PySide6.QtCore import qtTrId


def sequence_steps(preset, copy_steps=True):
    """Read authoritative steps, or convert a tester's string references to writes."""
    if not isinstance(preset, dict):
        raise ValueError(qtTrId("listener.error.event"))
    if "sequence_steps" in preset:
        steps = copy.deepcopy(preset["sequence_steps"]) if copy_steps else preset["sequence_steps"]
    else:
        references = preset.get("sequence_items", [])
        if not isinstance(references, list):
            raise ValueError(qtTrId("listener.error.event"))
        steps = [{"message_id": reference, "operation": "write"} for reference in references]
    if not isinstance(steps, list):
        raise ValueError(qtTrId("listener.error.event"))
    for step in steps:
        if (not isinstance(step, dict) or not isinstance(step.get("message_id"), str)
                or not step["message_id"] or step.get("operation", "write") not in ("write", "dispose")):
            raise ValueError(qtTrId("listener.error.event"))
        step.setdefault("operation", "write")
        delay = step.setdefault("delay_ms", 0)
        if (isinstance(delay, bool) or not isinstance(delay, (int, float))
                or not math.isfinite(delay) or not 0 <= delay <= 2147483647):
            raise ValueError(qtTrId("listener.error.timestamps"))
    return steps


def sequence_fields(steps):
    """Generate the write-only string list for older testers from the complete steps."""
    return {
        "sequence_steps": copy.deepcopy(steps),
        "sequence_items": [step["message_id"] for step in steps if step["operation"] == "write"],
    }
