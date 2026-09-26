"""
This file will handle the server-side file/folder commands like mkdir, cd, rmdir, del, ren, and etc) and reading/writing files.
It has no socket code - the server script will import this file and call these functions whenever a
command packet arrives from the client.
This is basically a skeleton structure with the main functions
"""

import os
import subprocess


def execute_prompt_command(command, args):
    """This will run a folder/file command like mkdir, cd, rmdir, del, ren."""
    pass


def open_read(filename):
    """This will open a file and returns its contents."""
    pass


def open_write(filename):
    """Will open a file for writing and returns the file handle."""
    pass


def write_data(file_handle, text):
    """will writes incoming data to an already open file."""
    pass


def close_file(file_handle):
    """Closes a file that was opened for writing."""
    pass