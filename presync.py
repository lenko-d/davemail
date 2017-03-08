import os
from subprocess import call

import notmuch

with open(os.devnull, "w") as devnull:
  call(["emacsclient", "-e", "(run-hooks 'notmuch-presync-hook)"],
       stdout=devnull)

db = notmuch.Database()
maildir_path = os.path.realpath(os.path.expanduser("~/Maildir"))

def move_messages(query_string, destination):
  query = db.create_query(query_string)
  for message in query.search_messages():
    old_filename = message.get_filename()
    path, filename = os.path.split(old_filename)
    cur_new = path.split(os.sep)[-1]
    new_filename = os.path.join(maildir_path, destination, cur_new, filename)
    os.rename(old_filename, new_filename)

# Archive any messages in INBOX which no longer have the inbox tag
move_messages("NOT tag:inbox AND folder:INBOX", "Archive")

# Move any junk to the Spam / Trash folders
move_messages("tag:spam AND NOT folder:Spam", "Spam")
move_messages("tag:deleted AND NOT folder:Trash", "Trash")
