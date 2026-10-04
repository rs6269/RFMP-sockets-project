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


def execute_prompt_command(command, args):
    """This will run a folder/file command like mkdir, cd, rmdir, del, ren."""
    try:
        if command == "mkdir": # check if the client asked for mkdir
            os.mkdir(args) # args is the folder name, this creates it
            return ("SC", "Directory '%s' created" % args) # SC means success, send the name back

        elif command == "cd": # check if the client asked to change folder
            os.chdir(args)  # args is the folder to move into
            return ("SC", "Changed directory to '%s'" % os.getcwd()) # getcwd shows where we are now

        elif command == "rmdir": # check if the client asked to remove a folder
            os.rmdir(args) # args is the folder name, this deletes it (only if empty)
            return ("SC", "Directory '%s' removed" % args) # send back a success message that includes the folder name that was deleted

        elif command == "del": # check if the client asked to delete a file
            os.remove(args)  # args is the file name, this deletes it
            return ("SC", "File '%s' deleted" % args) # send back a success message that includes the name of the file that was deleted

        elif command == "ren": # check if the client asked to rename something
            old_name, new_name = args.split(" ", 1) # args is "oldname newname", split cuts it into two words
            os.rename(old_name, new_name) # this does the actual renaming
            return ("SC", "Renamed '%s' to '%s'" % (old_name, new_name)) # send back a success message showing both the old name and the new name
            
        elif command == "dir": # check if the client asked to list files
            items = os.listdir(".") # "." means the current folder, this lists what's inside it
            return ("SC", "\n".join(items)) # join puts each item on its own line in one text block

        elif command == "pwd": # check if the client asked for the current folder
            return ("SC", os.getcwd()) # getcwd returns the folder path we're currently in

        elif command == "move": # check if the client asked to move a file
            old_name, new_name = args.split(" ", 1) # split "source destination" into two names
            os.rename(old_name, new_name) # rename also works for moving a file to a new path
            return ("SC", "File moved") # send back a simple success message, no file name included this time

        elif command == "type": # check if the client asked to see what's inside a file
            f = open(args, "rt", encoding="utf-8") # open the file in read mode
            contents = f.read() # read everything in the file into one piece of text
            f.close() # close the file once we're done reading it
            return ("SC", contents) # send the file's text back

        elif command == "copy": # check if the client asked to copy a file
            src_name, dst_name = args.split(" ", 1) # split "source destination" into two names
            f = open(src_name, "rt", encoding="utf-8") # open the original file to read it
            contents = f.read() # read all of its text
            f.close() # close the original file
            f = open(dst_name, "wt", encoding="utf-8") # open a new file in write mode
            f.write(contents) # write the copied text into the new file
            f.close() # close the new file
            return ("SC", "File copied") # send back a simple success message, no file name included this time

        else: # this runs if command didn't match any of the ones above
            return ("EE", "E01", "Unknown command: %s" % command) # EE means error, E01 is the unknown-command code

    except FileNotFoundError: # this runs only if the file/folder above wasn't found
        return ("EE", "E02", "Not found: %s" % args) # E02 is the not-found code
    
    except FileExistsError: # this runs only if the file/folder above already exists
        return ("EE", "E03", "Already exists: %s" % args) # E03 is the already-exists code
    
    except: # this catches any other kind of failure not already handled above
        return ("EE", "E04", "Command failed: %s" % command) # E04 is the general error code

def open_read(filename):
    """This will open a file and returns its contents."""
    try:  # attempt to open and read the file
        f = open(filename, "rt", encoding="utf-8")  # open the file in read mode
        contents = f.read()  # read the whole file into one piece of text
        f.close()  # close the file now that we have its contents
        return ("SC", contents)  # send the text back as a success result
    except FileNotFoundError:  # runs if the file doesn't exist
        return ("EE", "E02", "File not found: %s" % filename)
    except OSError as e:  # runs for any other file problem, e holds the real error message
        return ("EE", "E04", str(e))  # str(e) turns that error into readable text

def open_write(filename):
    """Will open a file for writing and returns the file handle."""
    try:  # attempt to open the file for writing
        file_handle = open(filename, "wt", encoding="utf-8")  # open in write mode, creates the file if missing
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