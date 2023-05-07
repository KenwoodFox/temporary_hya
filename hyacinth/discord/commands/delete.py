from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from discord import Member, Message, Reaction, User

from hyacinth.db.crud.notifier import delete_channel_notifiers
from hyacinth.db.session import Session
from hyacinth.notifier import ListingNotifier

if TYPE_CHECKING:
    from hyacinth.discord.discord_bot import DiscordNotifierBot

_logger = logging.getLogger(__name__)


async def delete_notifier(
    bot: DiscordNotifierBot, message: Message, notifier: ListingNotifier
) -> None:
    _logger.info(f"Received request to delete notifiers from channel {message.channel.id}")

    async def confirm_delete_notifier_handler(reaction: Reaction, user: Member | User) -> None:
        if user != message.author or reaction.emoji not in [
            "\u2705",  # :white_check_mark:
            "\u2714",  # :heavy_check_mark:
            "\u2611",  # :ballot_box_with_check:
        ]:
            return

        _logger.info(f"Confirmed deletion of notifiers from channel {message.channel.id}")
        del bot.notifiers[message.channel.id]
        notifier.cleanup()
        with Session() as session:
            delete_channel_notifiers(session, message.channel.id)
        await message.channel.send(
            f"{bot.affirm()} {message.author.mention}, I've deleted all of the notifiers from"
            " this channel."
        )
        del bot.reaction_handlers[reaction.message.id]

    confirmation_message = await message.channel.send(
        f"{bot.affirm()} {message.author.mention}, are you sure you want to delete the notifier"
        f" from this channel? All {len(notifier.config.active_searches)} searches and all filters"
        " will be deleted. React with \u2705 to confirm."
    )
    bot.reaction_handlers[confirmation_message.id] = confirm_delete_notifier_handler
