# coding=utf-8
"""
Tests for utility functions
"""
from subprocess import TimeoutExpired
from unittest import TestCase

from utils import run_subprocess


class UtilityTests(TestCase):
    """
    Tests for utility functions
    """

    def test_run_subprocess_no_shell_success(self):
        """
        Tests successful execution with output
        """
        code, out = run_subprocess(
            ["echo", "123   "],
            timeout=999999999,
            shell=False,
            stdin=None,
        )
        self.assertEqual(code, 0)
        self.assertEqual(out, "123   \n")

    def test_run_subprocess_shell_success(self):
        """
        Tests successful execution with output
        """
        code, out = run_subprocess(
            "echo '123   ' && echo '   456'",
            timeout=999999999,
            shell=True,
            stdin=None,
        )
        self.assertEqual(code, 0)
        self.assertEqual(out, "123   \n   456\n")

    def test_run_subprocess_shell_wrong_exec(self):
        """
        Tests unsuccessful execution with output
        """
        code, out = run_subprocess(
            "echo '123   ' && not_a_command",
            timeout=999999999,
            shell=True,
            stdin=None,
        )
        self.assertNotEqual(code, 0)
        self.assertTrue(out.startswith("123   \n"))

    def test_run_subprocess_timeout(self):
        """
        Tests execution with timeout
        """
        with self.assertRaises(TimeoutExpired) as e:
            run_subprocess(
                "echo '123   ' && sleep 100 && echo '   456'",
                timeout=1,
                shell=True,
                stdin=None,
            )
        raw_out: str = e.exception.output
        self.assertTrue("Original output was: " in raw_out)
        pos: int = raw_out.index("Original output was: ")
        out: str = raw_out[(pos + len("Original output was: ")):]
        self.assertEqual(out, "123   \n")
