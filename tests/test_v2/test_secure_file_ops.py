import pytest

from src.v2.secure_file_ops import SecureFileOperations, SecurityViolationError


def test_secure_file_ops_allows_write_and_read(tmp_path):
    ops = SecureFileOperations(tmp_path)
    ops.write_file("notes.md", "hello")
    assert ops.read_file("notes.md") == "hello"


def test_secure_file_ops_blocks_traversal(tmp_path):
    ops = SecureFileOperations(tmp_path)
    with pytest.raises(SecurityViolationError):
        ops.write_file("../evil.txt", "nope")
