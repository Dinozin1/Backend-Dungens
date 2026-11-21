"""
game.py - A classe Game: menu principal e a run completa (o "ciclo grande").
"""
import random

import config
from battle import Battle
from cards import (MUTATE_OPTION, REFACTOR_OPTION, REWARD_POOL, make_card,
                   upgraded_spec)
from characters import Player
from deck import Deck
from enemies import spawn_enemy
from hall_of_fame import HallOfFame, ScoreEntry
from modes import MODES, get_mode
from mutations import MUTATION_FACTORIES, make_mutation
from relics import make_relic, random_relics
from replay import ReplayError, RoomRecorder
from rng import rng
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
                if estado is not None:
                    if not self._ui.confirm("Já tens uma run guardada. Começar uma nova "
                                            "apaga-a. Continuar?"):
                        continue
                    self._save.delete()
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
        """Retoma uma run gravada, mesmo a meio de um combate (ver replay.py)."""
        mode = get_mode(state.mode_key)
        self._ui.message(f"\nA continuar a run de {state.name} "
                         f"({mode.label}), sala {state.next_room}.")
        try:
            self._run(self._rebuild_player(state), mode, state.next_room,
                      state.total_turns, state.seed, state.log)
        except ReplayError:
            # registo incoerente (ficheiro mexido): a sala recomeça do princípio
            self._ui.message("O registo da sala estava inconsistente: a sala recomeça.")
            self._run(self._rebuild_player(state), mode, state.next_room,
                      state.total_turns)

    @staticmethod
    def _rebuild_player(state):
        """Reconstrói o jogador como estava no INÍCIO da sala gravada."""
        player = Player(state.name, Deck([make_card(n) for n in state.cards]))
        player.restore_hp(state.hp)
        for nome in state.relics:
            player.add_relic(make_relic(nome))
        return player

    def _run(self, player, mode, start_room, total_turns, seed=None, log=()):
        """
        O ciclo grande: uma sala de cada vez. No início de cada sala grava-se o
        estado e a semente; durante a sala, o RoomRecorder grava as respostas.
        (seed e log só vêm preenchidos ao retomar uma sala a meio.)
        """
        rooms_cleared, won = start_room - 1, False
        for room in range(start_room, mode.rooms + 1):
            if seed is None:
                seed = random.getrandbits(32)
            if not self._save.save(player, mode, room, total_turns, seed, log):
                self._ui.message("(Não foi possível gravar a run.)")
            recorder = RoomRecorder(self._ui, log, self._save.update_log)
            rng.seed(seed)                       # a sala repete-se igual com a mesma semente
            victory, turns = self._play_room(player, mode, room, recorder)
            total_turns += turns
            seed, log = None, ()
            if not victory:
                break
            rooms_cleared = room
            if room == mode.rooms:
                won = True
                break
        self._finish_run(player, mode, rooms_cleared, total_turns, won)

    def _play_room(self, player, mode, room, ui):
        """Uma sala: combate e, se ganhou (e não é a última), cura, recompensa e relíquia."""
        battle = Battle(player, spawn_enemy(room, mode), ui)
        victory = battle.run()
        if victory and room < mode.rooms:
            curado = player.heal_after_combat()
            ui.message(f"Recuperas {curado} de vida. ({player.hp}/{player.max_hp})")
            self._give_reward(player, ui)
            if room in mode.relic_rooms:
                self._give_relic(player, ui)
        return victory, battle.turns

    def _give_reward(self, player, ui=None):
        """
        Fim do combate: 1 carta entre 3 para juntar ao baralho, OU um REFACTOR
        (melhorar uma carta que já tens), OU uma MUTAÇÃO (sorteada uma vez por
        recompensa: voltar atrás no menu não a muda), OU nada.
        """
        ui = ui or self._ui
        opcoes = [make_card(n) for n in
                  rng.sample(REWARD_POOL, config.REWARD_CHOICES)]
        mutacao = make_mutation(rng.choice(list(MUTATION_FACTORIES)))
        while True:
            nomes = player.deck.upgradable_names()
            alvos = player.deck.mutable_names()
            escolha = ui.choose_reward(opcoes, can_upgrade=bool(nomes),
                                       mutation=mutacao if alvos else None)
            if escolha == REFACTOR_OPTION:
                pares = [(make_card(n), make_card(upgraded_spec(n))) for n in nomes]
                indice = ui.choose_upgrade(pares)
                if indice is None:                 # voltou atrás: mostra o menu outra vez
                    continue
                nova = player.deck.upgrade_card(nomes[indice])
                ui.message(f"REFACTOR: {pares[indice][0].display_name} "
                           f"passou a {nova.display_name}!")
            elif escolha == MUTATE_OPTION:
                pares = [(make_card(n), self._mutated(n, mutacao)) for n in alvos]
                indice = ui.choose_mutation_target(mutacao, pares)
                if indice is None:
                    continue
                carta = player.deck.mutate_card(alvos[indice], make_mutation(mutacao.name))
                ui.message(f"MUTAÇÃO: {carta.name} ficou {mutacao.name}!")
            elif escolha is not None:
                player.deck.add_card(escolha)
                ui.message(f"{escolha.display_name} entrou no baralho "
                           f"({len(player.deck)} cartas).")
            return

    @staticmethod
    def _mutated(name, mutation):
        """Pré-visualização: a carta 'name' já com a mutação."""
        carta = make_card(name)
        carta.mutate(make_mutation(mutation.name))
        return carta

    def _give_relic(self, player, ui=None):
        """Oferece 2 relíquias que ainda não tens (se houver) e escolhe 1."""
        ui = ui or self._ui
        opcoes = random_relics([r.name for r in player.relics], 2)
        if not opcoes:
            return
        escolhida = ui.choose_relic(opcoes)
        player.add_relic(escolhida)
        ui.message(f"Relíquia obtida: {escolhida.name}!")

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
