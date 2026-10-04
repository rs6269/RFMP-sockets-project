"""
This file will handle the server-side file/folder commands like mkdir, cd, rmdir, del, ren, and etc) and reading/writing files.
It has no socket code - the server script will import this file and call these functions whenever a
command packet arrives from the client.
This is basically a skeleton structure with the main functions
"""
# Error code table (Maximum of 4 error codes):
# E01: Issue when unknown or unsupported command is passed
# E02: When unable to locate File or directory 
# E03: When file or directory with that name already exists
# E04: Any other command failure

import os


def execute_prompt_command(command, args, cwd):
    """This will run a folder/file command like mkdir, cd, rmdir, del, ren.
    cwd is this client's own current folder (just a text path), not the
    server's real folder, so one client's cd never affects another client.
    Returns (result, new_cwd) - new_cwd only changes when cd succeeds."""
    try:
        if command == "mkdir": # check if the client asked for mkdir
            path = os.path.join(cwd, args) # build the full path from this client's folder + the given name
            os.mkdir(path) # args is the folder name, this creates it
            return ("SC", "Directory '%s' created" % args), cwd # SC means success, send the name back, cwd stays the same

        elif command == "cd": # check if the client asked to change folder
            new_path = os.path.normpath(os.path.join(cwd, args)) # combine and clean up the path (handles "..", etc.)
            if not os.path.isdir(new_path): # check the folder actually exists before "moving" into it
                return ("EE", "E02", "Not found: %s" % args), cwd # folder doesn't exist, keep the old cwd
            return ("SC", "Changed directory to '%s'" % new_path), new_path # send back the new folder, and hand back the new cwd for this client only

        elif command == "rmdir": # check if the client asked to remove a folder
            path = os.path.join(cwd, args) # build the full path inside this client's current folder
            os.rmdir(path) # args is the folder name, this deletes it (only if empty)
            return ("SC", "Directory '%s' removed" % args), cwd # send back a success message that includes the folder name that was deleted

        elif command == "del": # check if the client asked to delete a file
            path = os.path.join(cwd, args) # build the full path inside this client's current folder
            os.remove(path)  # args is the file name, this deletes it
            return ("SC", "File '%s' deleted" % args), cwd # send back a success message that includes the name of the file that was deleted

        elif command == "ren": # check if the client asked to rename something
            old_name, new_name = args.split(" ", 1) # args is "oldname newname", split cuts it into two words
            old_path = os.path.join(cwd, old_name) # build the full path to the old name
            new_path = os.path.join(cwd, new_name) # build the full path to the new name
            os.rename(old_path, new_path) # this does the actual renaming
            return ("SC", "Renamed '%s' to '%s'" % (old_name, new_name)), cwd # send back a success message showing both the old name and the new name
            
        elif command == "dir": # check if the client asked to list files
            items = os.listdir(cwd) # list what's inside THIS client's current folder, not the server's own folder
            return ("SC", "\n".join(items)), cwd # join puts each item on its own line in one text block

        elif command == "pwd": # check if the client asked for the current folder
            return ("SC", cwd), cwd # just report this client's own folder, not the server process's real one

        elif command == "move": # check if the client asked to move a file
            old_name, new_name = args.split(" ", 1) # split "source destination" into two names
            old_path = os.path.join(cwd, old_name) # build the full path to the source
            new_path = os.path.join(cwd, new_name) # build the full path to the destination
            os.rename(old_path, new_path) # rename also works for moving a file to a new path
            return ("SC", "File moved"), cwd # send back a simple success message, no file name included this time

        elif command == "type": # check if the client asked to see what's inside a file
            path = os.path.join(cwd, args) # build the full path inside this client's current folder
            f = open(path, "rt", encoding="utf-8") # open the file in read mode
            contents = f.read() # read everything in the file into one piece of text
            f.close() # close the file once we're done reading it
            return ("SC", contents), cwd # send the file's text back

        elif command == "copy": # check if the client asked to copy a file
            src_name, dst_name = args.split(" ", 1) # split "source destination" into two names
            src_path = os.path.join(cwd, src_name) # build the full path to the source file
            dst_path = os.path.join(cwd, dst_name) # build the full path to the destination file
            f = open(src_path, "rt", encoding="utf-8") # open the original file to read it
            contents = f.read() # read all of its text
            f.close() # close the original file
            f = open(dst_path, "wt", encoding="utf-8") # open a new file in write mode
            f.write(contents) # write the copied text into the new file
            f.close() # close the new file
            return ("SC", "File copied"), cwd # send back a simple success message, no file name included this time

        else: # this runs if command didn't match any of the ones above
            return ("EE", "E01", "Unknown command: %s" % command), cwd # EE means error, E01 is the unknown-command code

    except FileNotFoundError: # this runs only if the file/folder above wasn't found
        return ("EE", "E02", "Not found: %s" % args), cwd # E02 is the not-found code
    
    except FileExistsError: # this runs only if the file/folder above already exists
        return ("EE", "E03", "Already exists: %s" % args), cwd # E03 is the already-exists code
    
    except UnicodeDecodeError: # this runs if the file being read isn't plain text (e.g. a binary file)
        return ("EE", "E04", "'%s' is not a text file" % args), cwd # tell the client the file couldn't be read as text

    except: # this catches any other kind of failure not already handled above
        return ("EE", "E04", "Command failed: %s" % command), cwd # E04 is the general error code

def open_read(filename, cwd):
    """This will open a file and returns its contents.
    cwd is this client's own current folder, so the file is looked up
    relative to wherever this client has "cd"-ed to."""
    try:  # attempt to open and read the file
        path = os.path.join(cwd, filename) # build the full path inside this client's current folder
        f = open(path, "rt", encoding="utf-8")  # open the file in read mode
        contents = f.read()  # read the whole file into one piece of text
        f.close()  # close the file now that we have its contents
        return ("SC", contents)  # send the text back as a success result
    except FileNotFoundError:  # runs if the file doesn't exist
        return ("EE", "E02", "File not found: %s" % filename)
    except UnicodeDecodeError: # runs if the file isn't plain text (e.g. a binary file)
        return ("EE", "E04", "'%s' is not a text file" % filename) # tell the client clearly instead of crashing
    except OSError as e:  # runs for any other file problem, e holds the real error message
        return ("EE", "E04", str(e))  # str(e) turns that error into readable text

def open_write(filename, cwd):
    """Will open a file for writing and returns the file handle.
    cwd is this client's own current folder, so the file is created
    relative to wherever this client has "cd"-ed to."""
    try:  # attempt to open the file for writing
        path = os.path.join(cwd, filename) # build the full path inside this client's current folder
        file_handle = open(path, "wt", encoding="utf-8")  # open in write mode, creates the file if missing
        return ("SC", file_handle)  # send back the open file so more data can be written to it later
    except OSError as e:  # runs if the file couldn't be opened
        return ("EE", "E04", str(e)) # send back an error, str(e) turns Python's own error into readable text

def write_data(file_handle, text):
    """will writes incoming data to an already open file."""
    try:  # attempt to write into the file
        file_handle.write(text)  # add the given text into the already-open file
        return ("SC", "Data written") # send back a success message confirming the text was added to the file
    except OSError as e:  # runs if writing fails
        return ("EE", "E04", str(e))# send back an error, str(e) turns Python's own error into readable text

def close_file(file_handle):
    """Closes a file that was opened for writing."""
    try:  # attempt to close the file
        file_handle.close()  # this saves and closes the file
        return ("SC", "File closed") # send back a success message confirming the file was closed properly
    except OSError as e:  # runs if closing fails
        return ("EE", "E04", str(e)) # send back an error, str(e) turns Python's own error into readable text