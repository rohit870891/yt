import time
import pymongo, os
from config import DB_URI, DB_NAME
from bot import Bot
import motor.motor_asyncio
from config import ADMINS, DB_URL, DB_NAME

dbclient = motor.motor_asyncio.AsyncIOMotorClient(DB_URL)
database = dbclient[DB_NAME]

user_data = database['users']
admin_data= database['admins']
link_data = database['links']
collection = database['premium-users']

default_verify = {
    'is_verified': False,
    'verified_time': 0,
    'verify_token': "",
    'link': ""
}

def new_user(id):
    return {
        '_id': id,
        'verify_status': {
            'is_verified': False,
            'verified_time': "",
            'verify_token': "",
            'link': ""
        }
    }

#links
async def new_link(hash: str):
    return {
        'clicks' : 0,
        'hash': hash
    }

async def gen_new_count(hash: str):
    data = await new_link(hash)
    await link_data.insert_one(data)
    return

async def present_hash(hash:str):
    found = await(link_data.find_one({"hash" : hash}))
    return bool(found)

async def inc_count(hash: str):
    data = await link_data.find_one({'hash': hash})
    clicks = data.get('clicks')
    await link_data.update_one({'hash': hash}, {'$set': {'clicks': clicks+1}})
    return

async def get_clicks(hash: str):
    data = await link_data.find_one({'hash': hash})
    clicks = data.get('clicks')
    return clicks


#users
async def present_user(user_id: int):
    found = await user_data.find_one({'_id': user_id})
    return bool(found)

async def add_user(user_id: int):
    user = new_user(user_id)
    await user_data.insert_one(user)
    return

async def db_verify_status(user_id):
    user = await user_data.find_one({'_id': user_id})
    if user:
        return user.get('verify_status', default_verify)
    return default_verify

async def db_update_verify_status(user_id, verify):
    await user_data.update_one({'_id': user_id}, {'$set': {'verify_status': verify}})

async def full_userbase():
    user_docs = user_data.find()
    user_ids = [doc['_id'] async for doc in user_docs]
    return user_ids

async def del_user(user_id: int):
    await user_data.delete_one({'_id': user_id})
    return

#admins

async def present_admin(user_id: int):
    found = await admin_data.find_one({'_id': user_id})
    return bool(found)


async def add_admin(user_id: int):
    user = new_user(user_id)
    await admin_data.insert_one(user)
    ADMINS.append(int(user_id))
    return

async def del_admin(user_id: int):
    await admin_data.delete_one({'_id': user_id})
    ADMINS.remove(int(user_id))
    return

async def full_adminbase():
    user_docs = admin_data.find()
    user_ids = [int(doc['_id']) async for doc in user_docs]
    return user_ids

async def add_premium(user_id, time_limit_months):
    expiration_timestamp = int(time.time()) + time_limit_months * 30 * 24 * 60 * 60
    premium_data = {
        "user_id": user_id,
        "expiration_timestamp": expiration_timestamp,
    }
    collection.insert_one(premium_data)
    dbclient.close()

async def remove_premium(user_id):
    result = collection.delete_one({"user_id": user_id})
    dbclient.close()

async def remove_expired_users():
    current_timestamp = int(time.time())

    # Find and delete expired users
    expired_users = collection.find({"expiration_timestamp": {"$lte": current_timestamp}})

    for expired_user in expired_users:
        user_id = expired_user["user_id"]
        collection.delete_one({"user_id": user_id})

    dbclient.close()

async def list_premium_users():

    premium_users = collection.find({})

    premium_user_list = []

    for user in premium_users:
        user_id = user["user_id"]
        user_info = Bot.get_users(user_id)
        username = user_info.username if user_info.username else user_info.first_name
        expiration_timestamp = user["expiration_timestamp"]
        premium_user_list.append(f"{user_id} - {username} - Expiration Timestamp: {expiration_timestamp}")

    return premium_user_list
