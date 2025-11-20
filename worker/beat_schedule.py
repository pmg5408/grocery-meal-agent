beat_schedule = {
    "scan-users-for-meal-triggers": {
        "task": "worker.tasks.scanMealTriggersAndQueueUsers",
        "schedule": 60.0,
    },
}