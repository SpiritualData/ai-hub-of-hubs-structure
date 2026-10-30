"""One lock per card folder: re-entrant in a thread, exclusive across threads, with a generation counter. Offline."""
import threading

from hubofhubs.recall.card_store_lock import StoreLock


def test_one_lock_object_per_folder_and_name(tmp_path):
    assert StoreLock.for_dir(str(tmp_path)) is StoreLock.for_dir(str(tmp_path))
    assert StoreLock.for_dir(str(tmp_path), ".tidy.lock") is not StoreLock.for_dir(str(tmp_path))


def test_the_same_thread_may_take_it_again(tmp_path):
    lock = StoreLock.for_dir(str(tmp_path))
    with lock:
        with lock:
            assert lock.held_by_current_thread()
        assert lock.held_by_current_thread()
    assert not lock.held_by_current_thread()


def test_another_thread_cannot_take_it_without_waiting(tmp_path):
    lock = StoreLock.for_dir(str(tmp_path))
    result = []
    with lock:
        worker = threading.Thread(target=lambda: result.append(lock.acquire(blocking=False)))
        worker.start()
        worker.join()
    assert result == [False]


def test_the_generation_counts_changes_made_under_the_lock(tmp_path):
    lock = StoreLock.for_dir(str(tmp_path))
    assert lock.generation() == 0 and lock.bump() == 0     # not held: nothing recorded
    with lock:
        assert lock.bump() == 1 and lock.bump() == 2
    assert lock.generation() == 2
