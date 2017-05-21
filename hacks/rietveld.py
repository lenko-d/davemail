import email
import os
import re

import notmuch

def valid_message_id(message_id):
  return message_id.endswith("@codereview1.adblockplus.org")

def find_references(message_id, subject):
  # Whilst finding the issue part of the subject we also take care to avoid
  # matching quote characters, since we're not escaping the search query later!
  match = re.search(r"\(issue \d+ by [^\)\"]+\)$", subject)
  if match:
    db = notmuch.Database()
    query = db.create_query("subject:\"" + match.group(0) + "\"")
    if query.count_messages() > 0:
      query.set_sort(notmuch.Query.SORT.OLDEST_FIRST)
      message_ids = [m.get_message_id()
                     for m in query.search_messages()
                     if valid_message_id(m.get_message_id())]
      index = message_ids.index(message_id)
      try:
        return message_ids[:index]
      except:
        pass
  return []

def atime_mtime(path):
  stat = os.stat(path)
  return (stat.st_atime, stat.st_mtime)

# https://www.jwz.org/doc/threading.html
def fix_threading(message):
  if message.get("In-Reply-To") and message.get("References"):
    return False
  references = ["<" + id + ">"
                for id in find_references(message.get("Message-Id").strip("<>"),
                                          message["Subject"])]
  if not references:
    return False
  # We don't want nested threading, so we discard most of the references.
  message["In-Reply-To"] = references[0]
  message["References"] = references[0]
  return True

def fix_wrapping(message):
  # FIXME - Figure out a proper algorithm for this when I have more time!
  return False

def fix_rietveld_email(db, path):
  with open(path, "r+") as f:
    message = email.message_from_file(f)
    if valid_message_id(message.get("Message-Id").strip("<>")):
      if fix_threading(message) or fix_wrapping(message):
        times = atime_mtime(path)
        f.seek(0)
        f.write(message.as_string())
        f.truncate()
        # We store the Modify time before making changes and restore it here.
        # That's important since mbsync uses that for the internaldate property.
        # (The access time doesn't actually matter to us, but utime requires
        #  that we specify that too.)
        os.utime(path, times)
        # Also store the notmuch tags, since we're going to lose those.
        tags = db.find_message_by_filename(path).get_tags()
        # Notmuch won't notice the change unless we remove it from the database
        # and add it back again! FIXME - mbsync won't notice the change at all!
        db.remove_message(path)
        notmuch_message = db.add_message(path)[0]
        for tag in tags:
          notmuch_message.add_tag(tag, True)

def fix_rietveld_emails(query_string):
  with notmuch.Database(mode=notmuch.Database.MODE.READ_WRITE) as db:
    query = db.create_query(query_string)
    for message in query.search_messages():
      fix_rietveld_email(db, message.get_filename())
