"""
This file will handle the server-side file/folder commands like mkdir, cd, rmdir, del, ren, and etc) and reading/writing files.
It has no socket code - the server script will import this file and call these functions whenever a
command packet arrives from the client.
This is basically a skeleton structure with the main functions
"""

import os


def execute_prompt_command(command, args):
    """This will run a folder/file command like mkdir, cd, rmdir, del, ren."""
    try:
        if command == "mkdir":
            os.mkdir(args)
            return ("SC", "Directory '%s' created" % args)

        elif command == "cd":
            os.chdir(args)
            return ("SC", "Changed directory to '%s'" % os.getcwd())

        elif command == "rmdir":
            os.rmdir(args)
            return ("SC", "Directory '%s' removed" % args)

        elif command == "del":
            os.remove(args)
            return ("SC", "File '%s' deleted" % args)

        elif command == "ren":
            old_name, new_name = args.split(" ", 1)
            os.rename(old_name, new_name)
            return ("SC", "Renamed '%s' to '%s'" % (old_name, new_name))
            
        elif command == "dir":
            items = os.listdir(".")
            return ("SC", "\n".join(items))

        elif command == "pwd":
            return ("SC", os.getcwd())

        elif command == "move":
            old_name, new_name = args.split(" ", 1)
            os.rename(old_name, new_name)
            return ("SC", "File moved")

        elif command == "type":
            f = open(args, "rt", encoding="utf-8")
            contents = f.read()
            f.close()
            return ("SC", contents)

        elif command == "copy":
            src_name, dst_name = args.split(" ", 1)
            f = open(src_name, "rt", encoding="utf-8")
            contents = f.read()
            f.close()
            f = open(dst_name, "wt", encoding="utf-8")
            f.write(contents)
            f.close()
            return ("SC", "File copied")

        else:
            return ("EE", "E01", "Unknown command: %s" % command)

    except FileNotFoundError:
        return ("EE", "E02", "Not found: %s" % args)
    except OSError as e:
        return ("EE", "E04", str(e))


def open_read(filename):
    """This will open a file and returns its contents."""
    try:
        f = open(filename, "rt", encoding="utf-8")
        contents = f.read()
        f.close()
        return ("SC", contents)
    except FileNotFoundError:
        return ("EE", "E02", "File not found: %s" % filename)
    except OSError as e:
        return ("EE", "E04", str(e))


def open_write(filename):
    """Will open a file for writing and returns the file handle."""
    try:
        file_handle = open(filename, "wt", encoding="utf-8")
        return ("SC", file_handle)
    except OSError as e:
        return ("EE", "E04", str(e))


def write_data(file_handle, text):
    """will writes incoming data to an already open file."""
    try:
        file_handle.write(text)
        return ("SC", "Data written")
    except OSError as e:
        return ("EE", "E04", str(e))


def close_file(file_handle):
    """Closes a file that was opened for writing."""
    try:
        file_handle.close()
        return ("SC", "File closed")
    except OSError as e:
        return ("EE", "E04", str(e))