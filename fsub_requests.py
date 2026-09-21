from pyrogram import Client
from pyrogram.types import ChatJoinRequest


@Client.on_chat_join_request()
async def fsub_join_request(client: Client, request: ChatJoinRequest):

    channel_id = request.chat.id
    user_id = request.from_user.id

    # Check whether this is one of our Force Sub channels
    if channel_id not in client.req_channels:
        return

    try:
        progress = await client.mongodb.increment_fsub_request(channel_id)

        count = progress["count"]
        target = progress["target"]

        # Update in-memory status if needed
        client.req_fsub[channel_id] = progress

        channel_name = request.chat.title or str(channel_id)

        if progress["completed"]:
            text = (
                "🎉 <b>FORCE SUB COMPLETED!</b>\n\n"
                f"📢 <b>Channel:</b> {channel_name}\n"
                f"🆔 <b>ID:</b> <code>{channel_id}</code>\n"
                f"📊 <b>Requests:</b> {count}/{target}\n"
                "✅ <b>Status: COMPLETED</b>"
            )

            # Send completion message to owner
            for admin_id in client.admins:
                try:
                    await client.send_message(
                        admin_id,
                        text
                    )
                except Exception:
                    pass

        else:
            # Optional progress notification
            if count % 100 == 0:
                text = (
                    "📊 <b>FORCE SUB PROGRESS</b>\n\n"
                    f"📢 <b>{channel_name}</b>\n"
                    f"👥 <b>Requests:</b> {count}/{target}\n"
                    f"⏳ <b>Remaining:</b> {max(target - count, 0)}"
                )

                for admin_id in client.admins:
                    try:
                        await client.send_message(
                            admin_id,
                            text
                        )
                    except Exception:
                        pass

    except Exception as e:
        client.LOGGER(
            __name__,
            client.name
        ).error(
            f"Join request counter error for {channel_id}: {e}"
        )
