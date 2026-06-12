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
    assert "set-value" in set_value or "execute" in set_value
    assert any("Al Noor International School" in part for part in set_value)


def test_all_commands_target_the_new_site_after_creation():
    cmds = build_commands(make_config())
    for cmd in cmds[1:]:
        assert "--site" in cmd
        assert cmd[cmd.index("--site") + 1] == "alnoor.localhost"
