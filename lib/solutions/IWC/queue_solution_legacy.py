from dataclasses import dataclass
from datetime import datetime
from enum import IntEnum
from functools import cmp_to_key

# LEGACY CODE ASSET
# RESOLVED on deploy
from solutions.IWC.task_types import TaskSubmission, TaskDispatch

class Priority(IntEnum):
    """Represents the queue ordering tiers observed in the legacy system."""
    HIGH = 1
    NORMAL = 2

@dataclass
class Provider:
    name: str
    base_url: str
    depends_on: list[str]

MAX_TIMESTAMP = datetime.max.replace(tzinfo=None)

COMPANIES_HOUSE_PROVIDER = Provider(
    name="companies_house", base_url="https://fake.companieshouse.co.uk", depends_on=[]
)


CREDIT_CHECK_PROVIDER = Provider(
    name="credit_check",
    base_url="https://fake.creditcheck.co.uk",
    depends_on=["companies_house"],
)


BANK_STATEMENTS_PROVIDER = Provider(
    name="bank_statements", base_url="https://fake.bankstatements.co.uk", depends_on=[]
)

ID_VERIFICATION_PROVIDER = Provider(
    name="id_verification", base_url="https://fake.idv.co.uk", depends_on=[]
)


REGISTERED_PROVIDERS: list[Provider] = [
    BANK_STATEMENTS_PROVIDER,
    COMPANIES_HOUSE_PROVIDER,
    CREDIT_CHECK_PROVIDER,
    ID_VERIFICATION_PROVIDER,
]

class Queue:
    def __init__(self):
        self._queue = []

        # Tracks mapping of users to providers
        self._queue_users_to_providers: dict[int, list[str]] = {}

    def _collect_dependencies(self, task: TaskSubmission) -> list[TaskSubmission]:
        provider = next((p for p in REGISTERED_PROVIDERS if p.name == task.provider), None)
        if provider is None:
            return []

        tasks: list[TaskSubmission] = []
        for dependency in provider.depends_on:
            duplicate_provider, curr_index = self.get_provider_and_index(dependency, task.user_id)

            if not duplicate_provider:
                dependency_task = TaskSubmission(
                    provider=dependency,
                    user_id=task.user_id,
                    timestamp=task.timestamp,
                )
                tasks.extend(self._collect_dependencies(dependency_task))
                tasks.append(dependency_task)
            else:
                self._queue[curr_index].timestamp = min(self._queue[curr_index].timestamp, task.timestamp)

        return tasks

    @staticmethod
    def _priority_for_task(task):
        metadata = task.metadata
        raw_priority = metadata.get("priority", Priority.NORMAL)
        try:
            return Priority(raw_priority)
        except (TypeError, ValueError):
            return Priority.NORMAL

    @staticmethod
    def _earliest_group_timestamp_for_task(task):
        metadata = task.metadata
        return metadata.get("group_earliest_timestamp", MAX_TIMESTAMP)

    @staticmethod
    def _timestamp_for_task(task):
        timestamp = task.timestamp
        if isinstance(timestamp, datetime):
            return timestamp.replace(tzinfo=None)
        if isinstance(timestamp, str):
            return datetime.fromisoformat(timestamp).replace(tzinfo=None)
        return timestamp

    # Give a higher number so other values are sorted earlier
    @staticmethod
    def _deprioritise_bank_statements(task: TaskSubmission):
        if task.provider == BANK_STATEMENTS_PROVIDER.name:
            return 1
        return 0

    def get_provider_and_index(self, provider: str, user_id: int) -> tuple[str, int]:
        try:
            existing_user_providers = self._queue_users_to_providers[user_id]
            if provider in existing_user_providers:
                duplicate_provider = provider
                for index, task in enumerate(self._queue):
                    if task.provider == provider:
                        curr_index = index
                        return duplicate_provider, curr_index
        except KeyError:
            pass
        return "", -1

    def enqueue(self, item: TaskSubmission) -> int:
        tasks = [*self._collect_dependencies(item), item]

        duplicate_provider, curr_index = self.get_provider_and_index(item.provider, item.user_id)

        for task in tasks:
            metadata = task.metadata
            metadata.setdefault("priority", Priority.NORMAL)
            metadata.setdefault("group_earliest_timestamp", MAX_TIMESTAMP)
            if not duplicate_provider:
                # Always ensure the bank statements tasks are at the end
                bank_statements_tasks  = []
                curr_pos = self.size - 1

                while (self.size > 0 and self._queue[curr_pos].provider == BANK_STATEMENTS_PROVIDER.name
                        and (task.provider != BANK_STATEMENTS_PROVIDER.name or task.timestamp < self._queue[-1].timestamp)):
                    bank_statements_tasks.append(self._queue.pop(curr_pos))
                    curr_pos -= 1

                self._queue.append(task)
                if len(bank_statements_tasks) > 0:
                    for bank_task in bank_statements_tasks:
                        self._queue.append(bank_task)
                try:
                    self._queue_users_to_providers[item.user_id].append(item.provider)
                except KeyError:
                    self._queue_users_to_providers[item.user_id] = [item.provider]
            else:
                self._queue[curr_index].timestamp = min(self._queue[curr_index].timestamp, item.timestamp)

        return self.size

    def dequeue(self):
        if self.size == 0:
            return None

        user_ids = {task.user_id for task in self._queue}
        task_count = {}
        priority_timestamps = {}
        for user_id in user_ids:
            user_tasks = [t for t in self._queue if t.user_id == user_id]
            earliest_timestamp = sorted(user_tasks, key=lambda t: t.timestamp)[0].timestamp
            priority_timestamps[user_id] = earliest_timestamp
            task_count[user_id] = len(user_tasks)

        for task in self._queue:
            metadata = task.metadata
            current_earliest = metadata.get("group_earliest_timestamp", MAX_TIMESTAMP)
            raw_priority = metadata.get("priority")
            try:
                priority_level = Priority(raw_priority)
            except (TypeError, ValueError):
                priority_level = None

            if priority_level is None or priority_level == Priority.NORMAL:
                metadata["group_earliest_timestamp"] = MAX_TIMESTAMP
                if task_count[task.user_id] >= 3:
                    metadata["group_earliest_timestamp"] = priority_timestamps[task.user_id]
                    metadata["priority"] = Priority.HIGH
                else:
                    metadata["priority"] = Priority.NORMAL
            else:
                metadata["group_earliest_timestamp"] = current_earliest
                metadata["priority"] = priority_level

        self._queue.sort(
            key=lambda i: (
                self._priority_for_task(i),
                self._earliest_group_timestamp_for_task(i),
                self._deprioritise_bank_statements(i)
            )
        )

        # Brute force pairwise comparison, then will test adding sorting criteria
        # for i in range(len(self._queue)):
        #     curr_task_i: TaskSubmission = self._queue[i]
        #     for j in range(len(self._queue)):
        #         # Do not swap same item or previous items back
        #         if i >= j:
        #             continue
        #         curr_task_j: TaskSubmission = self._queue[j]
        #         if (curr_task_i.provider != BANK_STATEMENTS_PROVIDER.name
        #             and curr_task_j.provider != BANK_STATEMENTS_PROVIDER.name):
        #             continue
        #
        #         age: int = self.__calculate_difference_seconds(datetime.fromisoformat(curr_task_j.timestamp), datetime.fromisoformat(curr_task_i.timestamp))
        #
        #         # Check > 5 mins (300 seconds)
        #         if age >= 300:
        #             if curr_task_j.provider == BANK_STATEMENTS_PROVIDER.name:
        #                 # Swap i and j where j should be moved forward
        #                 temp = curr_task_i
        #                 self._queue[i] = self._queue[j]
        #                 self._queue[j] = temp

        self._queue.sort(key=cmp_to_key(self._prioritise_older_bank_statements))

        self._queue.sort(key=lambda i: self._timestamp_for_task(i))


        task = self._queue.pop(0)

        # Update queue to remove provider from item
        user_id = task.user_id
        provider = task.provider
        curr_providers = self._queue_users_to_providers[user_id]
        for index, curr_provider in enumerate(curr_providers):
            # Remove item from the queue to indicate it is no longer part of it
            # There can only be one item due to deduplication rules
            if provider == curr_provider:
                curr_providers.pop(index)
                break


        return TaskDispatch(
            provider=provider,
            user_id=user_id
        )

    @property
    def size(self):
        return len(self._queue)

    @property
    def age(self):
        if self.size == 0:
            return 0

        # No time gap, so return 0
        if self.size == 1:
            return 0

        if self.size == 2:
            return self._calculate_difference_seconds_abs(datetime.fromisoformat(self._queue[0].timestamp), datetime.fromisoformat(self._queue[1].timestamp))

        newest_timestamp = datetime.fromisoformat(self._queue[0].timestamp)
        oldest_timestamp = newest_timestamp
        for i in range(1, self.size - 1):
            curr_timestamp = datetime.fromisoformat(self._queue[i].timestamp)
            if curr_timestamp < newest_timestamp:
                newest_timestamp = curr_timestamp
            elif curr_timestamp > oldest_timestamp:
                oldest_timestamp = curr_timestamp

        return self._calculate_difference_seconds_abs(newest_timestamp, oldest_timestamp)


    def _prioritise_older_bank_statements(self, x: TaskSubmission, y: TaskSubmission) -> int:
        if y.provider != BANK_STATEMENTS_PROVIDER.name:
            return 1

        age: int = self._calculate_difference_seconds(datetime.fromisoformat(y.timestamp), datetime.fromisoformat(x.timestamp))

        # Check > 5 mins (300 seconds)
        if age >= 300:
            # Return lower value so it is prioritised earlier
            return 0
        return 1

    @staticmethod
    def _calculate_difference_seconds(first_timestamp, second_timestamp) -> int:
        return int((first_timestamp - second_timestamp).total_seconds())

    @staticmethod
    def _calculate_difference_seconds_abs(first_timestamp, second_timestamp) -> int:
        return int((abs(first_timestamp - second_timestamp)).total_seconds())

    def purge(self):
        self._queue.clear()
        self._queue_users_to_providers.clear()
        return True

    def contents(self):
        return self._queue

"""
===================================================================================================

The following code is only to visualise the final usecase.
No changes are needed past this point.

To test the correct behaviour of the queue system, import the `Queue` class directly in your tests.

===================================================================================================

```python
import asyncio
import logging
from fastapi import FastAPI
from contextlib import asynccontextmanager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(queue_worker())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        logger.info("Queue worker cancelled on shutdown.")


app = FastAPI(lifespan=lifespan)
queue = Queue()


@app.get("/")
def read_root():
    return {
        "registered_providers": [
            {"name": p.name, "base_url": p.base_url} for p in registered_providers
        ]
    }


class DataRequest(BaseModel):
    user_id: int
    providers: list[str]


@app.post("/fetch_customer_data")
def fetch_customer_data(data: DataRequest):
    provider_names = [p.name for p in registered_providers]

    for provider in data.providers:
        if provider not in provider_names:
            logger.warning(f"Provider {provider} doesn't exists. Skipping")
            continue

        queue.enqueue(
            TaskSubmission(
                provider=provider,
                user_id=data.user_id,
                timestamp=datetime.now(),
            )
        )

    return {"status": f"{len(data.providers)} Task(s) added to queue"}


async def queue_worker():
    while True:
        if queue.size == 0:
            await asyncio.sleep(1)
            continue

        task = queue.dequeue()
        if not task:
            continue

        logger.info(f"Processing task: {task}")
        await asyncio.sleep(2)
        logger.info(f"Finished task: {task}")
```
"""

