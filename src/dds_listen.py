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

from cyclonedds.core import Listener, Qos, Policy
from cyclonedds.domain import DomainParticipant
from cyclonedds.topic import Topic
from cyclonedds.sub import Subscriber, DataReader
from cyclonedds.util import duration


from PySide6.QtCore import QObject, Signal, Slot


class TopicReaderListen(QObject):

    
    def listen(self, domain_id, topic_name, topic_type, qos):

        domain_participant = DomainParticipant(domain_id)
        topic = Topic(domain_participant, topic_name, topic_type, qos=qos)
        subscriber = Subscriber(domain_participant)
        reader = DataReader(domain_participant, topic)

        for sample in reader.take_iter(timeout=duration(seconds=10)):
            print(sample)

    @Slot
    def addReader(self, domain_id, topic_name, topic_type, q_own, q_dur, q_rel):
        pass

    