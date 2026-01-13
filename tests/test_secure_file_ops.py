"""
Unit tests for secure file operations.

Tests the security features and functionality of the SecureFileOperations class.
"""

import shutil
import tempfile
from pathlib import Path

import pytest

from src.agents.secure_file_ops import SecureFileOperations, SecurityViolationError


class TestSecureFileOperations:
    """Test SecureFileOperations functionality and security"""

    def setup_method(self):
        """Set up temporary directory for each test"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.secure_ops = SecureFileOperations(self.temp_dir, max_file_size=1024)

    def teardown_method(self):
        """Clean up temporary directory"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_secure_ops_initialization(self):
        """Test SecureFileOperations initialization"""
        assert self.secure_ops.allowed_base_path == self.temp_dir.resolve()
        assert self.secure_ops.max_file_size == 1024
        assert self.temp_dir.exists()

    def test_write_and_read_file(self):
        """Test writing and reading files within allowed directory"""
        content = "Hello, world!"
        file_path = "test.py"

        # Write file
        self.secure_ops.write_file(file_path, content)

        # Verify file exists
        assert self.secure_ops.file_exists(file_path)

        # Read file
        read_content = self.secure_ops.read_file(file_path)
        assert read_content == content

    def test_file_in_subdirectory(self):
        """Test file operations in subdirectories"""
        content = "Subdirectory content"
        file_path = "subdir/test.py"

        # Write file (should create subdirectory)
        self.secure_ops.write_file(file_path, content)

        # Verify file exists
        assert self.secure_ops.file_exists(file_path)

        # Read file
        read_content = self.secure_ops.read_file(file_path)
        assert read_content == content

    def test_directory_traversal_blocked(self):
        """Test that directory traversal attempts are blocked"""
        with pytest.raises(SecurityViolationError, match="outside allowed directory"):
            self.secure_ops.write_file("../escape.py", "malicious content")

        with pytest.raises(SecurityViolationError, match="outside allowed directory"):
            self.secure_ops.read_file("../../../etc/passwd")

    def test_blocked_file_patterns(self):
        """Test that blocked file patterns are rejected"""
        test_cases = [
            ".env",
            "config.py",
            "settings.py",
            ".git/config",
            "__pycache__/test.pyc",
            "secret.key",
            "cert.pem",
        ]

        for blocked_file in test_cases:
            with pytest.raises(SecurityViolationError, match="matches blocked pattern"):
                self.secure_ops.write_file(blocked_file, "content")

    def test_allowed_file_extensions(self):
        """Test that only allowed file extensions are permitted"""
        # Allowed extensions should work
        allowed_files = [
            "test.py",
            "data.json",
            "config.yaml",
            "readme.md",
            "data.csv",
            "app.log",
        ]

        for allowed_file in allowed_files:
            self.secure_ops.write_file(allowed_file, "content")
            assert self.secure_ops.file_exists(allowed_file)

        # Disallowed extensions should fail
        with pytest.raises(SecurityViolationError, match="not allowed"):
            self.secure_ops.write_file("malware.exe", "content")

    def test_file_size_limits(self):
        """Test that file size limits are enforced"""
        # Small file should work
        small_content = "a" * 100
        self.secure_ops.write_file("small.py", small_content)

        # Large file should fail
        large_content = "a" * 2000  # Exceeds 1024 byte limit
        with pytest.raises(SecurityViolationError, match="too large"):
            self.secure_ops.write_file("large.py", large_content)

    def test_file_append_mode(self):
        """Test file append functionality"""
        file_path = "append_test.py"

        # Write initial content
        self.secure_ops.write_file(file_path, "Line 1\\n")

        # Append content
        self.secure_ops.write_file(file_path, "Line 2\\n", append=True)

        # Read and verify both lines
        content = self.secure_ops.read_file(file_path)
        assert "Line 1" in content
        assert "Line 2" in content

    def test_list_files(self):
        """Test listing files in directory"""
        # Create some test files
        files_to_create = ["file1.py", "file2.json", "subdir/file3.md"]
        for file_path in files_to_create:
            self.secure_ops.write_file(file_path, f"Content of {file_path}")

        # List files in root
        files = self.secure_ops.list_files()
        assert "file1.py" in files
        assert "file2.json" in files
        assert "subdir/file3.md" not in files  # Only direct files

        # List files in subdirectory
        subdir_files = self.secure_ops.list_files("subdir")
        assert "file3.md" in subdir_files

    def test_delete_file(self):
        """Test file deletion"""
        file_path = "to_delete.py"

        # Create file
        self.secure_ops.write_file(file_path, "Content to delete")
        assert self.secure_ops.file_exists(file_path)

        # Delete file
        result = self.secure_ops.delete_file(file_path)
        assert result is True
        assert not self.secure_ops.file_exists(file_path)

        # Try to delete non-existent file
        result = self.secure_ops.delete_file("nonexistent.py")
        assert result is False

    def test_read_nonexistent_file(self):
        """Test reading a file that doesn't exist"""
        with pytest.raises(FileNotFoundError):
            self.secure_ops.read_file("nonexistent.py")

    def test_absolute_path_handling(self):
        """Test that absolute paths are handled correctly"""
        # Absolute path within allowed directory should work
        allowed_absolute = self.temp_dir / "absolute_test.py"
        self.secure_ops.write_file(str(allowed_absolute), "absolute content")
        assert self.secure_ops.file_exists(str(allowed_absolute))

        # Absolute path outside allowed directory should fail
        with pytest.raises(SecurityViolationError):
            self.secure_ops.write_file("/tmp/outside.py", "outside content")

    def test_symlink_protection(self):
        """Test protection against symlink attacks"""
        # This test would be more complex and OS-dependent
        # For now, we test that the path validation catches obvious issues
        with pytest.raises(SecurityViolationError):
            # Attempting directory traversal through relative paths
            self.secure_ops.write_file("./../../escape.py", "content")

    def test_get_allowed_base_path(self):
        """Test getting the allowed base path"""
        base_path = self.secure_ops.get_allowed_base_path()
        assert base_path == self.temp_dir.resolve()


class TestSecureFileOperationsEdgeCases:
    """Test edge cases and error conditions"""

    def test_empty_content(self):
        """Test handling empty file content"""
        temp_dir = Path(tempfile.mkdtemp())
        try:
            secure_ops = SecureFileOperations(temp_dir)

            # Write empty file
            secure_ops.write_file("empty.py", "")
            assert secure_ops.file_exists("empty.py")

            # Read empty file
            content = secure_ops.read_file("empty.py")
            assert content == ""
        finally:
            shutil.rmtree(temp_dir)

    def test_unicode_content(self):
        """Test handling Unicode content"""
        temp_dir = Path(tempfile.mkdtemp())
        try:
            secure_ops = SecureFileOperations(temp_dir)

            unicode_content = "Hello 世界! 🌍 café résumé"
            secure_ops.write_file("unicode.py", unicode_content)

            read_content = secure_ops.read_file("unicode.py")
            assert read_content == unicode_content
        finally:
            shutil.rmtree(temp_dir)

    def test_very_deep_directory_structure(self):
        """Test deep directory structures"""
        temp_dir = Path(tempfile.mkdtemp())
        try:
            secure_ops = SecureFileOperations(temp_dir)

            deep_path = "a/b/c/d/e/f/g/h/deep_file.py"
            secure_ops.write_file(deep_path, "deep content")

            assert secure_ops.file_exists(deep_path)
            content = secure_ops.read_file(deep_path)
            assert content == "deep content"
        finally:
            shutil.rmtree(temp_dir)
