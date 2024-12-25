import json
import os
import random

import discord


class TrueColours:
    def __init__(self, join_msg, channel_id) -> None:
        self.channel_id = channel_id
        self.join_msg_id = join_msg
        self.players = {}
        self.curr_qn = ""
        self.questions = []
        self.asked_qns = []
        self.point_results = {}
        self.colour_lookup = {}  # lookup table for colour to playerid
        self.vote_ids = {}
        self.prediction_id = ""

        self.load_qn_bank()

    def load_qn_bank(self):
        qn_json = "questions.json"
        qn_json = os.path.abspath(qn_json)
        with open(qn_json, "r") as f:
            data = json.load(f)
        self.questions = data["questions"]

    def start_game(self):
        # Reset players
        self.players = {}
        self.colour_lookup = {}

    def reset_round(self):
        """
        Call this at the start/end of each round/question
        Resets round specific values
        """
        self.vote_ids = {}
        self.prediction_id = ""

        for player in self.players.keys():
            self.players[player]["vote1"] = ""
            self.players[player]["vote2"] = ""
            self.players[player]["prediction"] = ""
            self.players[player]["votes"] = 0
            self.players[player]["roundResult"] = ""

    def pick_qn(self):
        qn = random.choice(self.questions)
        self.curr_qn = qn
        self.prevent_repeat_qn(qn)  # Prevent qn repeating

    def prevent_repeat_qn(self, qn):
        """
        prevent repeat qns
        """
        self.asked_qns.append(qn)
        self.questions.remove(qn)

    def add_colour_lookup(self, player_id, colour):
        self.colour_lookup[colour] = player_id

    def add_player(self, player_id, player_name, colour, user: discord.User):
        self.players[player_id] = {
            "user": user,
            "name": player_name,
            "colour": colour,
            "points": 0,
            "vote1": "",  # blue
            "vote2": "",  # pink
            "prediction": None,  # most, some, none
            "votes": 0,  # How many people voted for them,
            "roundResult": "",  # most, some, none
        }

        self.add_colour_lookup(player_id, colour)

    def add_point(self, player_id, points):
        self.players[player_id]["points"] += points

    def add_vote_1(self, player_id, vote):
        self.players[player_id]["vote1"] = vote

    def add_vote_2(self, player_id, vote):
        self.players[player_id]["vote2"] = vote

    def add_prediction(self, player_id, prediction):
        self.players[player_id]["prediction"] = prediction

    def tally_votes(self):
        """
        Count vote1 and vote2 from each player and tally into respective self.players "votes"
        """
        for player in self.players.keys():
            try:
                votes = [self.players[player]["vote1"], self.players[player]["vote2"]]
                voted_player_id = self.colour_lookup[vote]
                self.players[voted_player_id]["votes"] += 1
            except:
                continue

    def determine_round_result(self):
        """
        Assign status of 'most', 'some' and 'none' to players 'roundResult' according to 'votes' score
        """
        max_votes = max(self.players.values(), key=lambda x: x["votes"])["votes"]

        for player in self.players.keys():
            votes = self.players[player]["votes"]

            if votes == 0:
                self.players[player]["roundResult"] = "none"
            elif votes == max_votes:
                self.players[player]["roundResult"] = "most"
            else:
                self.players[player]["roundResult"] = "some"

    def assign_points(self):
        """
        compare voting results and assign points according to player
        """
        for player in self.players.keys():
            prediction = self.players[player]["prediction"]
            result = self.players[player]["roundResult"]

            if result != prediction:  # no points
                self.add_point(player, 0)
                continue

            if result == "some":  # 1 point
                self.add_point(player, 1)
                continue

            self.add_point(player, 3)  # 3 points for "most" and "none"

    def get_winner(self):
        """
        return userid of winning player(s) and their score
        """
        points = max(self.players.values(), key=lambda x: x["points"])["points"]
        userid = [
            userid
            for userid, player_data in self.players.items()
            if player_data["points"] == points
        ]

        return userid, points
