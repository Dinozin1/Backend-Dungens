"""
game.py - A classe Game: menu principal e a run completa (o "ciclo grande").
"""
import random

import config
from battle import Battle
from cards import REWARD_POOL, make_card
from characters import Player
from deck import Deck
from enemies import spawn_enemy
from hall_of_fame import HallOfFame, ScoreEntry
from ui import TextUI

# Baralho inicial (secção 5): 4x Print("Hit"), 4x If/Else e 2 à escolha da equipa.
STARTER_DECK = (['Print("Hit")'] * 4 + ["If/Else"] * 4 + ["Segfault", "Try/Catch"])


class Game:
    def __init__(self, ui=None, hall=None):
        self._ui = ui or TextUI()
        self._hall = hall or HallOfFame()

    def menu(self):
        """Menu principal. Corre até o jogador escolher Sair."""
        while True:
            escolha = self._ui.main_menu()
            if escolha == "1":
                self.play_run()
            elif escolha == "2":
                self._ui.show_hall(self._hall.top(), self._hall.warning)
            elif escolha == "3":
                self._ui.show_help()
            else:
                self._ui.message("Até à próxima, programador!")
                return

    def play_run(self):
        """Uma run: até 10 salas, com recompensa entre combates."""
        nome = self._ui.ask_name()
        player = Player(nome, Deck([make_card(n) for n in STARTER_DECK]))
        rooms_cleared, total_turns, won = 0, 0, False

        for room in range(1, config.TOTAL_ROOMS + 1):
            battle = Battle(player, spawn_enemy(room), self._ui)
            victory = battle.run()
            total_turns += battle.turns
            if not victory:
                break
            rooms_cleared += 1
            if room == config.TOTAL_ROOMS:
                won = True
                break
            curado = player.heal_after_combat()
            self._ui.message(f"Recuperas {curado} de vida. ({player.hp}/{player.max_hp})")
            self._give_reward(player)

        self._finish_run(player, rooms_cleared, total_turns, won)

    def _give_reward(self, player):
        """1 carta entre 3 (sem repetir) para juntar ao baralho."""
        opcoes = [make_card(n) for n in
                  random.sample(REWARD_POOL, config.REWARD_CHOICES)]
        escolhida = self._ui.choose_reward(opcoes)
        if escolhida is not None:
            player.deck.add_card(escolhida)
            self._ui.message(f"{escolhida.name} entrou no baralho "
                             f"({len(player.deck)} cartas).")

    @staticmethod
    def compute_score(rooms_cleared, hp, total_turns, won):
        """Pontuação: salas e vida contam; bónus de vitória; turnos custam um pouco."""
        score = rooms_cleared * 100 + hp * 2 + (500 if won else 0) - total_turns * 2
        return max(0, score)

    def _finish_run(self, player, rooms_cleared, total_turns, won):
        score = self.compute_score(rooms_cleared, player.hp, total_turns, won)
        titulo = "VITÓRIA! O sistema está limpo!" if won else "FIM DA RUN"
        self._ui.message(f"\n=== {titulo} ===\nSalas limpas: {rooms_cleared}/"
                         f"{config.TOTAL_ROOMS}  |  Pontuação: {score}")
        self._hall.add(ScoreEntry(player.name, score, rooms_cleared, won))
        if not self._hall.save():
            self._ui.message("(Não foi possível gravar os recordes no ficheiro.)")
