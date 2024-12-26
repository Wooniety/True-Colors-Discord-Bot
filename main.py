import os
from dotenv import load_dotenv

import discord
from discord.ext import commands

from TrueColours import TrueColours

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
DEFAULT_BUTTON_PARAMS = {
    "style": discord.ButtonStyle.secondary
}

intents = discord.Intents.default()
intents.members = True
intents.reactions = True
intents.message_content = True

bot = commands.Bot(command_prefix="$", intents=intents)

colour_emojis = ["🔴", "🟠", "🟡", "🟢", "🔵", "🟣"]
prediction_emojis = {"💕": "most", "💓": "some", "💔": "none"}
games = {}

@bot.event
async def on_ready():
    print(f"We have logged in as {bot.user}")

def getGameByChannel(id):
    return games.get(id)

def getGameByJoinId(channel_id, id):
    game = getGameByChannel(channel_id)
    return game if game is None or game.join_msg_id == id else None

def getGameByVoteId(channel_id, id):
    game = getGameByChannel(channel_id)
    return game if game is None or id in game.vote_ids.keys() else None

def getGameByPredictionId(channel_id, id):
    game = getGameByChannel(channel_id)
    return game if game is None or id == game.prediction_id else None

async def joinGameHandler(
    interaction: discord.Interaction, emoji: str, user: discord.User | discord.Member, game: TrueColours
):
    if interaction.message is None:
        return

    # Check if player is in game
    if user.id in game.players.keys():
        await interaction.response.send_message(f"{user.mention} is already in game!")
        return

    # Check if colour has already been picked
    if emoji in game.colour_lookup.keys():
        await interaction.response.send_message(
            f"{user.mention}, that colour has already been picked!"
        )
        return

    if emoji in colour_emojis:
        game.add_player(user.id, user.display_name, emoji, user)
        await interaction.response.send_message(
            f"{user.mention} has joined the game with the color {emoji}!"
        )


async def voteHandler(
    interaction: discord.Interaction, emoji: str, user: discord.User | discord.Member, game: TrueColours, vote_id
):
    vote_num = 0
    confirm_msg = ""

    if game.vote_ids[vote_id][0] == 0:
        game.lock_vote(user.id)
        await interaction.response.send_message("Voting is locked!", ephemeral=True)
        return

    if emoji == game.players[user.id]["colour"]:
        await interaction.response.send_message("You cannot vote for yourself!", ephemeral=True)
        return

    if game.vote_ids[vote_id][0] == 1:
        result = game.add_vote_1(user.id, emoji)
        vote_num = 1
    else:
        result = game.add_vote_2(user.id, emoji)
        vote_num = 2

    if not result:
        await interaction.response.send_message("Vote is already locked!", ephemeral=True)
        return

    confirm_msg = f"Vote {vote_num}: {emoji}"
    print(f"{user.display_name} vote {vote_num}: {emoji} {str(emoji)}")
    await interaction.response.send_message(confirm_msg, ephemeral=True)


async def predictionHandler(
    interaction: discord.Interaction, emoji: str, user: discord.User | discord.Member, game: TrueColours
):
    if emoji not in prediction_emojis.keys():
        prediction = game.get_prediction(user.id)
        if prediction == "":
            await interaction.response.send_message(f"You cannot lock your vote without voting!", ephemeral=True)
            return

        result = game.lock_vote(user.id)
        if result:
            await interaction.response.send_message(f"{user.mention} has voted!")
        return

    prediction = prediction_emojis[emoji]
    game.add_prediction(user.id, prediction)
    await interaction.response.send_message(f"Your vote has been registered, click ⏩ to lock it in!", ephemeral=True)

@bot.event
async def on_interaction(interaction: discord.Interaction):
    action = interaction.data.get("custom_id", "")
    action = action.split('|')
    user = interaction.user
    if len(action) != 2 or interaction.message is None or user is None:
        return

    action, value = action
    channel_id = interaction.channel_id
    msg_id = interaction.message.id

    if action == "JOIN_GAME":
        game = getGameByJoinId(channel_id, msg_id)
        if game != None:
            await joinGameHandler(interaction, value, user, game)
    elif action == "VOTE":
        game = getGameByVoteId(channel_id, msg_id)
        if game != None:
            await voteHandler(interaction, value, user, game, msg_id)
    elif action == "PREDICT":
        game = getGameByPredictionId(channel_id, msg_id)
        if game != None:
            await predictionHandler(interaction, value, user, game)

@bot.command()
async def creategame(ctx: commands.Context):
    if ctx.guild is None:
        await ctx.send("This command can only be used in a server.")
        return
    if ctx.message.author.bot:
        return  # Ignore messages from other bots

    # Send a message to start the game
    channel_id = ctx.channel.id
    if channel_id in games:
        await ctx.send("There is already a game running!")
        return

    # Add reactions to the message
    view = discord.ui.View()
    for emoji in colour_emojis:
        button = discord.ui.Button(
            **DEFAULT_BUTTON_PARAMS,
            custom_id=f"JOIN_GAME|{emoji}",
            emoji=emoji,
        )
        view.add_item(button)

    # Setup game
    create_message = await ctx.send("Game started! Please pick a colour.", view=view)
    games[channel_id] = TrueColours(create_message.id, channel_id)

def gen_list_of_players(game: TrueColours):
    player_list_str = ""
    for player in game.players.keys():
        player_name = game.players[player]["name"]
        colour = game.players[player]["colour"]
        player_list_str += f"\n{player_name} - {colour}"
    return player_list_str


async def prompt_voting(ctx: commands.Context, game: TrueColours, round_num):
    view = discord.ui.View()
    for emoji in colour_emojis:
        button = discord.ui.Button(
            **DEFAULT_BUTTON_PARAMS,
            custom_id=f"JOIN_GAME|{emoji}",
            emoji=emoji,
        )
        view.add_item(button)

    msg = (
        f"\n**Round {round_num}/10**\n*{game.curr_qn}*{gen_list_of_players(game)}\n"
    )
    view = discord.ui.View()
    view.add_item(discord.ui.Button(**DEFAULT_BUTTON_PARAMS, custom_id="VOTE|☑️", emoji="☑️"))
    msg = await ctx.send(msg, view=view)
    game.vote_ids[msg.id] = [0]

    view = discord.ui.View()
    for colour in game.colour_lookup.keys():
        button = discord.ui.Button(
            **DEFAULT_BUTTON_PARAMS,
            custom_id=f"VOTE|{colour}",
            emoji=colour
        )
        view.add_item(button)

    for idx in range(1, 3):
        vote_msg = await ctx.send(f"Vote {idx}", view=view)
        game.vote_ids[vote_msg.id] = [idx]

def cnt_check(reaction, user):
    return reaction.emoji == "⏩"


async def prompt_prediction(ctx, game: TrueColours, round_num):
    view = discord.ui.View()
    for emoji in prediction_emojis.keys():
        button = discord.ui.Button(
            **DEFAULT_BUTTON_PARAMS,
            custom_id=f"PREDICT|{emoji}",
            emoji=emoji
        )
        view.add_item(button)
    button = discord.ui.Button(**DEFAULT_BUTTON_PARAMS, custom_id=f"PREDICT|⏩", emoji="⏩")
    view.add_item(button)

    prompt_msg = await ctx.send(
        "How do you think your friends voted for you?\n💕 - Most\n💓 - Some\n💔 - None\n\n Click ⏩ when you are done",
        view=view
    )

    game.prediction_id = prompt_msg.id

def gen_round_results_msg(game: TrueColours):
    results = ""
    for player in game.players.keys():
        player_data = game.players[player]

        name = player_data["name"]
        votes = player_data["votes"]
        roundResult = player_data["roundResult"]

        results += f"\n{name} ({roundResult.upper()})- {votes} vote(s)"
    return results


async def run_game_round(ctx: commands.Context, game: TrueColours, round_num):
    game.reset_round()

    # Display prompt
    game.pick_qn()

    # Vote
    await prompt_voting(ctx, game, round_num)
    await game.tally_votes()
    game.determine_round_result()

    await prompt_prediction(ctx, game, round_num)
    await game.wait_next.wait()

    # Count score
    game.assign_points()

    results = gen_round_results_msg(game)
    await ctx.send(f"\n**Round {round_num}/10 results:**{results}\n")


def gen_scoreboard(game):
    msg = "\n**SCOREBOARD**"
    for player in game.players.keys():
        player_data = game.players[player]

        colour = player_data["colour"]
        name = player_data["name"]
        points = player_data["points"]

        msg += f"\n{colour} {name} - {points}"

    winner_id, winner_score = game.get_winner()
    winners = []
    for id in winner_id:
        winners.append(game.players[id]["name"])
    winner_string = " and ".join(winners)
    msg += f"\n\nThe winner is... {winner_string} with a score of {winner_score}!"

    return msg


@bot.command()
async def startgame(ctx: commands.Context):
    if ctx.guild is None:
        await ctx.send("This command can only be used in a server.")
        return
    if ctx.message.author.bot:
        return  # Ignore messages from other bots

    game = getGameByChannel(ctx.message.channel.id)
    if game is None:
        await ctx.send("Use creategame to create a game first!")
        return

    if len(game.players) == 0:
        await ctx.send("No players to start game!")
        return

    for i in range(10):
        await run_game_round(ctx, game, i + 1)

    msg = gen_scoreboard(game)
    await ctx.send(msg)


# Run the bot with your token
bot.run(TOKEN)
