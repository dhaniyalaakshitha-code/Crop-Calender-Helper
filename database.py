
import json
import csv
import os
from pathlib import Path
from datetime import date

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_FILE = DATA_DIR / "crop_tasks.json"

DATA_DIR.mkdir(exist_ok=True)


def load_tasks():
    if not DATA_FILE.exists():
        save_tasks([])
        return []

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as file:
            tasks = json.load(file)
            return tasks if isinstance(tasks, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def save_tasks(tasks):
    temp_file = DATA_FILE.with_suffix(".tmp")

    with open(temp_file, "w", encoding="utf-8") as file:
        json.dump(tasks, file, indent=4)

    os.replace(temp_file, DATA_FILE)


def add_task(data):
    tasks = load_tasks()

    new_id = max(
        (int(task.get("id", 0)) for task in tasks),
        default=0
    ) + 1

    data["id"] = new_id
    tasks.append(data)

    save_tasks(tasks)
    return data


def update_task(task_id, updated_data):
    tasks = load_tasks()

    for task in tasks:
        if int(task.get("id", 0)) == int(task_id):
            task.update(updated_data)
            save_tasks(tasks)
            return True

    return False


def delete_task(task_id):
    tasks = load_tasks()

    updated = [
        task for task in tasks
        if int(task.get("id", 0)) != int(task_id)
    ]

    if len(updated) == len(tasks):
        return False

    save_tasks(updated)
    return True


def search_tasks(keyword=""):
    tasks = load_tasks()
    keyword = keyword.lower().strip()

    if not keyword:
        return tasks

    return [
        task for task in tasks
        if keyword in task.get("crop", "").lower()
        or keyword in task.get("task", "").lower()
        or keyword in task.get("category", "").lower()
        or keyword in task.get("status", "").lower()
    ]


def get_summary():
    tasks = load_tasks()
    today = date.today().isoformat()

    total = len(tasks)

    completed = sum(
        1 for t in tasks
        if t.get("status") == "Completed"
    )

    pending = sum(
        1 for t in tasks
        if t.get("status") == "Pending"
    )

    in_progress = sum(
        1 for t in tasks
        if t.get("status") == "In Progress"
    )

    overdue = sum(
        1 for t in tasks
        if t.get("status") != "Completed"
        and t.get("due_date", "") < today
        and bool(t.get("due_date"))
    )

    progress = round(
        completed / total * 100, 1
    ) if total else 0

    return {
        "total": total,
        "completed": completed,
        "pending": pending,
        "in_progress": in_progress,
        "overdue": overdue,
        "progress": progress
    }


def export_csv():
    tasks = load_tasks()

    if not tasks:
        return None

    output = DATA_DIR / "crop_report.csv"

    with open(output, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "id", "crop", "task", "category",
                "due_date", "status", "notes"
            ]
        )

        writer.writeheader()
        writer.writerows(tasks)

    return output


def export_markdown():
    tasks = load_tasks()

    lines = [
        "# Crop Calendar Helper Report",
        "",
        f"Total Tasks: {len(tasks)}",
        "",
        "| Crop | Task | Category | Due Date | Status |",
        "|---|---|---|---|---|"
    ]

    for task in tasks:
        lines.append(
            f"| {task.get('crop', '')} "
            f"| {task.get('task', '')} "
            f"| {task.get('category', '')} "
            f"| {task.get('due_date', '')} "
            f"| {task.get('status', '')} |"
        )

    output = DATA_DIR / "crop_report.md"

    output.write_text(
        "\n".join(lines),
        encoding="utf-8"
    )

    return output
