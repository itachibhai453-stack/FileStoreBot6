#  Developed by t.me/napaaextra

import motor.motor_asyncio
import uuid
import base64
from datetime import datetime, timedelta

class MongoDB:
    _instances = {}

    def __new__(cls, uri: str, db_name: str):
        if (uri, db_name) not in cls._instances:
            instance = super().__new__(cls)
            instance.client = motor.motor_asyncio.AsyncIOMotorClient(uri)
            instance.db = instance.client[db_name]
            instance.user_data = instance.db["users"]
            instance.channel_data = instance.db["channels"]
            instance.bot_settings = instance.db["bot_settings"]
            instance.batch_data = instance.db["batch_links"]
            instance.backup_map = instance.db["backup_map"]
            instance.premium_users = instance.db['pros']
            instance.shortner_settings = instance.db["shortner_settings"]
            instance.approval_config = instance.db["approval_config"]
            instance.gofile_links = instance.db["gofile_links"]
            cls._instances[(uri, db_name)] = instance
        return cls._instances[(uri, db_name)]

    async def save_batch(self, channel_id: int, file_ids: list) -> str:
        """Saves a list of file IDs and their channel, returns a unique key."""
        key = str(uuid.uuid4().hex[:8])
        await self.batch_data.insert_one(
            {"_id": key, "channel_id": channel_id, "ids": file_ids}
        )
        return key

    async def get_batch(self, key: str) -> tuple | None:
        """Retrieves channel_id and a list of file IDs by its unique key."""
        data = await self.batch_data.find_one({"_id": key})
        return (data.get("channel_id"), data.get("ids")) if data else (None, None)

    async def add_backup_mapping(self, original_chat_id: int, original_msg_id: int, backup_msg_id: int):
        """Stores a mapping from an original message to its backup."""
        await self.backup_map.update_one(
            {"_id": f"{original_chat_id}:{original_msg_id}"},
            {"$set": {"backup_msg_id": backup_msg_id}},
            upsert=True
        )

    async def get_backup_msg_id(self, original_chat_id: int, original_msg_id: int) -> int | None:
        """Retrieves the backup message ID for an original message."""
        data = await self.backup_map.find_one({"_id": f"{original_chat_id}:{original_msg_id}"})
        return data.get("backup_msg_id") if data else None

    async def is_backed_up(self, original_chat_id: int, original_msg_id: int) -> bool:
        """Checks if a backup mapping exists for a message."""
        count = await self.backup_map.count_documents({"_id": f"{original_chat_id}:{original_msg_id}"})
        return count > 0

    async def save_settings(self, session_name: str, settings: dict):
        """Saves the bot's legacy settings to the database."""
        await self.bot_settings.update_one(
            {"_id": session_name},
            {"$set": {"settings": settings}},
            upsert=True
        )

    async def load_settings(self, session_name: str) -> dict | None:
        """Loads the bot's legacy settings from the database."""
        data = await self.bot_settings.find_one({"_id": session_name})
        return data.get("settings") if data else None

    async def save_bot_setting(self, key: str, value):
        """Saves a single bot-wide setting."""
        await self.bot_settings.update_one({'_id': 'global_config'}, {'$set': {key: value}}, upsert=True)
    
    async def load_bot_setting(self, key: str, default=None):
        """Loads a single bot-wide setting."""
        config = await self.bot_settings.find_one({'_id': 'global_config'})
        return config.get(key, default) if config else default
        
    async def set_auto_approval(self, channel_id: int, status: bool):
        """Enable or disable auto approval for a specific channel."""
        if status:
            await self.approval_config.update_one({'_id': channel_id}, {'$set': {'enabled': True}}, upsert=True)
        else:
            await self.approval_config.delete_one({'_id': channel_id})

    async def is_auto_approval_enabled(self, channel_id: int) -> bool:
        """Check if auto approval is enabled for a channel."""
        doc = await self.approval_config.find_one({'_id': channel_id})
        return doc is not None

    async def get_auto_approval_channels(self) -> list:
        """Get a list of all channels with auto approval enabled."""
        cursor = self.approval_config.find({'enabled': True})
        return [doc['_id'] async for doc in cursor]

    async def add_pro(self, user_id: int, expiry_date: datetime = None):
        try:
            await self.premium_users.update_one(
                {'_id': user_id},
                {'$set': {'expiry_date': expiry_date}},
                upsert=True
            )
            return True
        except Exception as e:
            print(f"Failed to add premium user: {e}")
            return False

    async def remove_pro(self, user_id: int):
        try:
            await self.premium_users.delete_one({'_id': user_id})
            return True
        except Exception as e:
            print(f"Failed to remove premium user: {e}")
            return False

    async def is_pro(self, user_id: int):
        doc = await self.premium_users.find_one({'_id': user_id})
        if not doc:
            return False
        if 'expiry_date' not in doc:
            return True
        if doc['expiry_date'] is None:
            return True
        return doc['expiry_date'] > datetime.now()

    async def get_pros_list(self):
        current_time = datetime.now()
        cursor = self.premium_users.find({
            '$or': [
                {'expiry_date': None},
                {'expiry_date': {'$exists': False}},
                {'expiry_date': {'$gt': current_time}}
            ]
        })
        return [doc['_id'] async for doc in cursor]
        
    async def get_expiry_date(self, user_id: int) -> datetime:
        doc = await self.premium_users.find_one({'_id': user_id})
        return doc.get('expiry_date') if doc else None
        
    async def update_shortner_setting(self, key: str, value):
        """Updates a specific shortener setting."""
        await self.shortner_settings.update_one(
            {"_id": "shortner_config"},
            {"$set": {key: value}},
            upsert=True
        )
    
    async def get_shortner_settings(self) -> dict:
        """Retrieves all shortener settings."""
        data = await self.shortner_settings.find_one({"_id": "shortner_config"})
        return data if data else {}
    
    async def set_shortner_status(self, enabled: bool):
        """Sets the shortener enabled/disabled status."""
        await self.shortner_settings.update_one(
            {"_id": "shortner_config"},
            {"$set": {"enabled": enabled}},
            upsert=True
        )
    
    async def get_shortner_status(self) -> bool:
        """Gets the shortener enabled/disabled status."""
        data = await self.shortner_settings.find_one({"_id": "shortner_config"})
        return data.get("enabled", True) if data else True
    
    async def set_channels(self, channels: list[int]):
        await self.user_data.update_one(
            {"_id": 1},
            {"$set": {"channels": channels}},
            upsert=True
        )
    
    async def get_channels(self) -> list[int]:
        data = await self.user_data.find_one({"_id": 1})
        return data.get("channels", []) if data else []
    
    async def add_channel_user(self, channel_id: int, user_id: int):
        await self.channel_data.update_one(
            {"_id": channel_id},
            {"$addToSet": {"users": user_id}},
            upsert=True
        )

    async def remove_channel_user(self, channel_id: int, user_id: int):
        await self.channel_data.update_one(
            {"_id": channel_id},
            {"$pull": {"users": user_id}}
        )

    async def get_channel_users(self, channel_id: int) -> list[int]:
        doc = await self.channel_data.find_one({"_id": channel_id})
        return doc.get("users", []) if doc else []
        
    async def is_user_in_channel(self, channel_id: int, user_id: int) -> bool:
        doc = await self.channel_data.find_one(
            {"_id": channel_id, "users": {"$in": [user_id]}},
            {"_id": 1}
        )
        return doc is not None

    async def present_user(self, user_id: int) -> bool:
        found = await self.user_data.find_one({'_id': user_id})
        return bool(found)

    async def add_user(self, user_id: int, ban: bool = False):
        await self.user_data.update_one(
            {'_id': user_id},
            {'$setOnInsert': {'ban': ban, 'credits': 0}},
            upsert=True
        )

    async def full_userbase(self) -> list[int]:
        user_docs = self.user_data.find()
        return [doc['_id'] async for doc in user_docs]

    async def del_user(self, user_id: int):
        await self.user_data.delete_one({'_id': user_id})

    async def ban_user(self, user_id: int):
        await self.user_data.update_one({'_id': user_id}, {'$set': {'ban': True}})

    async def unban_user(self, user_id: int):
        await self.user_data.update_one({'_id': user_id}, {'$set': {'ban': False}})

    async def is_banned(self, user_id: int) -> bool:
        user = await self.user_data.find_one({'_id': user_id})
        return user.get('ban', False) if user else False

    async def get_credits(self, user_id: int) -> int:
        user = await self.user_data.find_one({'_id': user_id})
        return user.get('credits', 0) if user else 0

    async def update_credits(self, user_id: int, amount: int):
        """Atomically increments or decrements user credits."""
        await self.user_data.update_one(
            {'_id': user_id},
            {'$inc': {'credits': amount}},
            upsert=True
        )

    async def set_credits(self, user_id: int, amount: int):
        """Sets a user's credits to a specific value."""
        await self.user_data.update_one(
            {'_id': user_id},
            {'$set': {'credits': amount}},
            upsert=True
        )
    
    async def save_gofile_link(self, channel_id: int, message_id: int, gofile_url: str):
        """Saves a Gofile.io URL for a specific message."""
        await self.gofile_links.update_one(
            {"_id": f"{channel_id}:{message_id}"},
            {"$set": {"url": gofile_url}},
            upsert=True
        )

    async def get_gofile_link(self, channel_id: int, message_id: int) -> str | None:
        """Retrieves a Gofile.io URL for a specific message."""
        doc = await self.gofile_links.find_one({"_id": f"{channel_id}:{message_id}"})
        return doc.get("url") if doc else None
    

    async def save_link_channel(self, channel_id: int):
        """Save a channel to link sharing system"""
        await self.user_data.update_one(
            {"_id": "link_channels"},
            {"$addToSet": {"channels": channel_id}},
            upsert=True
        )

    async def remove_link_channel(self, channel_id: int) -> bool:
        """Remove a channel from link sharing system"""
        result = await self.user_data.update_one(
            {"_id": "link_channels"},
            {"$pull": {"channels": channel_id}}
        )
        return result.modified_count > 0

    async def get_link_channels(self) -> list:
        """Get all link sharing channels"""
        data = await self.user_data.find_one({"_id": "link_channels"})
        return data.get("channels", []) if data else []

    async def is_link_channel(self, channel_id: int) -> bool:
        """Check if channel is in link sharing system"""
        data = await self.user_data.find_one(
            {"_id": "link_channels", "channels": {"$in": [channel_id]}}
        )
        return data is not None

    async def save_invite_link(self, channel_id: int, invite_link: str, is_request: bool):
        """Save current invite link for a channel"""
        await self.user_data.update_one(
            {"_id": f"invite_{channel_id}"},
            {
                "$set": {
                    "invite_link": invite_link,
                    "is_request": is_request,
                    "created_at": datetime.utcnow()
                }
            },
            upsert=True
        )

    async def get_current_invite_link(self, channel_id: int) -> dict:
        """Get current invite link for a channel"""
        data = await self.user_data.find_one({"_id": f"invite_{channel_id}"})
        if data:
            return {
                "invite_link": data.get("invite_link"),
                "is_request": data.get("is_request", False)
            }
        return None

    async def decode_link_param(self, param: str) -> str:
        """Decode link parameter - NOT ASYNC, just helper"""
        try:
            base64_string = param.strip("=")
            base64_bytes = (base64_string + "=" * (-len(base64_string) % 4)).encode("ascii")
            string_bytes = base64.urlsafe_b64decode(base64_bytes)
            return string_bytes.decode("ascii")
        except Exception as e:
            print(f"Decode error: {e}")
            return None
            
                async def get_fsub_request_progress(self, channel_id: int) -> dict:
        """Get request counter for a force-sub channel."""
        data = await self.user_data.find_one(
            {"_id": f"fsub_progress_{channel_id}"}
        )

        if not data:
            return {
                "count": 0,
                "target": 1000,
                "completed": False
            }

        return {
            "count": data.get("count", 0),
            "target": data.get("target", 1000),
            "completed": data.get("completed", False)
        }

    async def increment_fsub_request(self, channel_id: int) -> dict:
        """Atomically increase ForceSub request counter."""

        data = await self.user_data.find_one_and_update(
            {"_id": f"fsub_progress_{channel_id}"},
            {
                "$inc": {"count": 1},
                "$setOnInsert": {
                    "target": 1000,
                    "completed": False
                }
            },
            upsert=True,
            return_document=True
        )

        count = data.get("count", 0)
        target = data.get("target", 1000)

        if count >= target and not data.get("completed", False):
            await self.user_data.update_one(
                {"_id": f"fsub_progress_{channel_id}"},
                {"$set": {"completed": True}}
            )
            completed = True
        else:
            completed = data.get("completed", False)

        return {
            "count": count,
            "target": target,
            "completed": completed
        }

    async def set_fsub_request_target(
        self,
        channel_id: int,
        target: int = 1000
    ):
        """Set target request count for a channel."""

        await self.user_data.update_one(
            {"_id": f"fsub_progress_{channel_id}"},
            {
                "$set": {
                    "target": target,
                    "count": 0,
                    "completed": False
                }
            },
            upsert=True
        )
