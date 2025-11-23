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

from PySide6.QtCore import QAbstractListModel, Qt
from PySide6.QtCore import QObject, Signal, Slot, QThread
from loguru import logger as logging
import time
from dds_access import dds_utils
from cyclonedds.core import Qos, Policy
from cyclonedds import core
from cyclonedds.topic import Topic
from cyclonedds.pub import Publisher, DataWriter
from cyclonedds.sub import Subscriber, DataReader
from cyclonedds.domain import DomainParticipant

import sys
from dds_access.datatypes import atc_data
sys.modules["AtcData"] = atc_data


class AtcModel(QAbstractListModel):

    airplaneUpdated = Signal(str, float, float, str, bool)  # id, lat, lon, region, isRemoved

    def __init__(self, parent: QObject = None):
        super().__init__(parent)
        self.airplanes = {}
        self.domainParticipant = None
        self.topic = None
        self.topicName = "FlightData"
        self.domainId = 0
        self.dispatcherThread = None

    def getTopic(self):
        if self.topic is None:
            self.domainParticipant = DomainParticipant(self.domainId)
            self.topic = Topic(self.domainParticipant, self.topicName, atc_data.Flight)

        return self.domainParticipant, self.topic

    @Slot()
    def clearAddedAirplaines(self):
        self.airplanes.clear()

    @Slot(str, float, float, str)
    def addUpdateAirplane(self, id, lat, lon, region):
        try:
            dp, topic = self.getTopic()

            if id in self.airplanes:
                self.airplanes[id]["lat"] = lat
                self.airplanes[id]["lon"] = lon

                if region != self.airplanes[id]["region"]:
                    del self.airplanes[id]["writer"]
                    del self.airplanes[id]["publisher"]
                    self.airplanes[id]["publisher"] = Publisher(dp, Qos(Policy.Partition(partitions=[region])))
                    self.airplanes[id]["writer"] = DataWriter(self.airplanes[id]["publisher"], topic)

                self.airplanes[id]["region"] = region
            else:
                publisher = Publisher(dp, Qos(Policy.Partition(partitions=[region])))
                self.airplanes[id] = {
                    "lat": lat,
                    "lon": lon,
                    "region": region,
                    "writer": DataWriter(publisher, topic),
                    "publisher": publisher
                }

            logging.trace(f"Writing ... {id}")
            self.airplanes[id]["writer"].write(atc_data.Flight(id, atc_data.Position(lat, lon), region))

        except Exception as e:
            logging.error(f"AtcModel.addUpdateAirplane exception: {e}")

    @Slot(list)
    def restart(self, partitions):

        if self.dispatcherThread is not None:
            self.dispatcherThread.stop()
            self.dispatcherThread.wait()
            self.dispatcherThread = None

        if self.dispatcherThread is None and len(partitions) > 0:
            dp, topic = self.getTopic()
            self.dispatcherThread = AirplaneDispatcherThread(dp, topic, partitions)
            self.dispatcherThread.onData.connect(self.dataReceived, Qt.ConnectionType.QueuedConnection)
            self.dispatcherThread.start()

    @Slot(str)
    def removeAirplane(self, id):
        try:
            if id in self.airplanes:
                del self.airplanes[id]["writer"]
                del self.airplanes[id]["publisher"]
                del self.airplanes[id]
        except Exception as e:
            logging.error(f"AtcModel.removeAirplane exception: {e}")

    @Slot(str, float, float, str, bool)
    def dataReceived(self, id, lat, lon, region, isRemoved):
        self.airplaneUpdated.emit(id, lat, lon, region, isRemoved)

    @Slot()
    def stop(self):
        if self.dispatcherThread is not None:
            self.dispatcherThread.stop()
            self.dispatcherThread.wait()
            self.dispatcherThread = None

class AirplaneDispatcherThread(QThread):

    onData = Signal(str, float, float, str, bool)

    def __init__(self, domainParticipant, topic, partitions, parent=None):
        super().__init__()
        self.domain_participant = domainParticipant
        self.running = False
        self.paused = False
        self.topic = topic
        self.partitions = partitions

    def run(self):
        self.running = True

        try:
            subscriber = Subscriber(self.domain_participant, Qos(Policy.Partition(partitions=self.partitions)))
            reader = DataReader(subscriber, self.topic,)

            while self.running:
                time.sleep(0.04)

                if self.paused:
                    continue

                try:
                    samples = reader.take(dds_utils.MAX_SAMPLE_SIZE)
                    for sample in samples:
                        if not self.running:
                            break

                        if sample.sample_info.sample_state == core.SampleState.NotRead and sample.sample_info.instance_state == core.InstanceState.Alive and sample.sample_info.valid_data:
                            self.onData.emit(sample.id, sample.pos.latitude, sample.pos.longitude, sample.CurrentRegion, False)
                        else:
                            self.onData.emit(sample.key_sample.id, 0.0, 0.0, "", True)

                except Exception as e:
                    logging.error(str(e))
        except Exception as e:
            logging.error(str(e))

    def stop(self):
        self.running = False

    @Slot()
    def pause(self):
        self.paused = True

    @Slot()
    def resume(self):
        self.paused = False
