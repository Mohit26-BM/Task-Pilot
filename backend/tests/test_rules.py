"""Who can see and change what, input checking, and the project / task rules."""
import pytest

from conftest import PASSWORD
from database import db
from models import ProjectMember, Task, User


@pytest.fixture()
def world(make):
    """An admin, two members, and two projects: Alpha (admin, ann) and Beta (admin, bob)."""
    ids = {
        "admin": make.user("admin@example.com", "Admin"),
        "ann": make.user("ann@example.com", name="Ann"),
        "bob": make.user("bob@example.com", name="Bob"),
        "cy": make.user("cy@example.com", name="Cy"),
    }
    ids["alpha"] = make.project("Alpha", ids["admin"], [ids["ann"]])
    ids["beta"] = make.project("Beta", ids["admin"], [ids["bob"]])
    ids["t_alpha"] = make.task("Alpha task", ids["alpha"], assigned_to=ids["ann"])
    ids["t_beta"] = make.task("Beta task", ids["beta"], assigned_to=ids["bob"])
    return ids


def titles(res):
    return sorted(item["title"] for item in res.get_json())


# ---------- who sees what ----------
def test_a_member_only_sees_their_own_projects_and_tasks(client, login, world):
    ann = login("ann@example.com")
    assert titles(client.get("/projects", headers=ann)) == ["Alpha"]
    assert titles(client.get("/tasks", headers=ann)) == ["Alpha task"]
    assert client.get(f"/projects/{world['alpha']}", headers=ann).status_code == 200
    assert client.get(f"/projects/{world['beta']}", headers=ann).status_code == 404
    stats = client.get("/dashboard/stats", headers=ann).get_json()["cards"]
    assert stats["total_tasks"] == 1 and stats["active_projects"] == 1


def test_an_admin_sees_everything(client, login, world):
    admin = login("admin@example.com")
    assert titles(client.get("/projects", headers=admin)) == ["Alpha", "Beta"]
    assert titles(client.get("/tasks", headers=admin)) == ["Alpha task", "Beta task"]
    assert client.get("/dashboard/stats", headers=admin).get_json()["cards"]["total_tasks"] == 2


def test_members_cannot_use_admin_endpoints(client, login, world):
    ann = login("ann@example.com")
    assert client.get("/users", headers=ann).status_code == 403
    assert client.post("/projects", json={"title": "X"}, headers=ann).status_code == 403
    assert client.put(f"/projects/{world['alpha']}", json={"title": "X"}, headers=ann).status_code == 403
    assert client.delete(f"/projects/{world['alpha']}", headers=ann).status_code == 403
    assert client.post("/tasks", json={"title": "X", "project_id": world["alpha"]}, headers=ann).status_code == 403
    assert client.delete(f"/tasks/{world['t_alpha']}", headers=ann).status_code == 403
    assert client.put(f"/users/{world['bob']}", json={"role": "Admin"}, headers=ann).status_code == 403
    assert client.post(f"/projects/{world['alpha']}/members", json={"user_id": world["bob"]}, headers=ann).status_code == 403


def test_user_options_show_only_names_and_only_people_you_share_a_project_with(client, login, world, make):
    ann = login("ann@example.com")
    people = client.get("/users/options", headers=ann).get_json()
    assert sorted(p["name"] for p in people) == ["Admin", "Ann"]
    assert all(set(p) == {"id", "name"} for p in people), "no emails or roles"
    everyone = client.get("/users/options", headers=login("admin@example.com")).get_json()
    assert len(everyone) == 4 and all(set(p) == {"id", "name"} for p in everyone)


# ---------- what a member may change ----------
def test_a_member_can_only_change_the_status_of_their_tasks(client, login, world):
    ann = login("ann@example.com")
    url = f"/tasks/{world['t_alpha']}"
    assert client.put(url, json={"status": "In Progress"}, headers=ann).get_json()["status"] == "In Progress"
    assert client.put(url, json={"title": "Renamed"}, headers=ann).status_code == 403
    assert client.put(url, json={"status": "Nonsense"}, headers=ann).status_code == 400
    assert client.put(f"/tasks/{world['t_beta']}", json={"status": "Completed"}, headers=ann).status_code == 404


def test_completing_and_reopening_a_task_sets_and_clears_the_finish_time(client, login, world):
    admin = login("admin@example.com")
    url = f"/tasks/{world['t_alpha']}"
    assert client.put(url, json={"status": "Completed"}, headers=admin).get_json()["completed_at"]
    assert client.put(url, json={"status": "Review"}, headers=admin).get_json()["completed_at"] is None


# ---------- assignment rules ----------
def test_assigning_a_task_makes_the_person_a_member_of_that_project(app, client, login, world):
    admin = login("admin@example.com")
    res = client.post("/tasks", json={"title": "Help", "project_id": world["alpha"], "assigned_to": world["cy"]}, headers=admin)
    assert res.status_code == 201
    with app.app_context():
        assert ProjectMember.query.filter_by(project_id=world["alpha"], user_id=world["cy"]).first()
    assert "Help" in titles(client.get("/tasks", headers=login("cy@example.com")))


def test_moving_an_assigned_task_to_another_project_brings_the_assignee_along(app, client, login, world):
    admin = login("admin@example.com")
    assert client.put(f"/tasks/{world['t_alpha']}", json={"project_id": world["beta"]}, headers=admin).status_code == 200
    with app.app_context():
        assert ProjectMember.query.filter_by(project_id=world["beta"], user_id=world["ann"]).first()


def test_removing_a_member_unassigns_their_tasks_in_that_project_only(app, client, login, world):
    admin = login("admin@example.com")
    client.post("/tasks", json={"title": "Other", "project_id": world["beta"], "assigned_to": world["ann"]}, headers=admin)
    assert client.delete(f"/projects/{world['alpha']}/members/{world['ann']}", headers=admin).status_code == 200
    with app.app_context():
        assert db.session.get(Task, world["t_alpha"]).assigned_to is None
        assert Task.query.filter_by(title="Other").first().assigned_to == world["ann"]


# ---------- the last admin ----------
def test_the_last_admin_cannot_be_demoted_but_one_of_two_can(client, login, world, make):
    admin = login("admin@example.com")
    res = client.put(f"/users/{world['admin']}", json={"role": "Member"}, headers=admin)
    assert res.status_code == 400 and "at least one Admin" in res.get_json()["error"]
    assert client.put(f"/users/{world['ann']}", json={"role": "Admin"}, headers=admin).status_code == 200
    assert client.put(f"/users/{world['admin']}", json={"role": "Member"}, headers=admin).status_code == 200
    assert client.put(f"/users/{world['admin']}", json={"role": "Wizard"}, headers=login("ann@example.com")).status_code == 400


# ---------- profile ----------
def test_changing_your_password_needs_the_current_one(client, login, world):
    ann = login("ann@example.com")
    assert client.put("/profile", json={"password": "New-Pass-1!"}, headers=ann).status_code == 403
    assert client.put("/profile", json={"password": "New-Pass-1!", "current_password": "wrong"}, headers=ann).status_code == 403
    assert client.put("/profile", json={"password": "weak", "current_password": PASSWORD}, headers=ann).status_code == 400
    assert client.put("/profile", json={"password": "New-Pass-1!", "current_password": PASSWORD}, headers=ann).status_code == 200
    assert client.post("/login", json={"email": "ann@example.com", "password": "New-Pass-1!"}).status_code == 200
    assert client.post("/login", json={"email": "ann@example.com", "password": PASSWORD}).status_code == 401


def test_the_name_can_change_without_a_password_and_must_be_sane(client, login, world):
    ann = login("ann@example.com")
    assert client.put("/profile", json={"name": "Annie"}, headers=ann).get_json()["name"] == "Annie"
    assert client.put("/profile", json={"name": ""}, headers=ann).status_code == 400
    assert client.put("/profile", json={"name": ["x"]}, headers=ann).status_code == 400


# ---------- input checking ----------
@pytest.mark.parametrize(
    "body",
    [
        {"title": "", "project_id": 1},
        {"title": ["x"], "project_id": 1},
        {"title": "x" * 181, "project_id": 1},
        {"title": "ok", "project_id": "abc"},
        {"title": "ok", "project_id": True},
        {"title": "ok", "project_id": 1, "due_date": "31/12/2026"},
        {"title": "ok", "project_id": 1, "due_date": "2026-02-30"},
        {"title": "ok", "project_id": 1, "due_date": 20260101},
        {"title": "ok", "project_id": 1, "description": "x" * 5001},
        {"title": "ok", "project_id": 1, "assigned_to": "nobody"},
        {"title": "ok", "project_id": 1, "assigned_to": 99999},
    ],
)
def test_bad_task_input_is_refused_with_a_clean_error(client, login, world, body):
    body = {**body, **({"project_id": world["alpha"]} if type(body.get("project_id")) is int else {})}  # 1 stands for the real id; True must stay a boolean
    res = client.post("/tasks", json=body, headers=login("admin@example.com"))
    assert res.status_code in (400, 404), res.get_json()
    assert res.is_json and "error" in res.get_json()


def test_bad_project_input_is_refused(client, login, world):
    admin = login("admin@example.com")
    assert client.post("/projects", json={"title": "ok", "members": "everyone"}, headers=admin).status_code == 400
    assert client.post("/projects", json={"title": {"a": 1}}, headers=admin).status_code == 400
    assert client.post("/projects", json={"title": "x" * 161}, headers=admin).status_code == 400
    ok = client.post("/projects", json={"title": "Fine", "members": [world["ann"], "junk", None, 99999]}, headers=admin)
    assert ok.status_code == 201
    assert sorted(m["name"] for m in ok.get_json()["members"]) == ["Admin", "Ann"]
    assert client.put(f"/projects/{world['alpha']}", json={"title": ""}, headers=admin).status_code == 400
    assert client.post(f"/projects/{world['alpha']}/members", json={"user_id": "abc"}, headers=admin).status_code == 404


def test_a_bad_edit_changes_nothing(client, login, world):
    admin = login("admin@example.com")
    res = client.put(f"/tasks/{world['t_alpha']}", json={"title": "New title", "due_date": "nonsense"}, headers=admin)
    assert res.status_code == 400
    assert client.get("/tasks", headers=admin).get_json()[-1]["title"] in ("Alpha task", "Beta task")
    assert "New title" not in titles(client.get("/tasks", headers=admin))


def test_search_treats_percent_and_underscore_as_plain_characters(client, login, world, make):
    make.task("100% done", world["alpha"])
    make.task("snake_case", world["alpha"])
    admin = login("admin@example.com")
    assert titles(client.get("/tasks?search=%25", headers=admin)) == ["100% done"]
    assert titles(client.get("/tasks?search=_", headers=admin)) == ["snake_case"]
    assert titles(client.get("/tasks?search=ALPHA", headers=admin)) == ["Alpha task"]


def test_filters_check_their_input(client, login, world):
    admin = login("admin@example.com")
    assert client.get("/tasks?project_id=abc", headers=admin).status_code == 400
    assert titles(client.get(f"/tasks?project_id={world['beta']}", headers=admin)) == ["Beta task"]
    assert titles(client.get("/tasks?status=Pending&priority=Medium", headers=admin)) == ["Alpha task", "Beta task"]


def test_deleting_a_project_removes_its_tasks_and_memberships(app, client, login, world):
    admin = login("admin@example.com")
    assert client.delete(f"/projects/{world['alpha']}", headers=admin).status_code == 200
    with app.app_context():
        assert Task.query.filter_by(project_id=world["alpha"]).count() == 0
        assert ProjectMember.query.filter_by(project_id=world["alpha"]).count() == 0
    assert client.delete(f"/projects/{world['alpha']}", headers=admin).status_code == 404
