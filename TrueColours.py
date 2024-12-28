from asyncio import Event
from typing import Union
import json
import os
import random

import discord

QNS_FILE = "questions.json"
QNS_FILE = os.path.abspath(QNS_FILE)
with open(QNS_FILE, "r") as f:
    QUESTIONS = json.load(f)["questions"]

class TrueColours:
    def __init__(self, join_msg_id, channel_id) -> None:
        self.channel_id = channel_id
        self.join_msg_id = join_msg_id
        self.wait_next = Event()
        self.skippers = set()
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
        self.questions = QUESTIONS

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
        self.skippers.clear()
        self.wait_next.clear()

        for player in self.players.keys():
            self.players[player]["lock_vote"] = False
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

    def add_player(self, player_id, player_name, colour, user: Union[discord.User, discord.Member]):
        self.players[player_id] = {
            "user": user,
            "name": player_name,
            "colour": colour,
            "points": 0,
            "lock_vote": False,
            "vote1": "",  # blue
            "vote2": "",  # pink
            "prediction": None,  # most, some, none
            "votes": 0,  # How many people voted for them,
            "roundResult": "",  # most, some, none
        }

        self.add_colour_lookup(player_id, colour)

    def add_point(self, player_id, points):
        self.players[player_id]["points"] += points

    def lock_vote(self, player_id):
        if self.players[player_id]["lock_vote"]:
            return False

        self.players[player_id]["lock_vote"] = True
        if all(map(lambda x: x["lock_vote"], self.players.values())):
            self.wait_next.set()

        return True

    def add_vote_1(self, player_id, vote):
        if self.players[player_id]["lock_vote"]:
            return False
        self.players[player_id]["vote1"] = vote
        return True

    def add_vote_2(self, player_id, vote):
        if self.players[player_id]["lock_vote"]:
            return False
        self.players[player_id]["vote2"] = vote
        return True
    
    def add_skipper(self, player_id):
        if player_id in self.skippers:
            return False

        self.skippers.add(player_id)
        if len(self.skippers) == len(self.players):
            self.wait_next.set()

        return True

    def add_prediction(self, player_id, prediction):
        if self.players[player_id]["lock_vote"]:
            return False
        self.players[player_id]["prediction"] = prediction
        return True

    def get_prediction(self, player_id):
        return self.players[player_id]["prediction"]

    async def tally_votes(self):
        """
        Count vote1 and vote2 from each player and tally into respective self.players "votes"
        """
        await self.wait_next.wait()
        if len(self.skippers) == len(self.players):
            self.wait_next.clear()
            return False

        for player in self.players.keys():
            try:
                votes = [self.players[player]["vote1"], self.players[player]["vote2"]]
                for vote in votes:
                    voted_player_id = self.colour_lookup[vote]
                    self.players[voted_player_id]["votes"] += 1
            except:
                continue
            finally:
                self.players[player]["lock_vote"] = False
        self.wait_next.clear()
        return True

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
