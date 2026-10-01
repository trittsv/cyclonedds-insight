"""Endpoint selection metadata exposed by the participant tree."""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from PySide6.QtCore import QAbstractItemModel, QModelIndex
from models import participant_model as module


class EndpointTreeQosTest(unittest.TestCase):
    def test_reader_and_writer_qos_and_refresh(self):
        model = module.ParticipantTreeModel.__new__(module.ParticipantTreeModel)
        QAbstractItemModel.__init__(model)
        model.rootItem = module.ParticipantTreeNode('root')
        parent = model.rootItem
        for key, layer in [(0, module.DisplayLayerEnum.DOMAIN),
                           ('host', module.DisplayLayerEnum.HOSTNAME),
                           ('app', module.DisplayLayerEnum.APP),
                           ('participant', module.DisplayLayerEnum.PARTICIPANT)]:
            node = module.ParticipantTreeNode(key, layer, parent)
            parent.appendChild(key, node)
            parent = node
        with patch.object(module, 'getHostname', return_value='host'), patch.object(module, 'getAppName', return_value='app'):
            for reader in (True, False):
                key = 'reader' if reader else 'writer'
                data = SimpleNamespace(participant=SimpleNamespace(key='participant'),
                    endpoint=SimpleNamespace(key=key, topic_name='topic', qos=['Reliability', 'History']),
                    isReader=lambda: reader)
                model.new_endpoint_slot('', 0, data)
                node = parent.childMap['topic'].childMap[key]
                index = model.createIndex(node.row(), 0, node)
                self.assertEqual(model.getEndpointTopicName(index), 'topic')
                self.assertEqual(model.getIsWriter(index), not reader)
                data.endpoint.qos = ['Durability']
                model.new_endpoint_slot('', 0, data)
                self.assertEqual(model.getEndpointTopicName(index), 'topic')
        self.assertEqual(model.getEndpointTopicName(QModelIndex()), '')
        self.assertEqual(model.getEndpointTopicName(model.createIndex(0, 0, parent)), '')


if __name__ == '__main__':
    unittest.main()
