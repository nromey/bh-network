import subprocess
import sys
import textwrap
from pathlib import Path

import pytest


BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


@pytest.fixture
def sample_repo(tmp_path, monkeypatch):
    nets_content = textwrap.dedent(
        """
        time_zone: America/New_York

        nets:
          - id: alpha-net
            category: bhn
            name: Alpha Net
            description: "Alpha description."
            start_local: "10:00"
            duration_min: 60
            rrule: "FREQ=WEEKLY;BYDAY=MO"
            time_zone: America/New_York
        """
    ).strip() + "\n"

    nets_file = tmp_path / "nets.yml"
    nets_file.write_text(nets_content, encoding="utf-8")

    pending_dir = tmp_path / "pending"
    pending_dir.mkdir()

    roles_file = tmp_path / "roles.yml"
    roles_file.write_text(
        textwrap.dedent(
            """
            publishers:
              - publisher
            reviewers:
              - reviewer
            """
        ).strip() + "\n",
        encoding="utf-8",
    )

    monkeypatch.setenv("BHN_NETS_FILE", str(nets_file))
    monkeypatch.setenv("BHN_NETS_OUTPUT_DIR", str(tmp_path))
    monkeypatch.setenv("BHN_NETS_ROLES", str(roles_file))
    monkeypatch.setenv("BHN_NETS_AUTO_PUSH", "0")
    monkeypatch.delenv("BHN_NETS_DEFAULT_USER", raising=False)

    subprocess.run(["git", "-c", "init.defaultBranch=main", "init"], cwd=tmp_path, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    subprocess.run(["git", "config", "user.name", "Test Bot"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", "nets.yml"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "Initial nets"], cwd=tmp_path, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    return {
        "root": tmp_path,
        "nets_file": nets_file,
        "pending_dir": pending_dir,
        "roles_file": roles_file,
    }


@pytest.fixture
def app(sample_repo):
    import app as nets_app

    flask_app = nets_app.create_app()
    flask_app.config.update(TESTING=True)
    yield flask_app


@pytest.fixture
def client(app):
    return app.test_client()
