"""
game.py - A classe Game: menu principal e a run completa (o "ciclo grande").
"""
import random

import config
from battle import Battle
from cards import REFACTOR_OPTION, REWARD_POOL, UPGRADES, make_card
from characters import Player
from deck import Deck
from enemies import spawn_enemy
from hall_of_fame import HallOfFame, ScoreEntry
from modes import MODES, get_mode
from relics import make_relic, random_relics
from savegame import SaveGame
from ui import TextUI

# Baralho inicial (secção 5): 4x Print("Hit"), 4x If/Else e 2 à escolha da equipa.
STARTER_DECK = (['Print("Hit")'] * 4 + ["If/Else"] * 4 + ["Segfault", "Try/Catch"])


class Game:
    def __init__(self, ui=None, hall=None, save=None):
        self._ui = ui or TextUI()
        self._hall = hall or HallOfFame()
        self._save = save or SaveGame()

    # ---------------- menu ----------------
    def menu(self):
        """Menu principal. Corre até o jogador escolher Sair."""
        while True:
            estado = self._save.load()
            escolha = self._ui.main_menu(has_save=estado is not None)
            if escolha in MODES:
                self.play_new(MODES[escolha])
            elif escolha == "continue":
                self.continue_run(estado)
            elif escolha == "hall":
                tabelas = [(m.label, self._hall.top(10, m.key)) for m in MODES.values()]
                self._ui.show_hall(tabelas, self._hall.warning)
            elif escolha == "help":
                self._ui.show_help()
            else:
                self._ui.message("Até à próxima, programador!")
                return

    # ---------------- runs ----------------
    def play_new(self, mode):
        """Começa uma run nova no modo escolhido."""
        nome = self._ui.ask_name()
        player = Player(nome, Deck([make_card(n) for n in STARTER_DECK]))
        self._run(player, mode, start_room=1, total_turns=0)

    def continue_run(self, state):
        """Retoma uma run gravada (reconstrói o jogador a partir do ficheiro)."""
        mode = get_mode(state.mode_key)
        player = Player(state.name, Deck([make_card(n) for n in state.cards]))
        player.restore_hp(state.hp)
        for nome in state.relics:
            player.add_relic(make_relic(nome))
        self._ui.message(f"\nA continuar a run de {state.name} "
                         f"({mode.label}), sala {state.next_room}.")
        self._run(player, mode, state.next_room, state.total_turns)

    def _run(self, player, mode, start_room, total_turns):
        """O ciclo grande: uma sala de cada vez, com recompensas pelo caminho."""
        rooms_cleared, won = start_room - 1, False
        for room in range(start_room, mode.rooms + 1):
            battle = Battle(player, spawn_enemy(room, mode), self._ui)
            victory = battle.run()
            total_turns += battle.turns
            if not victory:
                break
            rooms_cleared = room
            if room == mode.rooms:
                won = True
                break
            curado = player.heal_after_combat()
            self._ui.message(f"Recuperas {curado} de vida. ({player.hp}/{player.max_hp})")
            self._give_reward(player)
            if room in mode.relic_rooms:
                self._give_relic(player)
            if not self._save.save(player, mode, room + 1, total_turns):
                self._ui.message("(Não foi possível gravar a run.)")
        self._finish_run(player, mode, rooms_cleared, total_turns, won)

    def _give_reward(self, player):
        """
        Fim do combate: 1 carta entre 3 para juntar ao baralho, OU um REFACTOR
        (melhorar uma carta que já tens), OU nada.
        """
        opcoes = [make_card(n) for n in
                  random.sample(REWARD_POOL, config.REWARD_CHOICES)]
        while True:
            nomes = player.deck.upgradable_names()
            escolha = self._ui.choose_reward(opcoes, can_upgrade=bool(nomes))
            if escolha == REFACTOR_OPTION:
                pares = [(make_card(n), make_card(UPGRADES[n])) for n in nomes]
                indice = self._ui.choose_upgrade(pares)
                if indice is None:                 # voltou atrás: mostra o menu outra vez
                    continue
                nova = player.deck.upgrade_card(nomes[indice])
                self._ui.message(f"REFACTOR: {nomes[indice]} passou a {nova.name}!")
            elif escolha is not None:
                player.deck.add_card(escolha)
                self._ui.message(f"{escolha.name} entrou no baralho "
                                 f"({len(player.deck)} cartas).")
            return

    def _give_relic(self, player):
        """Oferece 2 relíquias que ainda não tens (se houver) e escolhe 1."""
        opcoes = random_relics([r.name for r in player.relics], 2)
        if not opcoes:
            return
        escolhida = self._ui.choose_relic(opcoes)
        player.add_relic(escolhida)
        self._ui.message(f"Relíquia obtida: {escolhida.name}!")

    @staticmethod
    def compute_score(rooms_cleared, hp, total_turns, won):
        """Pontuação: salas e vida contam; bónus de vitória; turnos custam um pouco."""
        score = rooms_cleared * 100 + hp * 2 + (500 if won else 0) - total_turns * 2
        return max(0, score)

    def _finish_run(self, player, mode, rooms_cleared, total_turns, won):
        self._save.delete()          # a run acabou: já não há nada para continuar
        score = self.compute_score(rooms_cleared, player.hp, total_turns, won)
        titulo = "VITÓRIA! O sistema está limpo!" if won else "FIM DA RUN"
        self._ui.message(f"\n=== {titulo} ===\nModo: {mode.label}  |  Salas limpas: "
                         f"{rooms_cleared}/{mode.rooms}  |  Pontuação: {score}")
        self._hall.add(ScoreEntry(player.name, score, rooms_cleared, won, mode.key))
        if not self._hall.save():
            self._ui.message("(Não foi possível gravar os recordes no ficheiro.)")
