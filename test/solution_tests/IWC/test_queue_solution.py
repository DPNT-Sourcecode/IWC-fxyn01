from __future__ import annotations

from .utils import call_dequeue, call_enqueue, call_size, iso_ts, run_queue, call_purge, call_age


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
    run_queue([
        call_enqueue("companies_house", 2, iso_ts(delta_minutes=0)).expect(1),
        call_enqueue("companies_house", 1, iso_ts(delta_minutes=0)).expect(2),
        call_enqueue("bank_statements", 1, iso_ts(delta_minutes=0)).expect(3),
        call_enqueue("id_verification", 1, iso_ts(delta_minutes=0)).expect(4),
        call_dequeue().expect("companies_house", 1),
        call_dequeue().expect("id_verification", 1),
        call_dequeue().expect("bank_statements", 1),
        call_dequeue().expect("companies_house", 2)
    ])

def test_timestamp_ordering_applies() -> None:
    run_queue([
        call_enqueue("companies_house", 2, iso_ts(delta_minutes=5)).expect(1),
        call_enqueue("companies_house", 1, iso_ts(delta_minutes=0)).expect(2),
        call_dequeue().expect("companies_house", 1),
        call_dequeue().expect("companies_house", 2)
    ])

def test_dependency_resolution_applies() -> None:
    run_queue([
        call_enqueue("credit_check", 1, iso_ts(delta_minutes=0)).expect(2),
        call_dequeue().expect("companies_house", 1),
        call_dequeue().expect("credit_check", 1)
    ])

def test_deduplication_rules_apply() -> None:
    run_queue([
        call_enqueue("companies_house", 1, iso_ts(delta_minutes=0)).expect(1),
        call_enqueue("companies_house", 1, iso_ts(delta_minutes=0)).expect(1),
        call_dequeue().expect("companies_house", 1),
        call_size().expect(0)
    ])

def test_deduplication_rule_of_three_applies() -> None:
    run_queue([
        call_enqueue("companies_house", 2, iso_ts(delta_minutes=0)).expect(1),
        call_enqueue("companies_house", 1, iso_ts(delta_minutes=0)).expect(2),
        call_enqueue("bank_statements", 1, iso_ts(delta_minutes=0)).expect(3),
        call_enqueue("id_verification", 1, iso_ts(delta_minutes=0)).expect(4),
        call_enqueue("id_verification", 1, iso_ts(delta_minutes=0)).expect(4),
        call_enqueue("bank_statements", 1, iso_ts(delta_minutes=0)).expect(4),
        call_dequeue().expect("companies_house", 1),
        call_dequeue().expect("id_verification", 1),
        call_dequeue().expect("bank_statements", 1),
        call_dequeue().expect("companies_house", 2)
    ])

def test_deduplication_timestamp_ordering_applies() -> None:
    run_queue([
        call_enqueue("companies_house", 2, iso_ts(delta_minutes=5)).expect(1),
        call_enqueue("companies_house", 1, iso_ts(delta_minutes=0)).expect(2),
        call_enqueue("companies_house", 1, iso_ts(delta_minutes=10)).expect(2),
        call_dequeue().expect("companies_house", 1),
        call_dequeue().expect("companies_house", 2)
    ])

def test_deduplication_dependency_resolution_applies() -> None:
    run_queue([
        call_enqueue("companies_house", 1, iso_ts(delta_minutes=0)).expect(1),
        call_enqueue("credit_check", 1, iso_ts(delta_minutes=0)).expect(2),
        call_dequeue().expect("companies_house", 1),
        call_dequeue().expect("credit_check", 1)
    ])

def test_deduplication_dependency_resolution_timestamp_applies_dependency_first() -> None:
    run_queue([
        call_enqueue("companies_house", 1, iso_ts(delta_minutes=5)).expect(1),
        call_enqueue("credit_check", 1, iso_ts(delta_minutes=0)).expect(2),
        call_dequeue().expect("companies_house", 1),
        call_dequeue().expect("credit_check", 1)
    ])

def test_deduplication_dependency_resolution_timestamp_applies_when_dependency_is_already_ahead() -> None:
    run_queue([
        call_enqueue("companies_house", 1, iso_ts(delta_minutes=0)).expect(1),
        call_enqueue("credit_check", 1, iso_ts(delta_minutes=5)).expect(2),
        call_dequeue().expect("companies_house", 1),
        call_dequeue().expect("credit_check", 1)
    ])

def test_multiple_bank_statements_rule_of_three_prioritised_correctly() -> None:
    run_queue([
        call_enqueue("companies_house", 1, iso_ts(delta_minutes=0)).expect(1),
        call_enqueue("bank_statements", 1, iso_ts(delta_minutes=4)).expect(2),
        call_enqueue("bank_statements", 2, iso_ts(delta_minutes=0)).expect(3),
        call_enqueue("credit_check", 1, iso_ts(delta_minutes=4)).expect(4),
        call_dequeue().expect("companies_house", 1),
        call_dequeue().expect("credit_check", 1),
        call_dequeue().expect("bank_statements", 1),
        call_dequeue().expect("bank_statements", 2)
    ])

def test_multiple_bank_statements_timestamp_prioritised_correctly() -> None:
    run_queue([
        call_enqueue("companies_house", 1, iso_ts(delta_minutes=0)).expect(1),
        call_enqueue("bank_statements", 1, iso_ts(delta_minutes=4)).expect(2),
        call_enqueue("bank_statements", 2, iso_ts(delta_minutes=0)).expect(3),
        call_enqueue("id_verification", 2, iso_ts(delta_minutes=0)).expect(4),
        call_dequeue().expect("companies_house", 1),
        call_dequeue().expect("id_verification", 2),
        call_dequeue().expect("bank_statements", 2),
        call_dequeue().expect("bank_statements", 1)
    ])

def test_bank_statements_last_even_with_earlier_timestamp() -> None:
    run_queue([
        call_enqueue("companies_house", 1, iso_ts(delta_minutes=1)).expect(1),
        call_enqueue("bank_statements", 1, iso_ts(delta_minutes=0)).expect(2),
        call_dequeue().expect("companies_house", 1),
        call_dequeue().expect("bank_statements", 1)
    ])

def test_bank_statements_not_affected_by_duplicates() -> None:
    run_queue([
        call_enqueue("companies_house", 1, iso_ts(delta_minutes=1)).expect(1),
        call_enqueue("bank_statements", 1, iso_ts(delta_minutes=5)).expect(2),
        call_enqueue("bank_statements", 1, iso_ts(delta_minutes=0)).expect(2),
        call_enqueue("id_verification", 2, iso_ts(delta_minutes=2)).expect(3),
        call_dequeue().expect("companies_house", 1),
        call_dequeue().expect("id_verification", 2),
        call_dequeue().expect("bank_statements", 1),
        call_size().expect(0)
    ])

def test_age_no_items_in_queue() -> None:
    run_queue([
        call_age().expect(0)
    ])

def test_age_one_items_in_queue() -> None:
    run_queue([
        call_enqueue("companies_house", 1, iso_ts(delta_minutes=0)).expect(1),
        call_age().expect(0)
    ])

def test_age_two_items() -> None:
    run_queue([
        call_enqueue("companies_house", 1, iso_ts(delta_minutes=0)).expect(1),
        call_enqueue("bank_statements", 1, iso_ts(delta_minutes=5)).expect(2),
        call_age().expect(300)
    ])

def test_age_more_than_two_items() -> None:
    run_queue([
        call_enqueue("companies_house", 1, iso_ts(delta_minutes=0)).expect(1),
        call_enqueue("id_verification", 1, iso_ts(delta_minutes=6)).expect(2),
        call_enqueue("bank_statements", 1, iso_ts(delta_minutes=5)).expect(3),
        call_age().expect(360)
    ])

def test_queue_does_not_track_duplicates_after_purge() -> None:
    run_queue([
        call_enqueue("companies_house", 1, iso_ts(delta_minutes=5)).expect(1),
        call_enqueue("id_verification", 1, iso_ts(delta_minutes=4)).expect(2),
        call_age().expect(60),
        call_purge().expect(True),
        call_size().expect(0),
        call_enqueue("companies_house", 1, iso_ts(delta_minutes=0)).expect(1),
        call_enqueue("id_verification", 1, iso_ts(delta_minutes=6)).expect(2),
        # If others were preserved, the earlier id_verification would be preserved and age would be 240
        call_age().expect(360)
    ])

def test_old_bank_statements_occur_before_other_events_one_event_older_than_five_mins() -> None:
    run_queue([
        call_enqueue("companies_house", 1, iso_ts(delta_minutes=5)).expect(1),
        call_enqueue("bank_statements", 1, iso_ts(delta_minutes=0)).expect(2),

        call_dequeue().expect("bank_statements", 1),
        call_dequeue().expect("companies_house", 1)
    ])

def test_old_bank_statements_occur_before_other_events_multiple_events_one_older_than_five_mins() -> None:
    run_queue([
        call_enqueue("companies_house", 1, iso_ts(delta_minutes=2)).expect(1),
        call_enqueue("bank_statements", 1, iso_ts(delta_minutes=0)).expect(2),
        call_enqueue("id_verification", 2, iso_ts(delta_minutes=5)).expect(3),

        call_dequeue().expect("bank_statements", 1),
        call_dequeue().expect("companies_house", 1),
        call_dequeue().expect("id_verification", 2),
    ])

def test_old_bank_statements_occur_before_later_timestamps() -> None:
    run_queue([
        call_enqueue("bank_statements", 1, iso_ts(delta_minutes=2)).expect(1),
        call_enqueue("companies_house", 1, iso_ts(delta_minutes=3)).expect(2),
        call_enqueue("id_verification", 2, iso_ts(delta_minutes=7)).expect(3),

        call_dequeue().expect("bank_statements", 1),
        call_dequeue().expect("companies_house", 1),
        call_dequeue().expect("id_verification", 2),
    ])

def test_old_bank_statements_occur_only_before_later_timestamps() -> None:
    run_queue([
        call_enqueue("id_verification", 1, iso_ts(delta_minutes=0)).expect(1),
        call_enqueue("bank_statements", 2, iso_ts(delta_minutes=1)).expect(2),
        call_enqueue("companies_house", 3, iso_ts(delta_minutes=7)).expect(3),

        call_dequeue().expect("id_verification", 1),
        call_dequeue().expect("bank_statements", 2),
        call_dequeue().expect("companies_house", 3),
    ])

def test_old_bank_statements_occur_first_along_other_ordering() -> None:
    run_queue([
        call_enqueue("bank_statements", 1, iso_ts(delta_minutes=0)).expect(1),
        call_enqueue("companies_house", 1, iso_ts(delta_minutes=7)).expect(2),
        call_enqueue("id_verification", 2, iso_ts(delta_minutes=2)).expect(3),
        call_enqueue("companies_house", 2, iso_ts(delta_minutes=4)).expect(4),
        call_dequeue().expect("bank_statements", 1),
        call_dequeue().expect("id_verification", 2),
        call_dequeue().expect("companies_house", 2),
        call_dequeue().expect("companies_house", 1)
    ])

def test_multiple_bank_statements_rule_of_three_prioritised_below_old_bank_statements() -> None:
    run_queue([
        call_enqueue("companies_house", 1, iso_ts(delta_minutes=0)).expect(1),
        call_enqueue("bank_statements", 1, iso_ts(delta_minutes=5)).expect(2),
        call_enqueue("bank_statements", 2, iso_ts(delta_minutes=0)).expect(3),
        call_enqueue("credit_check", 1, iso_ts(delta_minutes=5)).expect(4),
        call_dequeue().expect("bank_statements", 2),
        call_dequeue().expect("companies_house", 1),
        call_dequeue().expect("credit_check", 1),
        call_dequeue().expect("bank_statements", 1),
    ])

def test_bank_statement_shifts_only_above_non_bank_statements_with_same_timestamp() -> None:
    run_queue([
        call_enqueue("companies_house", 1, iso_ts(delta_minutes=5)).expect(1),
        call_enqueue("bank_statements", 1, iso_ts(delta_minutes=0)).expect(2),
        call_enqueue("bank_statements", 2, iso_ts(delta_minutes=0)).expect(3),
        call_enqueue("credit_check", 1, iso_ts(delta_minutes=6)).expect(4),
        call_dequeue().expect("bank_statements", 1),
        call_dequeue().expect("bank_statements", 2),
        call_dequeue().expect("companies_house", 1),
        call_dequeue().expect("credit_check", 1),
    ])

def test_bank_statement_multiple_rules_of_three() -> None:
    run_queue([
        call_enqueue("companies_house", 2, iso_ts(delta_minutes=0)).expect(1),
        call_enqueue("bank_statements", 1, iso_ts(delta_minutes=1)).expect(2),
        call_enqueue("id_verification", 2, iso_ts(delta_minutes=2)).expect(3),
        call_enqueue("bank_statements", 2, iso_ts(delta_minutes=7)).expect(4),
        call_enqueue("companies_house", 1, iso_ts(delta_minutes=8)).expect(5),
        call_enqueue("id_verification", 1, iso_ts(delta_minutes=9)).expect(6),
        call_dequeue().expect("companies_house", 2),
        call_dequeue().expect("bank_statements", 1),
        call_dequeue().expect("id_verification", 2),
        call_dequeue().expect("companies_house", 1),
        call_dequeue().expect("id_verification", 1),
        call_dequeue().expect("bank_statements", 2)
    ])


