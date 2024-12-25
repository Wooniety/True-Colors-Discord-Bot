import os
from dotenv import load_dotenv

import discord
from discord.ext import commands

from TrueColours import TrueColours

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.members = True
intents.reactions = True
intents.message_content = True

bot = commands.Bot(command_prefix="$", intents=intents)

colour_emojis = ["🔴", "🟠", "🟡", "🟢", "🔵", "🟣"]
prediction_emojis = {"💕": "most", "💓": "some", "💔": "none"}
games = []


@bot.event
async def on_ready():
    print(f"We have logged in as {bot.user}")


def getGameByJoinId(id):
    for game in games:
        if game.join_msg_id == id:
            return game

    return None


def getGameByChannel(id):
    for game in games:
        if game.channel_id == id:
            return game

    return None


def getGameByVoteId(id):
    for game in games:
        if id in game.vote_ids.keys():
            return game

    return None


def getGameByPredictionId(id):
    for game in games:
        if id == game.prediction_id:
            return game

    return None


async def joinGameHandler(
    reaction: discord.Reaction, user: discord.User, game: TrueColours
):
    # Check if player is in game
    if user.id in game.players.keys():
        await reaction.message.channel.send(f"{user.mention} is already in game!")
        return

    # Check if colour has already been picked
    if reaction.emoji in game.colour_lookup.keys():
        await reaction.message.channel.send(
            f"{user.mention}, that colour has already been picked!"
        )
        return

    if str(reaction.emoji) in colour_emojis:
        game.add_player(user.id, user.display_name, reaction.emoji, user)
        await reaction.message.channel.send(
            f"{user.mention} has joined the game with the color {reaction.emoji}!"
        )


async def voteHandler(
    reaction: discord.Reaction, user: discord.User, game: TrueColours, vote_id
):
    player = game.vote_ids[vote_id][0]
    vote = reaction.emoji
    if vote == "☑️":
        game.lock_vote(player)
        return
    vote_num = 0
    confirm_msg = ""

    if game.vote_ids[vote_id][1] == 1:
        result = game.add_vote_1(player, vote)
        vote_num = 1
    else:
        result = game.add_vote_2(player, vote)
        vote_num = 2

    dm_channel = await user.create_dm()
    if not result:
        await dm_channel.send("Vote is already locked!")
        return

    confirm_msg = f"Vote {vote_num}: {vote}"
    print(f"{user.display_name} vote {vote_num}: {vote} {str(vote)}")
    await dm_channel.send(confirm_msg)


async def predictionHandler(
    reaction: discord.Reaction, user: discord.User, game: TrueColours
):
    if reaction.emoji not in prediction_emojis.keys():
        return

    prediction = prediction_emojis[reaction.emoji]
    game.add_prediction(user.id, prediction)
    await reaction.message.channel.send(f"{user.mention} has voted!")


@bot.event
async def on_reaction_add(reaction: discord.Reaction, user: discord.User):
    if user.bot:
        return

    msg_id = reaction.message.id

    # Join game
    game = getGameByJoinId(msg_id)
    if game != None:
        await joinGameHandler(reaction, user, game)
        return

    # Submit vote
    game = getGameByVoteId(msg_id)
    if game != None:
        await voteHandler(reaction, user, game, msg_id)
        return

    # Submit prediction
    game = getGameByPredictionId(msg_id)
    if game != None:
        await predictionHandler(reaction, user, game)
        return


@bot.command()
async def creategame(ctx):
    if ctx.guild is None:
        await ctx.send("This command can only be used in a server.")
        return
    if ctx.message.author.bot:
        return  # Ignore messages from other bots

    # Send a message to start the game
    create_message = await ctx.send("Game started! Please pick a colour.")

    # Add reactions to the message
    for emoji in colour_emojis:
        await create_message.add_reaction(emoji)

    # Setup game
    games.append(TrueColours(create_message.id, create_message.channel.id))


def gen_list_of_players(game: TrueColours):
    player_list_str = ""
    for player in game.players.keys():
        player_name = game.players[player]["name"]
        colour = game.players[player]["colour"]
        player_list_str += f"\n{player_name} - {colour}"
    return player_list_str


async def prompt_voting(game: TrueColours, round_num):
    for player in game.players.keys():
        user = game.players[player]["user"]
        dm_channel = await user.create_dm()

        msg = (
            f"\n**Round {round_num}/10**\n*{game.curr_qn}*{gen_list_of_players(game)}\n"
        )
        initial_msg = await dm_channel.send(msg)
        vote1_msg = await dm_channel.send("Vote 1")
        vote2_msg = await dm_channel.send("Vote 2")

        await initial_msg.add_reaction("☑️")
        for colour in game.colour_lookup.keys():
            if colour == game.players[player]["colour"]:
                continue

            await vote1_msg.add_reaction(colour)
            await vote2_msg.add_reaction(colour)

        game.vote_ids[vote1_msg.id] = [player, 1]
        game.vote_ids[vote2_msg.id] = [player, 2]


def cnt_check(reaction, user):
    return reaction.emoji == "⏩"


async def prompt_prediction(ctx, game: TrueColours, round_num):
    qn = game.curr_qn
    prompt_msg = await ctx.send(
        "How do you think your friends voted for you?\n💕 - Most\n💓 - Some\n💔 - None\n\n Click ⏩ when everyone is done"
    )

    game.prediction_id = prompt_msg.id

    for emoji in prediction_emojis.keys():
        await prompt_msg.add_reaction(emoji)
    await prompt_msg.add_reaction("⏩")

    try:
        # Wait for a reaction from the user
        reaction, user = await bot.wait_for(
            "reaction_add", timeout=1000.0, check=cnt_check
        )
    except TimeoutError:
        await ctx.send("Moving onto predictions")


def gen_round_results_msg(game: TrueColours):
    results = ""
    for player in game.players.keys():
        player_data = game.players[player]

        name = player_data["name"]
        votes = player_data["votes"]
        roundResult = player_data["roundResult"]

        results += f"\n{name} ({roundResult.upper()})- {votes} vote(s)"
    return results


async def run_game_round(ctx, game: TrueColours, round_num):
    game.reset_round()

    # Display prompt
    game.pick_qn()
    await ctx.send(f"\n**Round {round_num}/10:**\n*{game.curr_qn}*")

    # Vote
    await prompt_voting(game, round_num)
    game.tally_votes()
    game.determine_round_result()

    finish_voting_msg = await ctx.send("Click me when everyone is done")
    await finish_voting_msg.add_reaction("⏩")

    # Predictions
    try:
        # Wait for a reaction from the user
        reaction, user = await bot.wait_for(
            "reaction_add", timeout=1000.0, check=cnt_check
        )
    except TimeoutError:
        await ctx.send("Moving onto predictions")

    await finish_voting_msg.delete()
    await prompt_prediction(ctx, game, round_num)

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
async def startgame(ctx):
    if ctx.guild is None:
        await ctx.send("This command can only be used in a server.")
        return
    if ctx.message.author.bot:
        return  # Ignore messages from other bots

    game = getGameByChannel(ctx.message.channel.id)
    for i in range(10):
        await run_game_round(ctx, game, i + 1)

    msg = gen_scoreboard(game)
    await ctx.send(msg)


# Run the bot with your token
bot.run(TOKEN)
