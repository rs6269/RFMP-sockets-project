"""
This is a standalone test script for the command_handler.py.
It will run each command with sample inputs and prints the result,
so the functions can be checked without needing sockets or a server.
Also tested command names which didnt exist, to check if the else: branch was correctly executed.
"""

from command_handler import (
    execute_prompt_command, open_read, open_write, write_data, close_file,
)  # bring in the functions from command_handler.py so they can be tested here

print("=== mkdir / cd / dir / pwd ===")  # just a label printed to separate this group of tests
print(execute_prompt_command("mkdir", "testfolder"))  # should create a folder called testfolder
print(execute_prompt_command("cd", "testfolder"))  # should move into that folder
print(execute_prompt_command("pwd", ""))  # should show the current folder path
print(execute_prompt_command("dir", ""))  # should list what's inside the current folder

print("\n=== ren / copy / move ===")  # label for the next group of tests
open("sample.txt", "w").close()  # create an empty file to test ren/copy/move on
print(execute_prompt_command("ren", "sample.txt renamed.txt"))  # should rename sample.txt
print(execute_prompt_command("copy", "renamed.txt copy_of_renamed.txt"))  # should copy the renamed file
print(execute_prompt_command("move", "copy_of_renamed.txt moved.txt"))  # should move/rename the copy

print("\n=== del / rmdir ===")  # label for the next group of tests
print(execute_prompt_command("del", "renamed.txt"))  # should delete renamed.txt
print(execute_prompt_command("del", "moved.txt"))  # should delete moved.txt
print(execute_prompt_command("cd", ".."))  # move back up one folder before removing testfolder
print(execute_prompt_command("rmdir", "testfolder"))  # should delete the now-empty testfolder

print("\n=== error cases (should return EE) ===")  # label for the error tests
print(execute_prompt_command("rmdir", "doesNotExist"))  # folder doesn't exist, should return E02
print(execute_prompt_command("mkdir", "."))  # "." already exists, should return E03
print(execute_prompt_command("blah", "something"))  # not a real command, should return E01
print(execute_prompt_command("ren", "onlyonename"))  # missing the second name, should return E04

print("\n=== openRead / openWrite / write_data / close_file ===")  # label for the file-handling tests
print(open_read("does_not_exist.txt"))  # file doesn't exist, should return E02
status, handle = open_write("demo.txt")  # open a new file for writing, get back status and the file handle
if status == "SC":  # only continue if the file actually opened successfully
    print(write_data(handle, "Hello from the DP packet simulation\n"))  # write some text into it
    print(close_file(handle))  # close the file once done writing
print(open_read("demo.txt"))  # read it back to confirm the text was actually saved

import os  # needed here just for the cleanup step below
if os.path.exists("demo.txt"):  # check if the test file still exists
    os.remove("demo.txt")  # delete it so repeated test runs start clean