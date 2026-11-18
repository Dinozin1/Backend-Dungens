"""Testes de integração: combates e runs completas com bots (sem consola)."""
import random
import tempfile
import unittest
from pathlib import Path

from battle import Battle
from cards import make_card
from characters import Player
from deck import Deck
from enemies import Bug
from game import Game
from hall_of_fame import HallOfFame
from modes import MODES
from savegame import SaveGame
from simulate import NaiveBot, SmartBot
from ui import QuitGame


class Stop(Exception):
    """Para o combate no meio, depois de recolher o que interessa."""


class RecordingUI(NaiveBot):
    """UI que regista as mensagens e tenta jogar uma carta que não pode pagar."""
    def __init__(self):
        self.messages, self.calls = [], 0

    def message(self, text):
        self.messages.append(text)

    def choose_purchase(self, can_draw_deck):
        return "deck"

    def choose_card(self, player, hand):
        self.calls += 1
        if self.calls > 1:
            raise Stop
        return 0


class TestBattle(unittest.TestCase):
    def test_insufficient_energy_is_refused(self):
        p = Player("T", Deck([make_card("Firewall") for _ in range(8)]))   # custo 4
        ui = RecordingUI()
        with self.assertRaises(Stop):
            Battle(p, Bug(1), ui).run()
        self.assertTrue(any("Energia insuficiente" in m for m in ui.messages))
        self.assertEqual(p.energy, 3)             # nada foi gasto

    def test_deck_purchase_refused_when_deck_empty(self):
        class OneCard(RecordingUI):
            asked = 0
            def choose_purchase(self, can_draw_deck):
                OneCard.asked += 1
                return "deck" if OneCard.asked == 1 else "attack"
        p = Player("T", Deck([make_card("If/Else") for _ in range(5)]))    # só 5 cartas
        ui = OneCard()
        with self.assertRaises(Stop):
            Battle(p, Bug(1), ui).run()
        self.assertTrue(any("Já não tens cartas" in m for m in ui.messages))


class TestBattleRules(unittest.TestCase):
    def test_rate_limiter_lowers_the_intent_of_the_current_turn(self):
        """Regressão: a Fraqueza tem de reduzir já o ataque planeado neste turno."""
        class Spy(NaiveBot):
            def __init__(self): self.intents, self.enemy = [], None
            def show_state(self, player, enemy, turn): self.enemy = enemy
            def choose_purchase(self, can_draw_deck): return "attack"
            def choose_card(self, player, hand):
                self.intents.append(self.enemy.intent.value)
                if len(self.intents) > 2:
                    raise Stop
                return next((i for i, c in enumerate(hand) if c.name == "Rate Limiter"), None)
        p = Player("T", Deck([make_card("Rate Limiter") for _ in range(10)]))
        ui = Spy()
        with self.assertRaises(Stop):
            Battle(p, Bug(9), ui).run()
        self.assertLess(ui.intents[1], ui.intents[0])       # 8 -> 6

    def test_player_wins_only_if_still_alive(self):
        """Regressão: se o jogador morre, nunca conta como vitória."""
        class Hopeless(NaiveBot):
            def choose_purchase(self, can_draw_deck): return "defense"
            def choose_card(self, player, hand): return None
        p = Player("T", Deck([make_card("If/Else") for _ in range(10)]))
        bug = Bug(10)
        p.take_damage(p.hp - 1)
        self.assertFalse(Battle(p, bug, Hopeless()).run())
        self.assertFalse(p.is_alive)


class TestRuns(unittest.TestCase):
    def setUp(self):
        random.seed(11)

    def _run(self, mode_key):
        hall = HallOfFame(None)
        Game(ui=SmartBot(), hall=hall, save=SaveGame(None)).play_new(MODES[mode_key])
        return hall.entries[0]

    def test_full_runs_finish_in_both_modes(self):
        for key, mode in MODES.items():
            for _ in range(15):
                e = self._run(key)
                self.assertTrue(0 <= e.rooms <= mode.rooms)
                self.assertEqual(e.mode, key)
                self.assertEqual(e.won, e.rooms == mode.rooms)

    def test_score_formula(self):
        self.assertEqual(Game.compute_score(10, 30, 40, True), 1000 + 60 + 500 - 80)
        self.assertEqual(Game.compute_score(0, 0, 999, False), 0)

    def test_quit_then_continue_run(self):
        with tempfile.TemporaryDirectory() as d:
            save = SaveGame(Path(d) / "save.json")

            class QuitAtRoom2(SmartBot):
                def choose_purchase(self, can_draw_deck):
                    if self.enemy.room == 2:
                        raise QuitGame
                    return super().choose_purchase(can_draw_deck)

            hall = HallOfFame(None)
            with self.assertRaises(QuitGame):
                Game(ui=QuitAtRoom2(), hall=hall, save=save).play_new(MODES["normal"])
            estado = save.load()
            self.assertEqual(estado.next_room, 2)      # gravou depois da sala 1

            Game(ui=SmartBot(), hall=hall, save=save).continue_run(estado)
            self.assertIsNone(save.load())             # run acabou: gravação apagada
            self.assertEqual(len(hall.entries), 1)
            self.assertGreaterEqual(hall.entries[0].rooms, 1)


if __name__ == "__main__":
    unittest.main()
