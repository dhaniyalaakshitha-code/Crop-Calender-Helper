
from nicegui import ui
import sqlite3
import csv
import calendar
from pathlib import Path
from datetime import date, datetime

# =====================================================
# 1. APPLICATION CONFIGURATION
# =====================================================

BASE_DIR = Path(__file__).resolve().parent
DB_FILE = BASE_DIR / "crop_calendar.db"

ui.colors(
    primary="#238636",
    secondary="#65a765",
    accent="#f0b429"
)

ui.add_head_html("""
<style>
body {
    background: #f4f8f3;
    font-family: Arial, sans-serif;
}
.stat-card {
    border-radius: 14px;
    min-height: 120px;
}
.task-card {
    border-radius: 12px;
}
</style>
""")


# =====================================================
# 2. DATABASE SETUP
# =====================================================

def get_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_database():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                crop TEXT NOT NULL,
                task TEXT NOT NULL,
                category TEXT NOT NULL,
                due_date TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Pending',
                notes TEXT DEFAULT ''
            )
        """)
        conn.commit()


initialize_database()


# =====================================================
# 3. DATABASE FUNCTIONS
# =====================================================

def load_tasks():
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT * FROM tasks
            ORDER BY due_date ASC, id DESC
        """).fetchall()

    return [dict(row) for row in rows]


def add_task(data):
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO tasks
            (crop, task, category, due_date, status, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            data["crop"],
            data["task"],
            data["category"],
            data["due_date"],
            data["status"],
            data["notes"]
        ))
        conn.commit()


def update_task(task_id, data):
    with get_connection() as conn:
        cursor = conn.execute("""
            UPDATE tasks
            SET crop=?, task=?, category=?,
                due_date=?, status=?, notes=?
            WHERE id=?
        """, (
            data["crop"],
            data["task"],
            data["category"],
            data["due_date"],
            data["status"],
            data["notes"],
            task_id
        ))
        conn.commit()
        return cursor.rowcount > 0


def delete_task(task_id):
    with get_connection() as conn:
        cursor = conn.execute(
            "DELETE FROM tasks WHERE id=?",
            (task_id,)
        )
        conn.commit()
        return cursor.rowcount > 0


def get_summary():
    tasks = load_tasks()
    today = date.today().isoformat()

    total = len(tasks)
    completed = sum(
        1 for t in tasks if t["status"] == "Completed"
    )
    pending = sum(
        1 for t in tasks if t["status"] == "Pending"
    )
    in_progress = sum(
        1 for t in tasks if t["status"] == "In Progress"
    )
    overdue = sum(
        1 for t in tasks
        if t["due_date"] < today
        and t["status"] != "Completed"
    )

    progress = round(
        completed / total * 100
    ) if total else 0

    return {
        "total": total,
        "completed": completed,
        "pending": pending,
        "in_progress": in_progress,
        "overdue": overdue,
        "progress": progress
    }


# =====================================================
# 4. COMMON FUNCTIONS
# =====================================================

def notify(message, color="positive"):
    ui.notify(message, type=color)


def validate_date(value):
    try:
        datetime.strptime(value, "%Y-%m-%d")
        return True
    except (ValueError, TypeError):
        return False


# =====================================================
# 5. ADD AND EDIT TASK DIALOG
# =====================================================

def task_dialog(task=None):

    editing = task is not None

    with ui.dialog() as dialog, ui.card().classes(
        "w-full max-w-lg p-6"
    ):

        ui.label(
            "Edit Crop Task" if editing else "Add New Crop Task"
        ).classes("text-2xl font-bold text-green-800")

        crop = ui.input(
            "Crop Name",
            value=task["crop"] if editing else ""
        ).classes("w-full")

        task_name = ui.input(
            "Task Name",
            value=task["task"] if editing else ""
        ).classes("w-full")

        category = ui.select(
            [
                "Sowing",
                "Watering",
                "Fertilizing",
                "Harvesting",
                "Pest Control",
                "Weeding",
                "Other"
            ],
            label="Task Category",
            value=task["category"] if editing else "Sowing"
        ).classes("w-full")

        due_date = ui.input(
            "Due Date",
            value=task["due_date"] if editing
            else date.today().isoformat()
        ).props("type=date").classes("w-full")

        status = ui.select(
            ["Pending", "In Progress", "Completed"],
            label="Status",
            value=task["status"] if editing else "Pending"
        ).classes("w-full")

        notes = ui.textarea(
            "Additional Notes",
            value=task["notes"] if editing else ""
        ).classes("w-full")

        def save_task():

            if not crop.value or not crop.value.strip():
                notify("Enter the crop name", "warning")
                return

            if not task_name.value or not task_name.value.strip():
                notify("Enter the task name", "warning")
                return

            if not validate_date(due_date.value):
                notify("Select a valid due date", "warning")
                return

            data = {
                "crop": crop.value.strip(),
                "task": task_name.value.strip(),
                "category": category.value,
                "due_date": due_date.value,
                "status": status.value,
                "notes": notes.value or ""
            }

            try:
                if editing:
                    update_task(task["id"], data)
                    notify("Task updated successfully!")
                else:
                    add_task(data)
                    notify("New task added successfully!")

                dialog.close()
                refresh_all()

            except sqlite3.Error as error:
                notify(f"Database error: {error}", "negative")

        with ui.row().classes("w-full justify-end mt-4"):

            ui.button(
                "Cancel",
                on_click=dialog.close
            ).props("flat")

            ui.button(
                "Save Task",
                icon="save",
                on_click=save_task
            ).classes("bg-green-700 text-white")

    dialog.open()


# =====================================================
# 6. DELETE TASK
# =====================================================

def confirm_delete(task_id):

    with ui.dialog() as dialog, ui.card():

        ui.label(
            "Are you sure you want to delete this task?"
        ).classes("text-lg font-bold")

        with ui.row().classes("justify-end w-full"):

            ui.button(
                "Cancel",
                on_click=dialog.close
            ).props("flat")

            def remove():

                delete_task(task_id)
                dialog.close()
                notify("Task deleted successfully!")
                refresh_all()

            ui.button(
                "Delete",
                icon="delete",
                on_click=remove
            ).props("color=negative")

    dialog.open()


# =====================================================
# 7. TASK CARD DISPLAY
# =====================================================

def task_list(tasks, container):

    container.clear()

    if not tasks:
        with container:
            ui.label("No tasks found.").classes(
                "text-gray-500 p-4"
            )
        return

    with container:

        for task in tasks:

            with ui.card().classes(
                "w-full p-4 task-card shadow-sm"
            ):

                with ui.row().classes(
                    "w-full justify-between items-center flex-wrap"
                ):

                    with ui.column().classes("gap-1"):

                        ui.label(
                            task["crop"]
                        ).classes(
                            "text-lg font-bold text-green-900"
                        )

                        ui.label(
                            task["task"]
                        ).classes("font-medium")

                        ui.label(
                            f'{task["category"]} | Due: {task["due_date"]}'
                        ).classes("text-sm text-gray-500")

                    with ui.row().classes("items-center"):

                        colors = {
                            "Completed": "green",
                            "Pending": "orange",
                            "In Progress": "blue"
                        }

                        ui.badge(
                            task["status"],
                            color=colors.get(task["status"], "grey")
                        )

                        ui.button(
                            icon="edit",
                            on_click=lambda t=task: task_dialog(t)
                        ).props("flat round color=primary")

                        ui.button(
                            icon="delete",
                            on_click=lambda tid=task["id"]: confirm_delete(tid)
                        ).props("flat round color=negative")

                if task["notes"]:
                    ui.label(
                        task["notes"]
                    ).classes("text-sm text-gray-500")


# =====================================================
# 8. DASHBOARD
# =====================================================

with ui.header().classes(
    "bg-green-900 items-center justify-between px-5 py-4"
):

    with ui.row().classes("items-center gap-2"):
        ui.icon("eco", size="2rem").classes("text-white")
        ui.label(
            "Crop Calendar Helper"
        ).classes("text-xl font-bold text-white")

    ui.label(
        date.today().strftime("%d %B %Y")
    ).classes("text-white")


ui.label(
    "🌱 Welcome to Your Farm Dashboard"
).classes(
    "text-3xl font-bold text-green-900 mt-6 ml-4"
)

ui.label(
    "Manage your crops, farming activities and schedules."
).classes("text-gray-600 ml-4")


# =====================================================
# 9. NAVIGATION TABS
# =====================================================

with ui.tabs().classes("w-full bg-white") as tabs:

    dashboard_tab = ui.tab(
        "Dashboard", icon="dashboard"
    )

    tasks_tab = ui.tab(
        "All Tasks", icon="task"
    )

    calendar_tab = ui.tab(
        "Crop Calendar", icon="calendar_month"
    )

    analytics_tab = ui.tab(
        "Analytics", icon="analytics"
    )

    reports_tab = ui.tab(
        "Reports", icon="description"
    )


# =====================================================
# 10. PAGE CONTENT
# =====================================================

with ui.tab_panels(
    tabs,
    value=dashboard_tab
).classes("w-full"):

    # ---------------------------------------------
    # DASHBOARD PANEL
    # ---------------------------------------------

    with ui.tab_panel(dashboard_tab):

        stats_container = ui.row().classes(
            "w-full gap-4 flex-wrap"
        )

        ui.label(
            "Recent Crop Activities"
        ).classes("text-xl font-bold text-green-900 mt-4")

        recent_container = ui.column().classes("w-full gap-3")

        ui.button(
            "Add New Task",
            icon="add",
            on_click=lambda: task_dialog()
        ).classes("bg-green-700 text-white")

        ui.label(
            "Farming Tip 🌿"
        ).classes("text-xl font-bold text-green-800 mt-4")

        ui.label(
            "Keep a regular schedule for watering, "
            "fertilizing and monitoring your crops."
        ).classes("text-gray-600")

    # ---------------------------------------------
    # ALL TASKS PANEL
    # ---------------------------------------------

    with ui.tab_panel(tasks_tab):

        with ui.row().classes(
            "w-full justify-between items-center flex-wrap"
        ):

            ui.label(
                "Manage Crop Tasks"
            ).classes("text-2xl font-bold text-green-900")

            ui.button(
                "Add Task",
                icon="add",
                on_click=lambda: task_dialog()
            ).classes("bg-green-700 text-white")

        search_input = ui.input(
            placeholder="Search crop or task..."
        ).props("outlined clearable").classes("w-full")

        status_filter = ui.select(
            ["All", "Pending", "In Progress", "Completed"],
            value="All",
            label="Filter by Status"
        ).classes("w-full max-w-xs")

        task_container = ui.column().classes("w-full gap-3")

        def render_tasks():

            tasks = load_tasks()

            search_text = (search_input.value or "").lower()

            if search_text:
                tasks = [
                    t for t in tasks
                    if search_text in t["crop"].lower()
                    or search_text in t["task"].lower()
                    or search_text in t["category"].lower()
                ]

            if status_filter.value != "All":
                tasks = [
                    t for t in tasks
                    if t["status"] == status_filter.value
                ]

            task_list(tasks, task_container)

        search_input.on_value_change(lambda _: render_tasks())
        status_filter.on_value_change(lambda _: render_tasks())

    # ---------------------------------------------
    # CALENDAR PANEL
    # ---------------------------------------------

    with ui.tab_panel(calendar_tab):

        ui.label(
            "Crop Activity Calendar"
        ).classes("text-2xl font-bold text-green-900")

        with ui.row().classes("items-center gap-3"):

            month_select = ui.select(
                list(calendar.month_name)[1:],
                value=date.today().strftime("%B"),
                label="Month"
            ).classes("w-48")

            year_select = ui.number(
                "Year",
                value=date.today().year,
                min=2000,
                max=2100,
                precision=0
            ).classes("w-32")

        calendar_container = ui.column().classes("w-full")

    # ---------------------------------------------
    # ANALYTICS PANEL
    # ---------------------------------------------

    with ui.tab_panel(analytics_tab):

        ui.label(
            "Crop Task Analytics"
        ).classes("text-2xl font-bold text-green-900")

        analytics_container = ui.column().classes("w-full gap-4")

    # ---------------------------------------------
    # REPORTS PANEL
    # ---------------------------------------------

    with ui.tab_panel(reports_tab):

        ui.label(
            "Crop Activity Reports"
        ).classes("text-2xl font-bold text-green-900")

        report_container = ui.column().classes("w-full gap-3")

        ui.button(
            "Export CSV Report",
            icon="download",
            on_click=lambda: export_report()
        ).classes("bg-green-700 text-white")


# =====================================================
# 11. CALENDAR RENDERING
# =====================================================

def render_calendar():

    calendar_container.clear()

    if not year_select.value:
        return

    month_number = list(calendar.month_name).index(
        month_select.value
    )

    year = int(year_select.value)

    tasks = [
        t for t in load_tasks()
        if t["due_date"].startswith(
            f"{year}-{month_number:02d}"
        )
    ]

    with calendar_container:

        with ui.grid(columns=7).classes("w-full gap-2"):

            for day_name in [
                "Mon", "Tue", "Wed",
                "Thu", "Fri", "Sat", "Sun"
            ]:

                with ui.card().classes(
                    "bg-green-800 text-white text-center p-2"
                ):
                    ui.label(day_name)

            weeks = calendar.monthcalendar(year, month_number)

            for week in weeks:

                for day in week:

                    with ui.card().classes(
                        "w-full min-h-24 p-2"
                    ):

                        if day == 0:
                            continue

                        ui.label(str(day)).classes(
                            "font-bold text-green-800"
                        )

                        for task in tasks:

                            if task["due_date"].endswith(
                                f"-{day:02d}"
                            ):

                                ui.label(
                                    task["crop"] + ": " + task["task"]
                                ).classes(
                                    "text-xs bg-green-100 "
                                    "text-green-900 p-1 rounded"
                                )


month_select.on_value_change(
    lambda _: render_calendar()
)

year_select.on_value_change(
    lambda _: render_calendar()
)


# =====================================================
# 12. ANALYTICS RENDERING
# =====================================================

def render_analytics():

    analytics_container.clear()

    summary = get_summary()

    with analytics_container:

        with ui.row().classes("w-full gap-4 flex-wrap"):

            for label, value in [
                ("Total Tasks", summary["total"]),
                ("Completed", summary["completed"]),
                ("Pending", summary["pending"]),
                ("In Progress", summary["in_progress"]),
                ("Overdue", summary["overdue"])
            ]:

                with ui.card().classes(
                    "p-5 min-w-32 stat-card"
                ):

                    ui.label(label).classes("text-gray-500")
                    ui.label(str(value)).classes(
                        "text-3xl font-bold text-green-800"
                    )

        ui.label(
            "Task Completion Progress"
        ).classes("text-xl font-bold mt-3")

        ui.label(
            f'{summary["progress"]}% completed'
        )

        ui.linear_progress(
            value=summary["progress"] / 100
        ).props("color=positive rounded")

        ui.label(
            "Task Status Distribution"
        ).classes("text-xl font-bold mt-4")

        if summary["total"]:

            ui.echart({
                "tooltip": {"trigger": "item"},
                "legend": {"bottom": "0"},
                "series": [{
                    "type": "pie",
                    "radius": ["40%", "70%"],
                    "data": [
                        {
                            "name": "Completed",
                            "value": summary["completed"]
                        },
                        {
                            "name": "Pending",
                            "value": summary["pending"]
                        },
                        {
                            "name": "In Progress",
                            "value": summary["in_progress"]
                        }
                    ]
                }]
            }).classes("w-full h-80")

        else:
            ui.label(
                "Add tasks to see your analytics."
            )


# =====================================================
# 13. REPORTS
# =====================================================

def render_reports():

    report_container.clear()

    summary = get_summary()

    with report_container:

        for label, value in [
            ("Total Tasks", summary["total"]),
            ("Completed Tasks", summary["completed"]),
            ("Pending Tasks", summary["pending"]),
            ("In Progress", summary["in_progress"]),
            ("Overdue Tasks", summary["overdue"]),
            ("Completion Percentage", str(summary["progress"]) + "%")
        ]:

            with ui.card().classes("w-full p-3"):
                ui.label(
                    f"{label}: {value}"
                ).classes("font-medium")


def export_report():

    tasks = load_tasks()

    if not tasks:
        notify("No tasks available to export", "warning")
        return

    file_path = BASE_DIR / "crop_report.csv"

    with open(
        file_path,
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=[
                "id",
                "crop",
                "task",
                "category",
                "due_date",
                "status",
                "notes"
            ]
        )

        writer.writeheader()
        writer.writerows(tasks)

    ui.download(str(file_path))
    notify("CSV report created successfully!")


# =====================================================
# 14. REFRESH ALL SECTIONS
# =====================================================

def refresh_all():

    summary = get_summary()
    tasks = load_tasks()

    # Dashboard statistics

    stats_container.clear()

    with stats_container:

        for label, value in [
            ("Total Tasks", summary["total"]),
            ("Completed", summary["completed"]),
            ("Pending", summary["pending"]),
            ("Overdue", summary["overdue"])
        ]:

            with ui.card().classes(
                "p-5 min-w-40 stat-card shadow-sm"
            ):

                ui.label(label).classes("text-gray-500")
                ui.label(str(value)).classes(
                    "text-3xl font-bold text-green-800"
                )

    # Recent activities

    task_list(tasks[:5], recent_container)

    # Other sections

    render_tasks()
    render_calendar()
    render_analytics()
    render_reports()


# =====================================================
# 15. START APPLICATION
# =====================================================

refresh_all()

ui.run(
    host="127.0.0.1",
    port=8080,
    title="Crop Calendar Helper",
    reload=False
)
