"""
Standalone test script for Raihan_command_handler.py.
Runs each command with sample inputs and prints the result, so the functions
can be checked without needing sockets or a server.
cwd is just a text path that is passed in and handed back, like the server does for each client.
"""

import os  # needed to find the starting folder and to clean up the test file at the end
from Raihan_command_handler import (
    execute_prompt_command, open_read, open_write, write_data, close_file,
)  # bring in the functions from Raihan_command_handler.py so they can be tested here

cwd = os.getcwd()  # start in the current folder, like a new client would

print("=== mkdir / cd / dir / pwd ===")  # just a label printed to separate this group of tests
result, cwd = execute_prompt_command("mkdir", "testfolder", cwd); print(result)  # should create testfolder
result, cwd = execute_prompt_command("cd", "testfolder", cwd); print(result)     # should move this "client" into it
result, cwd = execute_prompt_command("pwd", "", cwd); print(result)              # should show the new folder
result, cwd = execute_prompt_command("dir", "", cwd); print(result)              # should list what's inside

print("\n=== ren / copy / move ===")  # label for the next group of tests
open(os.path.join(cwd, "sample.txt"), "w").close()  # create the empty file INSIDE testfolder (cwd), not the process folder
result, cwd = execute_prompt_command("ren", "sample.txt renamed.txt", cwd); print(result)  # should rename sample.txt
result, cwd = execute_prompt_command("copy", "renamed.txt copy_of_renamed.txt", cwd); print(result)  # should copy the renamed file
result, cwd = execute_prompt_command("move", "copy_of_renamed.txt moved.txt", cwd); print(result)  # should move/rename the copy

print("\n=== del / rmdir ===")  # label for the next group of tests
result, cwd = execute_prompt_command("del", "renamed.txt", cwd); print(result)  # should delete renamed.txt
result, cwd = execute_prompt_command("del", "moved.txt", cwd); print(result)    # should delete moved.txt
result, cwd = execute_prompt_command("cd", "..", cwd); print(result)             # go back up before removing testfolder
result, cwd = execute_prompt_command("rmdir", "testfolder", cwd); print(result)  # should delete the now-empty testfolder

print("\n=== error cases (should return EE) ===")  # label for the error tests
result, cwd = execute_prompt_command("rmdir", "doesNotExist", cwd); print(result)  # folder doesn't exist, should return E02
result, cwd = execute_prompt_command("mkdir", ".", cwd); print(result)             # "." already exists, should return E03
result, cwd = execute_prompt_command("blah", "something", cwd); print(result)      # not a real command, should return E01
result, cwd = execute_prompt_command("ren", "onlyonename", cwd); print(result)     # missing the second name, should return E04

print("\n=== openRead / openWrite / write_data / close_file ===")  # label for the file-handling tests
print(open_read("does_not_exist.txt", cwd))  # file doesn't exist, should return E02
status, handle = open_write("demo.txt", cwd)  # open a new file for writing, get back status and the file handle
if status == "SC":  # only continue if the file actually opened successfully
    print(write_data(handle, "Hello from the DP packet simulation\n"))  # write some text into it
    print(close_file(handle))  # close the file once done writing
print(open_read("demo.txt", cwd))  # read it back to confirm the text was actually saved

demo_path = os.path.join(cwd, "demo.txt")  # build the full path to the test file, so cleanup looks in the right folder
if os.path.exists(demo_path):  # check if the test file still exists
    os.remove(demo_path)  # delete it so repeated test runs start clean