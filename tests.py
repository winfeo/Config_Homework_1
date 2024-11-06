import unittest
from unittest.mock import patch, MagicMock
from shell_emulator import ShellEmulator
import tkinter as tk

class TestShellEmulator(unittest.TestCase):
    def setUp(self):
        root = tk.Tk()
        self.shell = ShellEmulator(root)

    @patch('shell_emulator.ShellEmulator.ls')
    def test_ls_command(self, mock_ls):
        # Test ls without arguments
        self.shell.execute_command(command="ls")
        mock_ls.assert_called_once_with([])

        # Test ls with "-l" flag
        self.shell.execute_command(command="ls -l")
        mock_ls.assert_called_with(["-l"])

        # Test ls with "-h" flag
        self.shell.execute_command(command="ls -h")
        mock_ls.assert_called_with(["-h"])

    @patch('shell_emulator.ShellEmulator.cd')
    def test_cd_command(self, mock_cd):
        # Test cd without arguments (should go to root)
        self.shell.execute_command(command="cd")
        mock_cd.assert_called_once_with([])

        # Test cd with directory argument
        self.shell.execute_command(command="cd folder")
        mock_cd.assert_called_with(["folder"])

        # Test cd with ".." argument (move up a directory)
        self.shell.execute_command(command="cd ..")
        mock_cd.assert_called_with([".."])

    @patch('shell_emulator.ShellEmulator.echo')
    def test_echo_command(self, mock_echo):
        # Test echo with simple text
        self.shell.execute_command(command="echo Hello")
        mock_echo.assert_called_once_with(["Hello"])

        # Test echo with multiple words
        self.shell.execute_command(command="echo Hello World!")
        mock_echo.assert_called_with(["Hello", "World!"])

        # Test echo with no text
        self.shell.execute_command(command="echo")
        mock_echo.assert_called_with([])

    @patch('shell_emulator.ShellEmulator.mv')
    def test_mv_command(self, mock_mv):
        # Test mv with source and destination
        self.shell.execute_command(command="mv file1.txt folder/")
        mock_mv.assert_called_once_with(["file1.txt", "folder/"])

        # Test mv with multiple sources and a single destination
        self.shell.execute_command(command="mv file1.txt file2.txt folder/")
        mock_mv.assert_called_with(["file1.txt", "file2.txt", "folder/"])

        # Test mv with missing destination
        self.shell.execute_command(command="mv file1.txt")
        mock_mv.assert_called_with(["file1.txt"])

    @patch('shell_emulator.ShellEmulator.find')
    def test_find_command(self, mock_find):
        # Test find with no arguments
        self.shell.execute_command(command="find")
        mock_find.assert_called_once_with([])

        # Test find with directory argument and name pattern
        self.shell.execute_command(command="find /folder -name *.txt")
        mock_find.assert_called_with(["/folder", "-name", "*.txt"])

        # Test find with size limit
        self.shell.execute_command(command="find -size 1M")
        mock_find.assert_called_with(["-size", "1M"])

if __name__ == '__main__':
    unittest.main()
