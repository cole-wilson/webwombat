from PIL import Image
from io import BytesIO
from webwombat.transformers import _bytestomessage

def main(message):
    if message.messagetype == "response" and 'content-type' in message:
        form = False
        if message['content-type'].startswith("image/png"):
            form = "PNG"
        elif message['content-type'].startswith("image/jpeg"):
            form = "JPEG"

        if form:
            oformat = message['content-type'].split('/')[1][0:4]
            # message.read_headers()
            content_length = message['content-length']
            data = message.sourcefile.read(int(content_length))
            img = Image.open(BytesIO(data))
            img = img.rotate(180)
            newdata = BytesIO()
            img.save(newdata, format=form)
            return _bytestomessage(newdata.getvalue(), code=message.status, reason=message.reason, headers=message.headers)
    return message
