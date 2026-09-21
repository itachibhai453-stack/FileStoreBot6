#
#  Developed by t.me/napaaextra

from aiohttp import web
from plugins import web_server

from pyrogram import Client
from pyrogram.enums import ParseMode
import sys
from datetime import datetime

from config import LOGGER, PORT, OWNER_ID, SHORT_URL, SHORT_API
from helper import MongoDB, GofileManager


version = "v1.0.0"


class Bot(Client):

    def __init__(self, config):

        session = config["session"]
        workers = config["workers"]

        databases = config.get(
            "databases",
            {
                "primary": config.get("db"),
                "secondary": [],
                "backup": None
            }
        )

        fsub = config["fsubs"]
        token = config["token"]
        admins = config["admins"]
        messages = config.get("messages", {})
        auto_del = config["auto_del"]

        db_uri = config["db_uri"]
        db_name = config["db_name"]

        api_id = int(config["api_id"])
        api_hash = config["api_hash"]

        protect = config["protect"]
        disable_btn = config["disable_btn"]

        super().__init__(
            name=session,
            api_hash=api_hash,
            api_id=api_id,
            plugins={"root": "plugins"},
            workers=workers,
            bot_token=token
        )

        self.LOGGER = LOGGER
        self.name = session

        self.databases = databases
        self.db = databases.get("primary")

        # Force Subscribe
        self.fsub = fsub
        self.fsub_dict = {}

        self.owner = OWNER_ID

        self.admins = (
            admins + [OWNER_ID]
            if OWNER_ID not in admins
            else admins
        )

        self.messages = messages
        self.auto_del = auto_del

        # Request based FSub channels
        self.req_fsub = {}
        self.req_channels = []

        self.disable_btn = disable_btn

        self.reply_text = messages.get(
            "REPLY",
            "Do not send any useless message in the bot."
        )

        # MongoDB
        self.mongodb = MongoDB(
            db_uri,
            db_name
        )

        self.all_db_ids = []

        # Gofile
        self.gofile_enabled = config.get(
            "gofile_enabled",
            False
        )

        gofile_tokens = config.get(
            "gofile_tokens",
            []
        )

        self.gofile_manager = GofileManager(
            gofile_tokens,
            self.LOGGER(__name__, self.name)
        )

        self.active_uploads = set()

        # Other settings
        self.protect = protect

        self.shortner_enabled = True
        self.short_url = SHORT_URL
        self.short_api = SHORT_API

        self.tutorial_link = (
            "https://t.me/+zYJNXKoRIGs5YmY1"
        )

        self.auto_approval_enabled = False
        self.approval_delay = 5

        self.autobatch_template = ""

        self.hide_caption = False

        self.channel_button_enabled = False
        self.button_name = "Join Updates"
        self.button_url = "https://t.me/realm_bots"

        self.credit_system_enabled = False
        self.credits_per_visit = 1
        self.credits_per_file = 1
        self.max_credit_limit = 100

    # --------------------------------------------------
    # Legacy Settings
    # --------------------------------------------------

    def get_current_settings(self):

        return {
            "admins": self.admins,
            "messages": self.messages,
            "auto_del": self.auto_del,
            "disable_btn": self.disable_btn,
            "reply_text": self.reply_text,
            "fsub": self.fsub,
            "databases": self.databases
        }

    # --------------------------------------------------
    # START
    # --------------------------------------------------

    async def start(self):

        await super().start()

        usr_bot_me = await self.get_me()

        self.uptime = datetime.now()

        # --------------------------------------------------
        # Modern Settings
        # --------------------------------------------------

        from plugins.autobatch_settings import (
            DEFAULT_AUTOBATCH_TEMPLATE
        )

        self.autobatch_template = (
            await self.mongodb.load_bot_setting(
                "autobatch_template",
                DEFAULT_AUTOBATCH_TEMPLATE
            )
        )

        self.protect = await self.mongodb.load_bot_setting(
            "protect_content",
            self.protect
        )

        self.hide_caption = await self.mongodb.load_bot_setting(
            "hide_caption",
            False
        )

        self.channel_button_enabled = (
            await self.mongodb.load_bot_setting(
                "channel_button_enabled",
                False
            )
        )

        self.button_name = await self.mongodb.load_bot_setting(
            "button_name",
            self.button_name
        )

        self.button_url = await self.mongodb.load_bot_setting(
            "button_url",
            self.button_url
        )

        self.auto_approval_enabled = (
            await self.mongodb.load_bot_setting(
                "auto_approval_enabled",
                False
            )
        )

        self.approval_delay = await self.mongodb.load_bot_setting(
            "approval_delay",
            5
        )

        # --------------------------------------------------
        # Shortener
        # --------------------------------------------------

        self.shortner_enabled = (
            await self.mongodb.load_bot_setting(
                "shortner_enabled",
                True
            )
        )

        self.short_url = await self.mongodb.load_bot_setting(
            "short_url",
            SHORT_URL
        )

        self.short_api = await self.mongodb.load_bot_setting(
            "short_api",
            SHORT_API
        )

        self.tutorial_link = (
            await self.mongodb.load_bot_setting(
                "tutorial_link",
                self.tutorial_link
            )
        )

        # --------------------------------------------------
        # Credits
        # --------------------------------------------------

        self.credit_system_enabled = (
            await self.mongodb.load_bot_setting(
                "credit_system_enabled",
                False
            )
        )

        self.credits_per_visit = (
            await self.mongodb.load_bot_setting(
                "credits_per_visit",
                1
            )
        )

        self.credits_per_file = (
            await self.mongodb.load_bot_setting(
                "credits_per_file",
                1
            )
        )

        self.max_credit_limit = (
            await self.mongodb.load_bot_setting(
                "max_credit_limit",
                100
            )
        )

        # --------------------------------------------------
        # Gofile
        # --------------------------------------------------

        self.gofile_enabled = (
            await self.mongodb.load_bot_setting(
                "gofile_enabled",
                self.gofile_enabled
            )
        )

        db_gofile_tokens = (
            await self.mongodb.load_bot_setting(
                "gofile_tokens"
            )
        )

        if db_gofile_tokens is not None:

            self.gofile_manager = GofileManager(
                db_gofile_tokens,
                self.LOGGER(__name__, self.name)
            )

            self.LOGGER(
                __name__,
                self.name
            ).info(
                f"Loaded {len(db_gofile_tokens)} "
                f"Gofile tokens from the database."
            )

        elif (
            self.gofile_manager
            and self.gofile_manager.tokens
        ):

            self.LOGGER(
                __name__,
                self.name
            ).info(
                f"Using {self.gofile_manager.token_count} "
                f"Gofile tokens from setup.json."
            )

        # --------------------------------------------------
        # Validate Shortener
        # --------------------------------------------------

        if (
            not self.short_url
            or self.short_url.lower() in ["none", ""]
        ):
            self.short_url = SHORT_URL

        if (
            not self.short_api
            or self.short_api.lower() in ["none", ""]
        ):
            self.short_api = SHORT_API

        self.LOGGER(
            __name__,
            self.name
        ).info(
            "All modern settings loaded and validated."
        )

        # --------------------------------------------------
        # Legacy Settings
        # --------------------------------------------------

        saved_settings = await self.mongodb.load_settings(
            self.name
        )

        if saved_settings:

            self.LOGGER(
                __name__,
                self.name
            ).info(
                "Found legacy saved settings, merging them."
            )

            base_messages = self.messages.copy()

            saved_messages = saved_settings.get(
                "messages",
                {}
            )

            for key, value in saved_messages.items():

                if value:
                    base_messages[key] = value

            self.messages = base_messages

            saved_admins = saved_settings.get(
                "admins",
                []
            )

            self.admins = list(
                set(
                    self.admins
                    + saved_admins
                    + [OWNER_ID]
                )
            )

            if saved_fsub := saved_settings.get("fsub"):
                self.fsub = saved_fsub

            if saved_databases := saved_settings.get(
                "databases"
            ):

                self.databases = saved_databases

                self.db = self.databases.get(
                    "primary"
                )

            self.auto_del = saved_settings.get(
                "auto_del",
                self.auto_del
            )

            self.disable_btn = saved_settings.get(
                "disable_btn",
                self.disable_btn
            )

            self.reply_text = saved_settings.get(
                "reply_text",
                self.reply_text
            )

        # ==================================================
        # FORCE SUB INITIALIZATION
        # ==================================================

        self.fsub_dict = {}
        self.req_channels = []

        if self.fsub:

            for channel_id, needs_request, timer in self.fsub:

                try:

                    chat = await self.get_chat(
                        channel_id
                    )

                    invite_link = None

                    # --------------------------------------------------
                    # Permanent link
                    # --------------------------------------------------

                    if timer <= 0:

                        try:

                            # First try MongoDB saved link
                            saved_link = (
                                await self.mongodb
                                .get_current_invite_link(
                                    channel_id
                                )
                            )

                            if (
                                saved_link
                                and saved_link.get(
                                    "invite_link"
                                )
                                and saved_link.get(
                                    "is_request"
                                ) == needs_request
                            ):

                                invite_link = (
                                    saved_link[
                                        "invite_link"
                                    ]
                                )

                                self.LOGGER(
                                    __name__,
                                    self.name
                                ).info(
                                    f"Using saved invite "
                                    f"link for {channel_id}"
                                )

                            # --------------------------------------------------
                            # Create only if no saved link
                            # --------------------------------------------------

                            if not invite_link:

                                invite = (
                                    await self
                                    .create_chat_invite_link(
                                        channel_id,
                                        creates_join_request=(
                                            needs_request
                                        )
                                    )
                                )

                                invite_link = (
                                    invite.invite_link
                                )

                                # Save link to MongoDB
                                await self.mongodb.save_invite_link(
                                    channel_id,
                                    invite_link,
                                    needs_request
                                )

                                self.LOGGER(
                                    __name__,
                                    self.name
                                ).info(
                                    f"Created and saved "
                                    f"invite link for {channel_id}"
                                )

                        except Exception as e:

                            self.LOGGER(
                                __name__,
                                self.name
                            ).error(
                                f"Invite link error for "
                                f"{channel_id}: {e}"
                            )

                            # Fallback to Telegram chat invite
                            if (
                                not needs_request
                                and chat.invite_link
                            ):
                                invite_link = (
                                    chat.invite_link
                                )

                    # --------------------------------------------------
                    # Store FSub data
                    # --------------------------------------------------

                    self.fsub_dict[channel_id] = [
                        chat.title,
                        invite_link,
                        needs_request,
                        timer
                    ]

                    # --------------------------------------------------
                    # Request enabled channel
                    # --------------------------------------------------

                    if needs_request:

                        if channel_id not in self.req_channels:
                            self.req_channels.append(
                                channel_id
                            )

                        # Load current progress
                        try:

                            progress = (
                                await self.mongodb
                                .get_fsub_request_progress(
                                    channel_id
                                )
                            )

                            self.req_fsub[channel_id] = progress

                        except Exception as e:

                            self.LOGGER(
                                __name__,
                                self.name
                            ).warning(
                                f"Couldn't load FSub "
                                f"progress for "
                                f"{channel_id}: {e}"
                            )

                except Exception as e:

                    self.LOGGER(
                        __name__,
                        self.name
                    ).error(
                        f"Error processing FSub "
                        f"channel {channel_id}: {e}"
                    )

            # Save request channels
            await self.mongodb.set_channels(
                self.req_channels
            )

        # ==================================================
        # PRIMARY DATABASE
        # ==================================================

        if not self.db:

            self.LOGGER(
                __name__,
                self.name
            ).warning(
                "No Primary Database channel is set!"
            )

        else:

            try:

                db_channel = await self.get_chat(
                    self.db
                )

                self.db_channel = db_channel

                test = await self.send_message(
                    chat_id=db_channel.id,
                    text="Bot is online."
                )

                await test.delete()

            except Exception as e:

                self.LOGGER(
                    __name__,
                    self.name
                ).warning(e)

                self.LOGGER(
                    __name__,
                    self.name
                ).warning(
                    "Make sure bot is Admin in Primary DB "
                    f"Channel. Current Value {self.db}"
                )

        # ==================================================
        # DATABASE CHANNELS
        # ==================================================

        self.all_db_ids = [
            db_id
            for db_id in [
                self.databases.get("primary")
            ]
            + self.databases.get(
                "secondary",
                []
            )
            if db_id
        ]

        self.LOGGER(
            __name__,
            self.name
        ).info(
            f"Loaded {len(self.all_db_ids)} DB channels."
        )

        self.LOGGER(
            __name__,
            self.name
        ).info(
            f"Bot Started on @{usr_bot_me.username} !!"
        )

        self.username = usr_bot_me.username

    # --------------------------------------------------
    # STOP
    # --------------------------------------------------

    async def stop(self, *args):

        await super().stop()

        self.LOGGER(
            __name__,
            self.name
        ).info(
            "Bot stopped."
        )


# ======================================================
# WEB SERVER
# ======================================================

async def web_app():

    app = web.AppRunner(
        await web_server()
    )

    await app.setup()

    bind_address = "0.0.0.0"

    await web.TCPSite(
        app,
        bind_address,
        PORT
    ).start()
