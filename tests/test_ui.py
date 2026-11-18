"""Testes das interfaces: contrato (R2), validação (R4) e ecrãs do RichUI."""
import contextlib
import io
import random
import unittest
from importlib.util import find_spec
from unittest import mock

from cards import REFACTOR_OPTION, make_card
from characters import Player
from deck import Deck
from enemies import Boss, Virus
from game import STARTER_DECK, Game
from hall_of_fame import HallOfFame, ScoreEntry
from modes import MODES
from relics import make_relic
from savegame import SaveGame
from simulate import NaiveBot
from ui import GameUI, QuitGame, RunUI, TextUI

HAS_RICH = find_spec("rich") is not None
if HAS_RICH:
    from rich.console import Console
    from ui_rich import RichUI, card_kind


def new_player():
    p = Player("Dino", Deck([make_card(n) for n in STARTER_DECK + ["Infinite Loop", "Sudo"]]))
    p.add_relic(make_relic("Overclock"))
    p.start_combat()
    p.start_turn(first_turn=True)
    return p


class TestContract(unittest.TestCase):
    def test_interfaces_are_abstract(self):
        for abstrata in (RunUI, GameUI):
            with self.assertRaises(TypeError):
                abstrata()

    def test_bots_implement_run_ui_but_not_the_menus(self):
        self.assertIsInstance(NaiveBot(), RunUI)
        self.assertNotIsInstance(NaiveBot(), GameUI)

    def test_text_ui_is_a_full_game_ui(self):
        self.assertIsInstance(TextUI(), GameUI)

    def test_eof_quits_instead_of_crashing(self):
        with mock.patch("builtins.input", side_effect=EOFError), mock.patch("builtins.print"):
            with self.assertRaises(QuitGame):
                TextUI().choose_purchase(True)


class TestTextUIValidation(unittest.TestCase):
    def _answers(self, *respostas):
        it = iter(respostas)
        return mock.patch("builtins.input", lambda _: next(it)), mock.patch("builtins.print")

    def test_invalid_answers_are_asked_again(self):
        a, b = self._answers("x", "9", "", "2")
        with a, b:
            self.assertEqual(TextUI().choose_purchase(False), "defense")

    def test_deck_option_only_exists_when_there_is_a_deck(self):
        a, b = self._answers("3", "1")
        with a, b:
            self.assertEqual(TextUI().choose_purchase(False), "attack")

    def test_reward_refactor_and_none(self):
        opcoes = [make_card("Firewall"), make_card("Segfault"), make_card("Sudo")]
        a, b = self._answers("4", "0", "1")
        with a, b:
            ui = TextUI()
            self.assertEqual(ui.choose_reward(opcoes, can_upgrade=True), REFACTOR_OPTION)
            self.assertIsNone(ui.choose_reward(opcoes, can_upgrade=True))
            self.assertIs(ui.choose_reward(opcoes), opcoes[0])

    def test_end_turn_returns_none(self):
        p = new_player()
        a, b = self._answers("0", "2")
        with a, b:
            ui = TextUI()
            self.assertIsNone(ui.choose_card(p, p.deck.hand))
            self.assertEqual(ui.choose_card(p, p.deck.hand), 1)

    def test_main_menu_hides_continue_without_save(self):
        self.assertNotIn("continue", [k for k, _ in TextUI._menu_options(False)])
        self.assertIn("continue", [k for k, _ in TextUI._menu_options(True)])


class RandomMixin:
    """Responde sempre com uma opção válida ao acaso: percorre todos os ecrãs."""
    def _ask(self, prompt, valid):
        return random.choice(valid)

    def _read(self, prompt):
        return "Aleatorio"


@unittest.skipUnless(HAS_RICH, "rich não está instalado")
class TestRichUI(unittest.TestCase):
    def setUp(self):
        self.out = io.StringIO()
        self.ui = RichUI()
        self.ui._console = Console(file=self.out, width=100, force_terminal=False)

    def text(self):
        return self.out.getvalue()

    def test_rich_is_a_text_ui(self):
        self.assertIsInstance(self.ui, TextUI)
        self.assertIsInstance(self.ui, GameUI)

    def test_message_is_not_parsed_as_markup(self):
        self.ui.message("[bold]x[/bold] [custo 1]")
        self.assertIn("[bold]x[/bold] [custo 1]", self.text())

    def test_card_kinds_have_a_name_and_risky_ones_are_marked(self):
        self.assertEqual(card_kind(make_card("Segfault"))[0], "Ataque")
        self.assertIn("risco", card_kind(make_card("Infinite Loop"))[0])
        self.assertIn("risco", card_kind(make_card("Sudo"))[0])
        self.assertEqual(card_kind(make_card("If/Else"))[0], "Defesa")
        for nome in ("Ctrl+Z", "Catch & Return", "Debug Mode", "Zombie Process",
                     "Garbage Collector"):
            self.assertNotEqual(card_kind(make_card(nome))[0], "Carta")

    def test_every_screen_renders(self):
        p, v = new_player(), Virus(6)
        v.plan(1)
        self.ui.show_state(p, v, 1)
        self.ui._show_menu(self.ui._menu_options(True))
        self.ui._show_purchase(True)
        self.ui._show_hand(p, p.deck.hand)
        self.ui._show_discard(p.deck.hand)
        self.ui._show_reward([make_card("Firewall")], True)
        self.ui._show_upgrades([(make_card("Segfault"), make_card("Segfault+"))])
        self.ui._show_relics([make_relic("Overvolt"), make_relic("Macro")])
        self.ui.show_help()
        self.ui.show_hall([("Normal", [ScoreEntry("Ana", 9, 10, True, "normal")]),
                           ("Rápido", [])], warning="teste")
        for esperado in ("Turno 1", "Mão", "Recompensa", "REFACTOR", "relíquia",
                         "Ana", "Ainda não há recordes", "Como jogar"):
            self.assertIn(esperado, self.text())

    def test_boss_intent_stays_hidden(self):
        p, boss = new_player(), Boss(10)
        boss.plan(1)
        boss.act(p)
        boss.plan(2)
        self.ui.show_state(p, boss, 2)
        self.assertIn("???", self.text())
        self.assertIn("Já fez", self.text())
        self.assertNotIn("ENFRAQUECER", self.text())

    def test_eof_quits(self):
        with mock.patch.object(self.ui._console, "input", side_effect=EOFError):
            with self.assertRaises(QuitGame):
                self.ui.ask_name()


class TestFullRunsThroughEveryScreen(unittest.TestCase):
    """Corre runs completas com um 'jogador' aleatório pelas interfaces reais."""

    def _play(self, ui):
        random.seed(5)
        for key in MODES:
            Game(ui=ui, hall=HallOfFame(None), save=SaveGame(None)).play_new(MODES[key])

    def test_text_ui(self):
        class RandomText(RandomMixin, TextUI):
            pass
        saida = io.StringIO()
        with contextlib.redirect_stdout(saida):
            self._play(RandomText())
        self.assertIn("Sala 1/", saida.getvalue())

    @unittest.skipUnless(HAS_RICH, "rich não está instalado")
    def test_rich_ui(self):
        class RandomRich(RandomMixin, RichUI):
            pass
        ui, saida = RandomRich(), io.StringIO()
        ui._console = Console(file=saida, width=100, force_terminal=False)
        self._play(ui)
        self.assertIn("Sala 1/", saida.getvalue())
        self.assertIn("Mão", saida.getvalue())


if __name__ == "__main__":
    unittest.main()
