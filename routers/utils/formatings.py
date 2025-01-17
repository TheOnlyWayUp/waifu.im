import os
from werkzeug.datastructures import MultiDict
from fastapi.encoders import jsonable_encoder

class Image:
    def __init__(self,filename,extension,dominant_color=None):
        self.filename=filename
        self.extension=extension
        self.fullfilename=filename+extension
        self.dominant_color=dominant_color

class Tags:
    def __init__(self,tag_id,name,is_nsfw,description):
        self.tag_id=tag_id
        self.name=name
        self.is_nsfw=bool(is_nsfw)
        self.description=description
    def __hash__(self):
        return self.tag_id
    def __eq__(self,o):
        return o==self.__hash__()


def db_to_json(images):
    tagmapping=[]
    for im in images:
        im=dict(im)
        im['id']=int(im['id'])
        tagmapping.append((Tags(im.pop('id'),im.pop('name'),im.pop('is_nsfw'),im.pop('description')),im))
    tagmapping=MultiDict(tagmapping)
    default_tags=['ero','all']
    tags_=[]
    for tag,image in tagmapping.items():
        tag_images=tagmapping.getlist(tag.tag_id)
        tag_images=[dict(t,**{'url':'https://cdn.waifu.im/'+t['file']+t['extension']}) for t in tag_images]
        tags_.append(dict(vars(tag),**{'images':tag_images}))
    return jsonable_encoder(tags_)

def format_to_image(string):
    if not string:
        return []
    images=[x for x in string.split(",")]
    try:
        return [Image(os.path.splitext(x)[0],os.path.splitext(x)[1]) for x in images]
    except:
        raise ValueError



async def myendpoints(app,over18=None):
    rt=await app.state.pool.fetch("SELECT * FROM Tags")
    if over18 is None:
        return {"sfw":[tag['name'] for tag in rt if not tag['is_nsfw'] ],"nsfw":[tag['name'] for tag in rt if tag['is_nsfw']],'example':'https://api.waifu.im/sfw/waifu/'}
    elif over18:
        return [tag['name'] for tag in rt if tag['is_nsfw']]
    else:
        return [tag['name'] for tag in rt if not tag['is_nsfw']]

async def myendpoints_info(app,over18=None):
    rt= await app.state.pool.fetch("SELECT * FROM Tags")
    if over18 is None:
        return {"sfw":[tag for tag in rt if not tag['is_nsfw']],
                "nsfw":[tag for tag in rt if tag['is_nsfw']],'example':'https://api.waifu.im/sfw/waifu/'}
    elif over18:
        return [tag for tag in rt if tag['is_nsfw']]
    else:
        return [tag for tag in rt if not tag['is_nsfw']]


"""Determine if an image is already or not in the User gallery for the toggle url param"""
async def wich_action(image,insert,delete,user_id,conn):
    if not image:
        return
    for im in image:
        rt=await conn.fetchrow("SELECT image FROM FavImages WHERE user_id=$1 and image=$2",user_id,im.filename)
        if rt:
            delete.append(im)
        else:
            insert.append(im)
        
        

"""Utils to format into apropriate sql query"""
def create_query(user_id,insert=None,delete=None):
    if insert:
        args=[(user_id,im.filename) for im in insert]
        return "INSERT INTO FavImages(user_id,image) VALUES($1,$2) ON CONFLICT (user_id,image) DO NOTHING",args
    elif delete:
        args=[(user_id,im.filename) for im in delete]
        return "DELETE FROM FavImages WHERE user_id=$1 and image=$2",args