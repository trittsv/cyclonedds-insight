"""
 * Copyright(c) 2024 Sven Trittler
 *
 * This program and the accompanying materials are made available under the
 * terms of the Eclipse Public License v. 2.0 which is available at
 * http://www.eclipse.org/legal/epl-2.0, or the Eclipse Distribution License
 * v. 1.0 which is available at
 * http://www.eclipse.org/org/documents/edl-v10.php.
 *
 * SPDX-License-Identifier: EPL-2.0 OR BSD-3-Clause
"""

from dataclasses import dataclass
import cyclonedds.idl as idl
import cyclonedds.idl.annotations as annotate
import cyclonedds.idl.types as types


@dataclass
@annotate.mutable
@annotate.autoid("hash")
@annotate.nested
class Position(idl.IdlStruct, typename="AtcData.Position"):
    latitude: types.float64
    longitude: types.float64


@dataclass
@annotate.mutable
@annotate.autoid("hash")
class Flight(idl.IdlStruct, typename="AtcData.Flight"):
    id: str
    annotate.key("id")
    pos: 'AtcData.Position'
    CurrentRegion: str


