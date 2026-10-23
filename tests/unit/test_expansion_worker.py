from queue import Queue
from unittest.mock import Mock

import pytest

from app.helper.llm.expansion_worker import ExpansionWorker


def test_worker_logs_traceback_and_continues_after_failure(caplog):
    # Run two jobs synchronously, then stop the otherwise infinite loop.
    class StopWorker(BaseException):
        pass

    queue = Queue()
    queue.put('first')
    queue.put('second')
    get = Mock(side_effect=['first', 'second', StopWorker()])
    queue.get = get
    process = Mock(side_effect=[ConnectionRefusedError(111, 'Connection refused'), None])
    worker = ExpansionWorker.__new__(ExpansionWorker)
    worker.queue = queue
    worker._process_fn = process

    with pytest.raises(StopWorker):
        worker._run()

    assert process.call_count == 2
    assert queue.unfinished_tasks == 0
    record = next(r for r in caplog.records if r.message == 'Tag expansion worker failed')
    assert record.exc_info[0] is ConnectionRefusedError
    assert 'ConnectionRefusedError' in caplog.text
