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

from PySide6.QtCore import QObject, Signal, Slot, QThread, Qt
from cyclonedds.builtin import DcpsEndpoint, DcpsParticipant
import threading
import logging
import time
import copy
from queue import Queue
from typing import Dict, List
import gc

from dds_service import BuiltInObserverThread, builtin_observer
from dds_qos import qos_match, dds_qos_policy_id
from utils import singleton, EntityType

# Mit queue is eindeutig besser! oder? wirklich?
# mhm nicht so eindeutig!
g_use_sigslot = False

class DataEndpoint:
    def __init__(self, endpoint: DcpsEndpoint, entity_type) -> None:
        self.endpoint: DcpsEndpoint = endpoint
        self.entity_type: EntityType = entity_type
        self.participant = None
        self.missmatches : Dict[str, List[dds_qos_policy_id]]= {}

    def isReader(self):
        return self.entity_type == EntityType.READER

    def isWriter(self):
        return self.entity_type == EntityType.WRITER

    def link_participant(self, participant: DcpsParticipant):
        if str(self.endpoint.participant_key) == str(participant.key):
            self.participant = participant


class DataTopic:
    def __init__(self, name) -> None:
        self.name = name
        self.reader_endpoints: Dict[str, DataEndpoint] = {}
        self.writer_endpoints: Dict[str, DataEndpoint] = {}

    def add_endpoint(self, endpoint: DataEndpoint):
        if endpoint.isReader():
            if str(endpoint.endpoint.key) not in self.reader_endpoints:
                self.reader_endpoints[str(endpoint.endpoint.key)] = endpoint
        else:
            if str(endpoint.endpoint.key) not in self.writer_endpoints:
                self.writer_endpoints[str(endpoint.endpoint.key)] = endpoint

        self.check_qos_mismatch(endpoint)

    def remove_endpoint(self, endpointKey: str):
        if endpointKey in self.reader_endpoints:
            for mimKey in self.reader_endpoints[endpointKey].missmatches:
                if mimKey in self.writer_endpoints:
                    if endpointKey in self.writer_endpoints[mimKey].missmatches:
                        del self.writer_endpoints[mimKey].missmatches[endpointKey]

            del self.reader_endpoints[endpointKey]
    
        if endpointKey in self.writer_endpoints:
            for mimKey in self.writer_endpoints[endpointKey].missmatches:
                if mimKey in self.reader_endpoints:
                    if endpointKey in self.reader_endpoints[mimKey].missmatches:
                        del self.reader_endpoints[mimKey].missmatches[endpointKey]

            del self.writer_endpoints[endpointKey]

    def link_participant(self, participant: DcpsParticipant):
        for reader_key in self.reader_endpoints.keys():
            self.reader_endpoints[reader_key].link_participant(participant)
        for writer_key in self.writer_endpoints.keys():
            self.writer_endpoints[writer_key].link_participant(participant)

    def hasEndpoints(self) -> bool:
        return len(self.reader_endpoints) > 0 or len(self.writer_endpoints) > 0

    def check_qos_mismatch(self, data_endpoint: DataEndpoint):

        #mut_start = time.time()

        endpoints_to_check = self.reader_endpoints
        if data_endpoint.isReader():
            endpoints_to_check = self.writer_endpoints

        for endpKey in endpoints_to_check.keys():
            endpoint_to_check = endpoints_to_check[endpKey]

            mismatches: List[dds_qos_policy_id] = []
            if data_endpoint.isReader():
                mismatches = qos_match(data_endpoint.endpoint, endpoint_to_check.endpoint)
            else:
                mismatches = qos_match(endpoint_to_check.endpoint, data_endpoint.endpoint)

            if len(mismatches) > 0:
                data_endpoint.missmatches[str(endpoint_to_check.endpoint.key)] = mismatches
                endpoint_to_check.missmatches[str(data_endpoint.endpoint.key)] = mismatches

        #end_time = time.time()
        #logging.info(f"NEW QOS TAKES: {end_time - mut_start}")

    def get_mismatches(self) -> List[str]:
        mism_endp_keys: List[str] = []
        for endpKey in self.reader_endpoints.keys():
            if len(self.reader_endpoints[endpKey].missmatches):
                mism_endp_keys += self.reader_endpoints[endpKey].missmatches.keys()
        for endpKey in self.writer_endpoints.keys():
            if len(self.writer_endpoints[endpKey].missmatches):
                mism_endp_keys += self.writer_endpoints[endpKey].missmatches.keys()

        return list(dict.fromkeys(mism_endp_keys))

class DataDomain:
    def __init__(self, domain_id: int, queue) -> None:
        self.domain_id = domain_id
        self.topics: Dict[str, DataTopic] = {}
        self.endpointToTopic = {} # shortcut for deletion where only endp key is available
        self.participants = {}
        self.obs_running = [True]

        if g_use_sigslot:
            self.obs_thread: BuiltInObserverThread = BuiltInObserverThread(domain_id)

            dds_data = DdsData()
            self.obs_thread.newParticipantSignal.connect(dds_data.add_domain_participant, Qt.ConnectionType.QueuedConnection)
            self.obs_thread.newEndpointSignal.connect(dds_data.add_endpoint, Qt.ConnectionType.QueuedConnection)
            self.obs_thread.removeParticipantSignal.connect(dds_data.remove_domain_participant, Qt.ConnectionType.QueuedConnection)
            self.obs_thread.removeEndpointSignal.connect(dds_data.remove_endpoint, Qt.ConnectionType.QueuedConnection)
        else:
            self.obs_thread = threading.Thread(target=builtin_observer, args=(domain_id, queue, self.obs_running))

        self.obs_thread.start()

    def add_participant(self, participant: DcpsParticipant):
        self.participants[str(participant.key)] = participant
        for topic in self.topics.keys():
            self.topics[topic].link_participant(participant)

    def add_endpoint(self, dataEndpoint: DataEndpoint):
        self.endpointToTopic[str(dataEndpoint.endpoint.key)] = str(dataEndpoint.endpoint.topic_name)
        if str(dataEndpoint.endpoint.topic_name) not in self.topics:
            self.topics[str(dataEndpoint.endpoint.topic_name)] = DataTopic(str(dataEndpoint.endpoint.topic_name))

        if str(dataEndpoint.endpoint.participant_key) in self.participants:
            dataEndpoint.link_participant(self.participants[str(dataEndpoint.endpoint.participant_key)])

        self.topics[str(dataEndpoint.endpoint.topic_name)].add_endpoint(dataEndpoint)

    def remove_endpoint(self, endpoint_key: str):
        if endpoint_key in self.endpointToTopic:
            topicName = self.endpointToTopic[endpoint_key]
            if topicName in self.topics:
                self.topics[topicName].remove_endpoint(endpoint_key)
                del self.endpointToTopic[endpoint_key]

                if not self.topics[topicName].hasEndpoints():
                    del self.topics[topicName]

    def remove_participant(self, key: str):
        if key in self.participants:
            del self.participants[key]

    def hash_topic(self, topicName: str) -> bool:
        return topicName in self.topics

    def get_topic_name(self, endpointKey: str) -> bool:
        if endpointKey in self.endpointToTopic:
            return self.endpointToTopic[endpointKey]
        return ""

    def getEndpoints(self, topicName: str, entity_type: EntityType):
        if topicName in self.topics:
            if entity_type == EntityType.READER:
                return self.topics[topicName].reader_endpoints
            else:
                return self.topics[topicName].writer_endpoints
        return {}

    def __del__(self):
        self.obs_running[0] = False
        
        if g_use_sigslot:
            self.obs_thread.stop()
            self.obs_thread.wait()
        else:
            self.obs_thread.join()

class BuiltInReceiver(QThread):

    def __init__(self, dds_data):
        super().__init__()
        self.dds_data = dds_data

    def run(self):
        logging.info(f"Running ddsdata ... thread: {QThread.currentThread()}")

        last_updated_qos_mismatches = 0

        while self.dds_data.running[0]:
            time.sleep(1)

            #logging.info(f"Queue status: {self.queue.qsize()}, {time.monotonic()}")

            processing_started_time = time.monotonic()

            while True:
                if self.dds_data.queue.empty():
                    break

                #logging.info(f"Queue status: {self.queue.qsize()} {str(self.currentThread())}")

                push = False
                if time.monotonic() - processing_started_time > 2.0:
                    push = True

                item = self.dds_data.queue.get()

                if item is None:
                    break

                with self.dds_data.mutex:
                    for (domain_id, participant) in item.new_participants:
                        self.dds_data.add_domain_participant(domain_id, participant)

                    for (domain_id, participant) in item.remove_participants:
                        self.dds_data.remove_domain_participant(domain_id, participant)

                    for (domain_id, endpoint, entity_type) in item.new_endpoints:
                        self.dds_data.add_endpoint(domain_id, endpoint, entity_type)

                    for (domain_id, endpoint) in item.remove_endpoints:
                        self.dds_data.remove_endpoint(domain_id, endpoint)

                if push:
                    break

            time.sleep(1)

            #with self.mutex:
            #    if len(self.endpoints) > 0 and self.last_updated_endpoint != last_updated_qos_mismatches:
            #        last_updated_qos_mismatches = self.last_updated_endpoint
            #        for domain_id in self.domains:
            #            self.check_qos_mismatches(domain_id)


        logging.info("Running ddsdata ... DONE")
@singleton
class DdsData(QObject):

    # domain observer threads
    observer_threads = {}
    mutex = threading.RLock()

    # signals and slots
    new_topic_signal = Signal(int, str)
    remove_topic_signal = Signal(int, str)
    new_domain_signal = Signal(int)
    removed_domain_signal = Signal(int)
    new_endpoint_signal = Signal(str, int, DataEndpoint)
    removed_endpoint_signal = Signal(int, str)
    new_participant_signal = Signal(int, DcpsParticipant)
    removed_participant_signal = Signal(int, str)

    no_more_mismatch_in_topic_signal = Signal(int, str)
    publish_mismatch_signal = Signal(int, str, list)

    the_domains: Dict[int, DataDomain] = {}

    last_updated_endpoint = int(time.monotonic())

    queue = Queue()
    running = [True]

    def __init__(self):
        super().__init__()
        logging.debug("Construct DdsData")

        self.receiver = BuiltInReceiver(self)
        self.receiver.start()


    def join_observer(self):
        self.the_domains.clear()
        gc.collect()

    def add_domain(self, domain_id: int):
        with self.mutex:
            if domain_id in self.the_domains:
                return
            self.the_domains[domain_id] = DataDomain(domain_id, self.queue)
            self.new_domain_signal.emit(domain_id)

    @Slot(int)
    def remove_domain(self, domain_id: int):
        with self.mutex:
            if domain_id in self.the_domains:
                del self.the_domains[domain_id]
                gc.collect()

            self.removed_domain_signal.emit(domain_id)


    @Slot(int, DcpsParticipant)
    def add_domain_participant(self, domain_id: int, participant: DcpsParticipant):
        #logging.debug(f"Add domain participant {str(participant.key)}")

        if domain_id in self.the_domains:
            self.the_domains[domain_id].add_participant(participant)

        self.new_participant_signal.emit(domain_id, participant)

    @Slot(int, DcpsParticipant)
    def remove_domain_participant(self, domain_id: int, participant: DcpsParticipant):
        if domain_id in self.the_domains:
            self.the_domains[domain_id].remove_participant(str(participant.key))
            self.removed_participant_signal.emit(domain_id, str(participant.key))

    @Slot(int, DcpsEndpoint, EntityType)
    def add_endpoint(self, domain_id: int, endpoint: DcpsEndpoint, entity_type: EntityType):

        # logging.debug(f"Add endpoint domain: {domain_id}, key: {str(endpoint.key)}, entity: {entity_type}")

        

        if domain_id in self.the_domains:
            topic_already_known = self.the_domains[domain_id].hash_topic(str(endpoint.topic_name))
            dataEndp = DataEndpoint(endpoint, entity_type)
            self.the_domains[domain_id].add_endpoint(dataEndp)

            if not topic_already_known:
                self.new_topic_signal.emit(domain_id, endpoint.topic_name)


            self.new_endpoint_signal.emit("", domain_id, copy.deepcopy(dataEndp))
       
            mismatches = self.the_domains[domain_id].topics[endpoint.topic_name].get_mismatches()
            if len(mismatches) > 0:
                self.publish_mismatch_signal.emit(domain_id, endpoint.topic_name, mismatches)


    @Slot(int, DcpsEndpoint)
    def remove_endpoint(self, domain_id: int, endpoint: DcpsEndpoint):

        if domain_id in self.the_domains:

            topicName = self.the_domains[domain_id].get_topic_name(str(endpoint.key))

            self.the_domains[domain_id].remove_endpoint(str(endpoint.key))

            #logging.debug(f"Remove endpoint {str(endpoint.key)} (topic: {topicName})")

            self.updateEndpointsModified()
            self.removed_endpoint_signal.emit(domain_id, str(endpoint.key))

            if not self.the_domains[domain_id].hash_topic(topicName):
                #logging.info(f"Removed last endpointon topic, topic gone {topicName}")
                self.remove_topic_signal.emit(domain_id, topicName)
            else:
                self.no_more_mismatch_in_topic_signal.emit(domain_id, topicName)
                mismatches = self.the_domains[domain_id].topics[topicName].get_mismatches()
                if len(mismatches) > 0:
                    self.publish_mismatch_signal.emit(domain_id, topicName, mismatches)


    @Slot(str, int, str, EntityType)
    def requestEndpointsSlot(self, requestId: str, domain_id: int, topic_name: str, entity_type: EntityType):
        if g_use_sigslot:
            if domain_id in self.the_domains:
                endDict = self.the_domains[domain_id].getEndpoints(topic_name, entity_type)
                for key in endDict.keys():
                    self.new_endpoint_signal.emit(requestId, domain_id, copy.deepcopy(endDict[key]))
        else:
            with self.mutex:

                if domain_id in self.the_domains:
                    endDict = self.the_domains[domain_id].getEndpoints(topic_name, entity_type)
                    for key in endDict.keys():
                        self.new_endpoint_signal.emit(requestId, domain_id, copy.deepcopy(endDict[key]))

    @Slot(int, result=DcpsParticipant)
    def getParticipants(self, domain_id: int):
        with self.mutex:
            if domain_id in self.participants.keys():
                return self.participants[domain_id]

    def getQosMismatches(self, domain_id: int, topic_name: str):
        #with self.mutex:
        #    if domain_id in self.mismatches.keys() and domain_id in self.endpoints.keys():
        #        topic_mismatches = {}
        #        for (_, endpoint_iter) in self.endpoints[domain_id]:
        #            if topic_name == endpoint_iter.topic_name and str(endpoint_iter.key) in self.mismatches[domain_id].keys():
        #                topic_mismatches[str(endpoint_iter.key)] = self.mismatches[domain_id][str(endpoint_iter.key)]
        #        return topic_mismatches
        return {}

    def updateEndpointsModified(self):
        self.last_updated_endpoint = int(time.monotonic())

