from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord
from boolean import ParseError

from hyacinth.discord.commands.shared import get_notifier
from hyacinth.discord.views.confirm_delete import ConfirmDelete
from hyacinth.enums import RuleType
from hyacinth.filters import parse_numeric_rule_expr, parse_string_rule_expr
from hyacinth.plugin import Plugin

if TYPE_CHECKING:
    from hyacinth.discord.discord_bot import DiscordBot

_logger = logging.getLogger(__name__)


def validate_filter_expr(plugins: list[Plugin], field: str, expr: str) -> None:
    targeted_fields = [
        plugin.listing_cls.model_fields[field]
        for plugin in plugins
        if field in plugin.listing_cls.model_fields
    ]

    # check if the field is valid for any active plugin
    if not targeted_fields:
        raise ValueError(f"Field {field} is not a valid field for any active plugin.")

    # if the field is numerical, check if the expression is a valid numerical rule
    targets_numerical_field = any(
        targeted_field.annotation in (int, float) for targeted_field in targeted_fields
    )
    if targets_numerical_field:
        parse_numeric_rule_expr(expr)  # raises ValueError if invalid
        return

    # verify string contains only tokens allowed by the boolean algebra system
    # (alphanumeric and boolean operators/grouping symbols)
    try:
        parse_string_rule_expr(expr)
    except ParseError as e:
        raise ValueError(f"Invalid token in rule: {e.token_string}")


async def create_filter(
    bot: DiscordBot,
    interaction: discord.Interaction,
    field: str,
    rule_type: RuleType,
    rule_expr: str,
) -> None:
    notifier = await get_notifier(bot, interaction)
    if not notifier:
        return

    try:
        validate_filter_expr(notifier.get_active_plugins(), field, rule_expr)
    except ValueError as e:
        await interaction.response.send_message(
            f"Sorry {interaction.user.mention}, the filter rule you provided is not valid for"
            f' field "{field}": ```{e}```',
            ephemeral=True,
        )
        return

    notifier.add_filter(field, rule_type, rule_expr)
    await interaction.response.send_message(
        f"{bot.affirm()} {interaction.user.mention}, I've added a new filter rule for field"
        f' "{field}".',
        ephemeral=True,
    )


async def edit_filter(
    bot: DiscordBot, interaction: discord.Interaction, filter_idx: int, new_rule: str
) -> None:
    notifier = await get_notifier(bot, interaction)
    if not notifier:
        return
    filter_ = notifier.config.filters[filter_idx]

    try:
        validate_filter_expr(notifier.get_active_plugins(), filter_.field, new_rule)
    except ValueError as e:
        await interaction.response.send_message(
            f"Sorry {interaction.user.mention}, the filter rule you provided is not valid for"
            f' field "{filter_.field}": ```{e}```',
            ephemeral=True,
        )
        return

    notifier.update_filter(filter_, new_rule)
    await interaction.response.send_message(
        f"{bot.affirm()} {interaction.user.mention}, I've updated your filter rule for field"
        f' "{filter_.field}".',
        ephemeral=True,
    )


async def delete_filter(bot: DiscordBot, interaction: discord.Interaction, filter_idx: int) -> None:
    notifier = await get_notifier(bot, interaction)
    if not notifier:
        return
    filter_ = notifier.config.filters[filter_idx]
    formatted_filter = (
        f"{str(filter_.rule_type.value).upper()} {filter_.field}: {filter_.rule_expr}"
    )

    # send confirmation dialog before deleting
    confirm = ConfirmDelete()
    confirmation_message = await interaction.channel.send(  # type: ignore
        "Are you sure you want to continue? This will permanently delete your filter rule"
        f' "{formatted_filter}"',
        view=confirm,
    )
    await interaction.response.defer(ephemeral=True)
    await confirm.wait()
    await confirmation_message.delete()

    if confirm.value:
        notifier.remove_filter(filter_)
        await interaction.followup.send(
            content=(
                f"{bot.affirm()} {interaction.user.mention}, I deleted your filter"
                f" {formatted_filter}."
            ),
            ephemeral=True,
        )
    else:
        await interaction.followup.send(
            "Operation cancelled.",
            ephemeral=True,
        )
