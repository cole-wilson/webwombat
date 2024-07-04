import os
import time
import sqlitedict

path = os.path.abspath(os.path.expanduser("~") + os.sep + ".cache" + os.sep + "wombat" + os.sep + "sitecache.db")
print(path)
db = sqlitedict.SqliteDict(path)
print(list(db.keys()))

def main(message):
    # key = str(message)

    # if message.messagetype == "request" and key in db:
    #     birthday, response = db[key]
    #     if time.time() - birthday > (3600 * 24): # day
    #         del db[key]
    #         return message # bypass cache
    #     else:
    #         return response
    # elif message.messagetype == "response":
    #     db[str(message.requesting_message)] = message
    #     db.commit()
    #     return message
    # else:
        return message
