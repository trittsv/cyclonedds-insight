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

import xml.etree.ElementTree as ET

from cyclonedds.qos_provider import QosProvider
from cyclonedds.core import Qos

from dds_access.datatypes.entity_type import EntityType


def _local_name(tag):
    if not isinstance(tag, str):
        return ""
    return tag.rsplit("}", 1)[-1].casefold()


def _attribute(element, name):
    for attribute_name, value in element.attrib.items():
        if _local_name(attribute_name) == name:
            return value.strip()
    return ""


def _base_profile_key(library_name, base_name):
    if not base_name:
        return ""
    if "::" not in base_name:
        return f"{library_name}::{base_name}"

    parts = [part for part in base_name.split("::") if part]
    if len(parts) == 1:
        return f"{library_name}::{parts[0]}"
    return "::".join(parts[:2])


def _profile_has_qos(profile_key, qos_tag, profiles, visited=None):
    if profile_key not in profiles:
        return False

    visited = set() if visited is None else visited
    if profile_key in visited:
        return False
    visited.add(profile_key)

    library_name, profile, base_name = profiles[profile_key]
    if any(_local_name(element.tag) == qos_tag for element in profile):
        return True

    base_key = _base_profile_key(library_name, base_name)
    return bool(base_key) and _profile_has_qos(
        base_key, qos_tag, profiles, visited
    )


def get_qos_provider_keys(file_path, entity_type=None):
    try:
        root = ET.parse(file_path).getroot()
    except (OSError, ET.ParseError, TypeError, ValueError):
        return []

    profiles = {}
    for library in root.iter():
        if _local_name(library.tag) != "qos_library":
            continue
        library_name = _attribute(library, "name")
        if not library_name:
            continue

        for profile in library.iter():
            if _local_name(profile.tag) != "qos_profile":
                continue
            profile_name = _attribute(profile, "name")
            if profile_name:
                profile_key = f"{library_name}::{profile_name}"
                profiles[profile_key] = (
                    library_name,
                    profile,
                    _attribute(profile, "base_name"),
                )

    qos_tag = {
        EntityType.READER: "datareader_qos",
        EntityType.WRITER: "datawriter_qos",
    }.get(entity_type)

    keys = []
    for profile_key, (_, profile, _) in profiles.items():
        if qos_tag and not _profile_has_qos(profile_key, qos_tag, profiles):
            continue

        keys.append(profile_key)
        for qos_element in profile:
            if qos_tag and _local_name(qos_element.tag) != qos_tag:
                continue
            entity_name = _attribute(qos_element, "name")
            if entity_name:
                keys.append(f"{profile_key}::{entity_name}")

    return list(dict.fromkeys(keys))


def load_qos_from_provider(file_path, profile_key, entity_type):
    profile_key = profile_key.strip()
    if not profile_key:
        raise ValueError("A QoS profile key is required.")

    provider = QosProvider(file_path)
    participant_qos = Qos()
    topic_qos = provider.get_topic_qos(profile_key)

    if entity_type == EntityType.READER:
        pub_sub_qos = provider.get_subscriber_qos(profile_key)
        endpoint_qos = provider.get_datareader_qos(profile_key)
    elif entity_type == EntityType.WRITER:
        pub_sub_qos = provider.get_publisher_qos(profile_key)
        endpoint_qos = provider.get_datawriter_qos(profile_key)
    else:
        raise ValueError(f"Unsupported endpoint type: {entity_type}")

    return participant_qos, topic_qos, pub_sub_qos, endpoint_qos
