from ops.provision_school import APPS, SchoolConfig, build_commands


def make_config(**overrides):
    defaults = dict(
        site_name="alnoor.localhost",
        school_name="Al Noor International School",
        admin_password="secret-admin",
        db_root_password="secret-root",
    )
    defaults.update(overrides)
    return SchoolConfig(**defaults)


def test_first_command_creates_the_site():
    cmds = build_commands(make_config())
    assert cmds[0][:3] == ["bench", "new-site", "alnoor.localhost"]
    assert "--admin-password" in cmds[0]
    assert "--db-root-password" in cmds[0]


def test_installs_all_apps_in_order():
    cmds = build_commands(make_config())
    installed = [c[-1] for c in cmds if "install-app" in c]
    assert installed == list(APPS)


def test_sets_school_display_name_via_k12_settings():
    cmds = build_commands(make_config())
    set_value = cmds[-1]
    assert set_value[set_value.index("execute") + 1] == "frappe.client.set_value"
    assert "--kwargs" in set_value
    assert any("Al Noor International School" in part for part in set_value)


def test_school_name_with_apostrophe_is_safely_quoted():
    import ast

    cmds = build_commands(make_config(school_name="St. Mary's School"))
    kwargs_str = cmds[-1][cmds[-1].index("--kwargs") + 1]
    parsed = ast.literal_eval(kwargs_str)
    assert parsed["value"] == "St. Mary's School"
    assert parsed["doctype"] == "K12 Settings"


def test_all_commands_target_the_new_site_after_creation():
    cmds = build_commands(make_config())
    for cmd in cmds[1:]:
        assert "--site" in cmd
        assert cmd[cmd.index("--site") + 1] == "alnoor.localhost"


def test_seeds_default_grades_after_app_install():
    cmds = build_commands(make_config())
    flat = [" ".join(c) for c in cmds]
    seed_index = next(
        i
        for i, c in enumerate(flat)
        if "education_k12.k12_sis.grades.create_default_grade_programs" in c
    )
    last_install_index = max(i for i, c in enumerate(flat) if "install-app" in c)
    assert seed_index > last_install_index


def test_provision_runs_all_commands_in_order_with_env():
    calls = []

    def fake_runner(cmd, check, env):
        calls.append((cmd, check, env))

    from ops.provision_school import provision

    cfg = make_config()
    provision(cfg, runner=fake_runner)

    assert [c[0] for c in calls] == build_commands(cfg)
    assert all(check is True for _, check, _ in calls)
    assert all(env is not None for _, _, env in calls)
