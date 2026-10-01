"""Regression checks for discovery failures without a live DDS network."""
import sys
import unittest
from contextlib import ExitStack, nullcontext
from pathlib import Path
from queue import Queue
from types import SimpleNamespace
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from dds_access import builtin_observer as observer_module


class BuiltinObserverTest(unittest.TestCase):
    def run_observer(self, fail_wait=False, fail_read=False, fail_setup=False):
        queue = Queue()
        observer = observer_module.BuiltInObserver(0, queue)
        sample = SimpleNamespace(sample_info=SimpleNamespace(
            sample_state=observer_module.core.SampleState.NotRead,
            instance_state=observer_module.core.InstanceState.Alive))
        readers = [Mock() for _ in range(4)]
        for reader in readers:
            reader.take.return_value = []
        readers[0].take.side_effect = [[sample], [sample]]
        if fail_read:
            readers[3].take.side_effect = [Exception("Callfunc cqos errored."), []]
        waitset = Mock()
        calls = 0

        def wait(_):
            nonlocal calls
            calls += 1
            if fail_wait and calls == 1:
                raise RuntimeError("transient wait failure")
            if calls == (4 if fail_wait else 3):
                observer.stop()
            return 1

        waitset.wait.side_effect = wait
        ospl_reader = Mock()
        ospl_reader.take.return_value = []
        with ExitStack() as stack:
            stack.enter_context(patch.object(observer_module.DomainParticipantFactory,
                "get_participant", return_value=nullcontext(object())))
            stack.enter_context(patch.object(observer_module.core, "WaitSet", return_value=waitset))
            stack.enter_context(patch.object(observer_module.core, "GuardCondition"))
            stack.enter_context(patch.object(observer_module.core, "ReadCondition"))
            stack.enter_context(patch.object(observer_module.builtin, "BuiltinDataReader", side_effect=readers * (2 if fail_setup else 1)))
            stack.enter_context(patch.object(observer_module.internal, "feature_topic_discovery", True))
            topic = stack.enter_context(patch.object(observer_module, "Topic"))
            if fail_setup:
                topic.side_effect = [observer_module.core.DDSException(-1, "topic creation failed"), Mock()]
            retry_wait = stack.enter_context(patch.object(observer._stop_requested, "wait", return_value=False))
            stack.enter_context(patch.object(observer_module, "Subscriber"))
            stack.enter_context(patch.object(observer_module, "DataReader", return_value=ospl_reader))
            pause = stack.enter_context(patch.object(observer, "msleep"))
            log = stack.enter_context(patch.object(observer_module, "logging"))
            observer.run()
            if fail_setup:
                retry_wait.assert_called_once_with(1)
                self.assertEqual(topic.call_count, 2)

        self.assertFalse(observer.running)
        self.assertEqual(readers[0].take.call_count, 2)
        self.assertEqual(queue.qsize(), 2)
        self.assertEqual(queue.get().new_participants, [(0, sample)])
        self.assertEqual(queue.get().new_participants, [(0, sample)])
        return pause, log

    def test_read_failure_keeps_partial_batch_and_continues(self):
        pause, log = self.run_observer(fail_read=True)
        pause.assert_called_once_with(100)
        log.exception.assert_called_once()

    def test_wait_failure_retries_and_stop_does_not_read_again(self):
        pause, log = self.run_observer(fail_wait=True)
        pause.assert_called_once_with(100)
        log.exception.assert_called_once()

    def test_topic_initialization_failure_retries_and_resumes_discovery(self):
        pause, log = self.run_observer(fail_setup=True)
        pause.assert_not_called()
        log.exception.assert_called_once()

    def test_persistent_initialization_failure_has_capped_backoff_and_stops(self):
        observer = observer_module.BuiltInObserver(0, Queue())
        delays = []

        def wait(delay):
            delays.append(delay)
            if len(delays) == 6:
                observer.stop()
                return True
            return False

        with patch.object(observer, "_run_session", side_effect=RuntimeError("setup failed")) as session, \
                patch.object(observer._stop_requested, "wait", side_effect=wait), \
                patch.object(observer_module, "logging"):
            observer.run()
        self.assertEqual(delays, [1, 2, 4, 8, 10, 10])
        self.assertEqual(session.call_count, 6)
        self.assertFalse(observer.running)
        self.assertIsNone(observer.guardCondition)

    def test_stop_before_start_does_not_create_participant(self):
        observer = observer_module.BuiltInObserver(0, Queue())
        observer.stop()
        with patch.object(observer, "_run_session") as session:
            observer.run()
        session.assert_not_called()

    def test_normal_shutdown_does_not_delay(self):
        pause, log = self.run_observer()
        pause.assert_not_called()
        log.exception.assert_not_called()


if __name__ == "__main__":
    unittest.main()
