from pymongo import MongoClient, ReturnDocument
from datetime import datetime, timezone


class MongoDB:
    def __init__(self, uri, db_name):
        self.client = MongoClient(uri)
        self.db = self.client[db_name]
        self.user_data = self.db["user_data"]
        self.invite_links = self.db["invite_links"]
        self.fsub_progress = self.db["fsub_progress"]
        self.fsub_requests = self.db["fsub_requests"]

    async def save_invite_link(self, channel_id, invite_link, is_request=False):
        self.invite_links.update_one(
            {"channel_id": channel_id},
            {"$set": {
                "channel_id": channel_id,
                "invite_link": invite_link,
                "is_request": is_request,
                "updated_at": datetime.now(timezone.utc)
            }},
            upsert=True
        )

    async def get_current_invite_link(self, channel_id):
        return self.invite_links.find_one({"channel_id": channel_id})

    async def get_fsub_request_progress(self, channel_id):
        data = self.fsub_progress.find_one({"channel_id": channel_id})
        if not data:
            data = {
                "channel_id": channel_id,
                "count": 0,
                "target": 1000,
                "completed": False
            }
            self.fsub_progress.insert_one(data)
        return data

    async def increment_fsub_request(self, channel_id, user_id):
        key = f"{channel_id}:{user_id}"

        if self.fsub_requests.find_one({"_id": key}):
            data = await self.get_fsub_request_progress(channel_id)
            data["duplicate"] = True
            data["just_completed"] = False
            return data

        self.fsub_requests.insert_one({
            "_id": key,
            "channel_id": channel_id,
            "user_id": user_id,
            "created_at": datetime.now(timezone.utc)
        })

        old = await self.get_fsub_request_progress(channel_id)
        count = old["count"] + 1
        target = old.get("target", 1000)
        completed = count >= target

        data = self.fsub_progress.find_one_and_update(
            {"channel_id": channel_id},
            {"$set": {
                "count": count,
                "completed": completed
            }},
            return_document=ReturnDocument.AFTER
        )

        data["duplicate"] = False
        data["just_completed"] = not old.get("completed", False) and completed
        return data

    async def set_fsub_request_target(self, channel_id, target=1000, reset=True):
        data = {
            "channel_id": channel_id,
            "target": target,
            "count": 0 if reset else 0,
            "completed": False
        }
        self.fsub_progress.update_one(
            {"channel_id": channel_id},
            {"$set": data},
            upsert=True
        )
        return data

    async def reset_fsub_request_progress(self, channel_id):
        return await self.set_fsub_request_target(channel_id, 1000, True)

    async def get_fsub_request_count(self, channel_id):
        data = await self.get_fsub_request_progress(channel_id)
        return data["count"]

    async def is_fsub_completed(self, channel_id):
        data = await self.get_fsub_request_progress(channel_id)
        return data["completed"]
