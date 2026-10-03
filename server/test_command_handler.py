"""
This is a standalone test script for the command_handler.py.
It will run each command with sample inputs and prints the result,
so the functions can be checked without needing sockets or a server.
Also tested command names which didnt exist, to check if the else: branch was correctly executed.
"""

from command_handler import (
    execute_prompt_command, open_read, open_write, write_data, close_file,
)

print("=== mkdir / cd / dir / pwd ===")
print(execute_prompt_command("mkdir", "testfolder"))
print(execute_prompt_command("cd", "testfolder"))
print(execute_prompt_command("pwd", ""))
print(execute_prompt_command("dir", ""))

print("\n=== ren / copy / move ===")
open("sample.txt", "w").close()
print(execute_prompt_command("ren", "sample.txt renamed.txt"))
print(execute_prompt_command("copy", "renamed.txt copy_of_renamed.txt"))
print(execute_prompt_command("move", "copy_of_renamed.txt moved.txt"))

print("\n=== del / rmdir ===")
print(execute_prompt_command("del", "renamed.txt"))
print(execute_prompt_command("del", "moved.txt"))
print(execute_prompt_command("cd", ".."))
print(execute_prompt_command("rmdir", "testfolder"))

print("\n=== error cases (should return EE) ===")
print(execute_prompt_command("rmdir", "doesNotExist"))
print(execute_prompt_command("mkdir", "."))
print(execute_prompt_command("blah", "something"))
print(execute_prompt_command("ren", "onlyonename"))

print("\n=== openRead / openWrite / write_data / close_file ===")
print(open_read("does_not_exist.txt"))
status, handle = open_write("demo.txt")
if status == "SC":
    print(write_data(handle, "Hello from the DP packet simulation\n"))
    print(close_file(handle))
print(open_read("demo.txt"))

import os
if os.path.exists("demo.txt"):
    os.remove("demo.txt")