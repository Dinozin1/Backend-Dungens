"""Testes de robustez (R4): filtro de nomes, escrita atómica e aviso de run guardada."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fileutil import write_text_atomic
from game import Game
from hall_of_fame import HallOfFame, ScoreEntry
from modes import MODES
from names import is_acceptable_name
from savegame import SaveGame
from simulate import NaiveBot
from ui import TextUI


class TestNames(unittest.TestCase):
    def test_normal_names_pass(self):
        for nome in ("Dino", "Ana Sofia", "Computador", "Zé_99", "Júlia"):
            self.assertTrue(is_acceptable_name(nome), nome)

    def test_offensive_names_are_blocked_even_disguised(self):
        for nome in ("Nigga", "FUCK", "p.u.t.4", "Merda123", "xxfúckxx", "  "):
            self.assertFalse(is_acceptable_name(nome), nome)

    def test_non_strings_rejected(self):
        self.assertFalse(is_acceptable_name(None))
        self.assertFalse(is_acceptable_name(5))

    def test_ask_name_repeats_until_valid(self):
        respostas = iter(["", "Nigga", "Dino"])
        with mock.patch("builtins.input", lambda _: next(respostas)), \
                mock.patch("builtins.print"):
            self.assertEqual(TextUI().ask_name(), "Dino")

    def test_hall_of_fame_skips_offensive_or_odd_entries_on_load(self):
        with tempfile.TemporaryDirectory() as d:
            caminho = Path(d) / "scores.json"
            bom = {"name": "Ana", "score": 10, "rooms": 1, "won": False, "mode": "normal"}
            dados = [bom, dict(bom, name="Nigga"), dict(bom, name="A" * 40),
                     dict(bom, score=True), dict(bom, rooms=True)]
            caminho.write_text(json.dumps(dados), encoding="utf-8")
            self.assertEqual([e.name for e in HallOfFame(caminho).top()], ["Ana"])


class TestAtomicWrite(unittest.TestCase):
    def test_write_replaces_content_and_leaves_no_temp_file(self):
        with tempfile.TemporaryDirectory() as d:
            caminho = Path(d) / "x.json"
            write_text_atomic(caminho, "um")
            write_text_atomic(caminho, "dois")
            self.assertEqual(caminho.read_text(encoding="utf-8"), "dois")
            self.assertEqual([p.name for p in Path(d).iterdir()], ["x.json"])

    def test_failed_write_keeps_the_old_file(self):
        with tempfile.TemporaryDirectory() as d:
            caminho = Path(d) / "x.json"
            write_text_atomic(caminho, "antigo")
            with mock.patch("fileutil.os.replace", side_effect=OSError):
                with self.assertRaises(OSError):
                    write_text_atomic(caminho, "novo")
            self.assertEqual(caminho.read_text(encoding="utf-8"), "antigo")
            self.assertEqual([p.name for p in Path(d).iterdir()], ["x.json"])

    def test_hall_of_fame_save_reports_failure_without_crashing(self):
        with tempfile.TemporaryDirectory() as d:
            h = HallOfFame(Path(d) / "scores.json")
            h.add(ScoreEntry("Ana", 1, 1, False, "normal"))
            with mock.patch("fileutil.os.replace", side_effect=OSError):
                self.assertFalse(h.save())


class TestNewRunWarning(unittest.TestCase):
    def _game(self, d, resposta):
        save = SaveGame(Path(d) / "save.json")
        (Path(d) / "save.json").write_text(json.dumps({
            "name": "Dino", "hp": 40, "cards": ["If/Else"], "relics": [],
            "mode": "normal", "next_room": 3, "total_turns": 9}), encoding="utf-8")

        class UI(NaiveBot):
            escolhas = iter(["normal", "quit"])
            perguntas = []
            def main_menu(self, has_save=False): return next(UI.escolhas)
            def confirm(self, question):
                UI.perguntas.append(question)
                return resposta
        game = Game(ui=UI(), hall=HallOfFame(None), save=save)
        game.play_new = mock.Mock()
        return game, save, UI

    def test_declining_keeps_the_saved_run(self):
        with tempfile.TemporaryDirectory() as d:
            game, save, UI = self._game(d, False)
            game.menu()
            game.play_new.assert_not_called()
            self.assertEqual(len(UI.perguntas), 1)
            self.assertIsNotNone(save.load())

    def test_accepting_deletes_the_save_and_starts(self):
        with tempfile.TemporaryDirectory() as d:
            game, save, UI = self._game(d, True)
            game.menu()
            game.play_new.assert_called_once_with(MODES["normal"])
            self.assertIsNone(save.load())


if __name__ == "__main__":
    unittest.main()
