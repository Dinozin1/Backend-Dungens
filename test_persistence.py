"""Testes dos ficheiros: recordes e run gravada (R3 e R4)."""
import json
import tempfile
import unittest
from pathlib import Path

from cards import make_card
from characters import Player
from deck import Deck
from hall_of_fame import HallOfFame, ScoreEntry
from modes import MODES
from relics import make_relic
from savegame import SaveGame


class TestHallOfFame(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.path = Path(self._tmp.name) / "scores.json"

    def tearDown(self):
        self._tmp.cleanup()

    def test_missing_file_is_fine(self):
        h = HallOfFame(self.path)
        self.assertEqual((h.top(), h.warning), ([], ""))

    def test_roundtrip(self):
        h = HallOfFame(self.path)
        h.add(ScoreEntry("Ana", 300, 5, False, "curto"))
        self.assertTrue(h.save())
        e = HallOfFame(self.path).top()[0]
        self.assertEqual((e.name, e.score, e.mode), ("Ana", 300, "curto"))

    def test_corrupted_file_is_backed_up_and_ignored(self):
        self.path.write_text("{lixo", encoding="utf-8")
        h = HallOfFame(self.path)
        self.assertEqual(h.top(), [])
        self.assertTrue(h.warning)
        self.assertTrue(self.path.with_suffix(".bak").exists())

    def test_invalid_entries_skipped_old_entries_default_to_normal(self):
        dados = [{"name": "Velho", "score": 10, "rooms": 1, "won": False},
                 {"name": 5, "score": "x"}, "lixo"]
        self.path.write_text(json.dumps(dados), encoding="utf-8")
        h = HallOfFame(self.path)
        self.assertEqual(len(h.top()), 1)
        self.assertEqual(h.top()[0].mode, "normal")

    def test_top_sorted_and_filtered_by_mode(self):
        h = HallOfFame(None)
        h.add(ScoreEntry("A", 100, 3, False, "normal"))
        h.add(ScoreEntry("B", 900, 5, True, "curto"))
        h.add(ScoreEntry("C", 500, 5, False, "normal"))
        self.assertEqual([e.name for e in h.top()], ["B", "C", "A"])
        self.assertEqual([e.name for e in h.top(mode="normal")], ["C", "A"])


class TestSaveGame(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.path = Path(self._tmp.name) / "save.json"
        self.save = SaveGame(self.path)

    def tearDown(self):
        self._tmp.cleanup()

    def _write(self, **mudancas):
        dados = {"name": "Dino", "hp": 40, "cards": ['Print("Hit")', "If/Else"],
                 "relics": ["Overclock"], "mode": "normal", "next_room": 3,
                 "total_turns": 9}
        dados.update(mudancas)
        self.path.write_text(json.dumps(dados), encoding="utf-8")

    def test_roundtrip(self):
        p = Player("Dino", Deck([make_card("Firewall"), make_card("If/Else")]))
        p.add_relic(make_relic("Macro"))
        p.take_damage(15)
        self.assertTrue(self.save.save(p, MODES["curto"], 3, 12))
        s = self.save.load()
        self.assertEqual((s.name, s.hp, s.mode_key, s.next_room, s.total_turns),
                         ("Dino", 45, "curto", 3, 12))
        self.assertEqual((s.cards, s.relics), (["Firewall", "If/Else"], ["Macro"]))

    def test_missing_file_gives_none(self):
        self.assertIsNone(self.save.load())

    def test_valid_file_loads(self):
        self._write()
        self.assertEqual(self.save.load().next_room, 3)

    def test_corrupted_file_gives_none(self):
        self.path.write_text("{lixo", encoding="utf-8")
        self.assertIsNone(self.save.load())

    def test_tampered_files_are_rejected(self):
        for mau in ({"cards": ["Carta Inventada"]}, {"relics": ["Falsa"]},
                    {"mode": "impossivel"}, {"next_room": 99}, {"next_room": 0},
                    {"hp": 0}, {"hp": "muito"}, {"cards": []}, {"name": ""},
                    {"total_turns": -1}):
            self._write(**mau)
            self.assertIsNone(self.save.load(), mau)

    def test_delete(self):
        self._write()
        self.save.delete()
        self.assertIsNone(self.save.load())
        self.save.delete()           # apagar duas vezes não rebenta

    def test_disabled_save_does_nothing(self):
        s = SaveGame(None)
        self.assertIsNone(s.load())
        s.delete()


if __name__ == "__main__":
    unittest.main()
