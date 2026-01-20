from __future__ import annotations

from .utils import call_dequeue, call_enqueue, call_size, iso_ts, run_queue


def test_enqueue_size_dequeue_flow() -> None:
    run_queue([
        call_enqueue("companies_house", 1, iso_ts(delta_minutes=0)).expect(1),
        call_size().expect(1),
        call_dequeue().expect("companies_house", 1),
    ])

def test_purge_clears_queue() -> None:
    run_queue([
        call_enqueue("companies_house", 1, iso_ts(delta_minutes=0)).expect(1),
        call_size().expect(1),
        call_purge().expect(True),
        call_size().expect(0)
    ])

def test_rule_of_three_applies() -> None:
        
def test_timestamp_ordering_applies() -> None:
    pass

def dependency_resolution_applies() -> None:
    pass

