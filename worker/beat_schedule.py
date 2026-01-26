beat_schedule = {
    "scan-users-for-meal-triggers": {
        "task": "worker.tasks.scanMealTriggersAndQueueUsers",
        "schedule": 60.0,
    },
    "generate-daily-meals-batch": {
        "task": "worker.tasks.generateDailyMealsBatch",
        "schedule": 900.0,  # Every 15 minutes
    },
}
