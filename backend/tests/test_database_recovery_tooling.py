from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[2]

BACKUP_SCRIPT = ROOT / "scripts" / "backup_postgres.sh"
RESTORE_SCRIPT = ROOT / "scripts" / "restore_postgres.sh"


def run_script(path, *args, env=None):
    return subprocess.run(
        [str(path), *args],
        capture_output=True,
        text=True,
        env=env,
    )


def test_backup_script_exists_and_is_executable():
    assert BACKUP_SCRIPT.exists()
    assert BACKUP_SCRIPT.stat().st_mode & 0o111


def test_restore_script_exists_and_is_executable():
    assert RESTORE_SCRIPT.exists()
    assert RESTORE_SCRIPT.stat().st_mode & 0o111


def test_backup_requires_database_url():
    result = run_script(BACKUP_SCRIPT)

    assert result.returncode == 2
    assert "Usage:" in result.stdout


def test_backup_rejects_non_postgres_url(tmp_path):
    result = run_script(
        BACKUP_SCRIPT,
        "sqlite:///ptm.db",
        str(tmp_path),
    )

    assert result.returncode == 2
    assert (
        "Backup requires a PostgreSQL database URL."
        in result.stdout
    )


def test_restore_requires_arguments():
    result = run_script(RESTORE_SCRIPT)

    assert result.returncode == 2
    assert "Usage:" in result.stdout


def test_restore_rejects_non_postgres_url(tmp_path):
    backup = tmp_path / "test.dump"
    backup.write_bytes(b"not-a-real-backup")

    result = run_script(
        RESTORE_SCRIPT,
        "sqlite:///ptm.db",
        str(backup),
    )

    assert result.returncode == 2
    assert (
        "Restore requires a PostgreSQL database URL."
        in result.stdout
    )


def test_restore_requires_explicit_authorization(tmp_path):
    backup = tmp_path / "test.dump"
    backup.write_bytes(b"not-a-real-backup")

    result = run_script(
        RESTORE_SCRIPT,
        "postgresql://example.invalid/test",
        str(backup),
    )

    assert result.returncode == 2
    assert (
        "Set PTM_ALLOW_RESTORE=YES"
        in result.stdout
    )


def make_executable(path, content):
    path.write_text(content)
    path.chmod(0o755)


def test_backup_creates_custom_archive_in_output_directory(
    tmp_path,
):
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()

    fake_pg_dump = fake_bin / "pg_dump"

    make_executable(
        fake_pg_dump,
        """#!/usr/bin/env bash
set -euo pipefail

OUTPUT_FILE=""

for argument in "$@"; do
    case "$argument" in
        --file=*)
            OUTPUT_FILE="${argument#--file=}"
            ;;
    esac
done

if [ -z "$OUTPUT_FILE" ]; then
    echo "Missing --file argument."
    exit 1
fi

printf 'fake-postgres-custom-backup\\n' > "$OUTPUT_FILE"
""",
    )

    output_directory = tmp_path / "database-backups"

    env = {
        "PATH": f"{fake_bin}:/usr/bin:/bin",
    }

    result = run_script(
        BACKUP_SCRIPT,
        "postgresql://example.invalid/ptm",
        str(output_directory),
        env=env,
    )

    assert result.returncode == 0
    assert "PASS: Backup created." in result.stdout

    backups = list(
        output_directory.glob(
            "ptm-postgres-*.dump"
        )
    )

    assert len(backups) == 1
    assert backups[0].read_text() == (
        "fake-postgres-custom-backup\n"
    )


def test_restore_success_path_uses_destructive_restore_safeguards(
    tmp_path,
):
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()

    capture_file = tmp_path / "pg_restore_arguments.txt"

    fake_pg_restore = fake_bin / "pg_restore"

    make_executable(
        fake_pg_restore,
        f"""#!/usr/bin/env bash
set -euo pipefail
printf '%s\\n' "$@" > "{capture_file}"
""",
    )

    backup = tmp_path / "ptm-test.dump"
    backup.write_bytes(b"fake-backup")

    env = {
        "PATH": f"{fake_bin}:/usr/bin:/bin",
        "PTM_ALLOW_RESTORE": "YES",
    }

    database_url = (
        "postgresql://example.invalid/ptm"
    )

    result = run_script(
        RESTORE_SCRIPT,
        database_url,
        str(backup),
        env=env,
    )

    assert result.returncode == 0
    assert "PASS: Restore completed." in result.stdout

    arguments = capture_file.read_text().splitlines()

    assert "--clean" in arguments
    assert "--if-exists" in arguments
    assert "--no-owner" in arguments
    assert "--no-privileges" in arguments
    assert "--exit-on-error" in arguments
    assert f"--dbname={database_url}" in arguments
    assert str(backup) in arguments
