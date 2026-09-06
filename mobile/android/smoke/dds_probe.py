"""Exercise the real CycloneDDS Python package and its native serialization layer."""
from PySide6.QtCore import QObject, Property, Signal, Slot, QTimer


class DdsProbe(QObject):
    changed = Signal()

    def __init__(self):
        super().__init__()
        self._participant = None
        self._topic = self._writer = self._reader = None
        self._message_type = None
        self._count = 0
        self._status = "cyclonedds-python ready to test on domain 0."
        self._timer = QTimer(self)
        self._timer.setInterval(100)
        self._timer.timeout.connect(self._receive)

    @Property(str, notify=changed)
    def status(self):
        return self._status

    @Property(bool, notify=changed)
    def running(self):
        return self._participant is not None

    @Slot()
    def start(self):
        if self.running:
            return
        try:
            from dataclasses import dataclass
            from cyclonedds.domain import DomainParticipant
            from cyclonedds.topic import Topic
            from cyclonedds.pub import DataWriter
            from cyclonedds.sub import DataReader
            from cyclonedds.idl import IdlStruct

            @dataclass
            class ProbeMessage(IdlStruct, typename="InsightProbe::Message"):
                text: str

            self._message_type = ProbeMessage
            self._participant = DomainParticipant(0)
            self._topic = Topic(self._participant, "InsightAndroidProbe", ProbeMessage)
            self._reader = DataReader(self._participant, self._topic)
            self._writer = DataWriter(self._participant, self._topic)
            self._status = "cyclonedds-python active: participant, topic, reader and writer. Tap Send sample."
            self._timer.start()
        except Exception as error:
            self.stop()
            self._status = f"cyclonedds-python start failed: {error}"
        self.changed.emit()

    @Slot()
    def send(self):
        if self._writer is None:
            return
        try:
            self._count += 1
            self._writer.write(self._message_type(text=f"Hello from Insight Android #{self._count}"))
            self._status = f"Sent sample #{self._count}; waiting for reader."
        except Exception as error:
            self._status = f"Write failed: {error}"
        self.changed.emit()

    def _receive(self):
        try:
            samples = self._reader.take(10)
            for sample in samples:
                if isinstance(sample, self._message_type):
                    self._status = f"Received through cyclonedds-python: {sample.text}"
                    self.changed.emit()
        except Exception as error:
            self._timer.stop()
            self._status = f"Read failed: {error}"
            self.changed.emit()

    @Slot()
    def stop(self):
        self._timer.stop()
        # Release children first; CycloneDDS Python owns and deletes each entity.
        self._writer = None
        self._reader = None
        self._topic = None
        self._participant = None
        self._status = "cyclonedds-python stopped."
        self.changed.emit()
