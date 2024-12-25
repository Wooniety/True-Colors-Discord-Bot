from TrueColours import TrueColours

game = TrueColours()

# Resets all players
game.start_game()

game.add_player(1, "henggy", "green")
game.add_player(2, "david", "red")
game.add_player(3, "ch", "blue")

# A round
game.reset_round()  # always reset round each qn

# get qn string
print(game.pick_qn())

# players do voting
game.add_vote_1(1, "blue")
game.add_vote_2(1, "blue")
game.add_vote_1(2, "blue")
game.add_vote_2(2, "blue")
game.add_vote_1(3, "red")
game.add_vote_2(3, "red")

# players do predictions
game.add_prediction(1, "none")
game.add_prediction(2, "some")
game.add_prediction(3, "most")

# server side does vote tallying and score counting IN THIS ORDER
game.tally_votes()
game.determine_round_result()
game.assign_points()

# if you want to see round results, all the info is in the players dict
for player in game.players.keys():
    player_data = game.players[player]

    name = player_data["name"]
    votes = player_data["votes"]
    roundResult = player_data["roundResult"]

    results = f"{name} ({roundResult.upper()})- {votes} vote(s)"
    print(results)

# End of game

# Scoreboard
print("\nScoreboard")
for player in game.players.keys():
    player_data = game.players[player]

    name = player_data["name"]
    points = player_data["points"]

    print(f"{name} - {points}")

(
    winner_id,
    winner_score,
) = game.get_winner()  # Returns list of winners and the score they got
winners = []
for id in winner_id:
    winners.append(game.players[id]["name"])
winner_string = " and ".join(winners)

print(f"\nThe winner is... {winner_string} with a score of {winner_score}!")
