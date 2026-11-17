"""Testes dos inimigos, dos modos de jogo e da escala de dificuldade."""
import unittest

import config
from characters import Player
from deck import Deck
from enemies import Boss, Bug, Enemy, RaceCondition, Trojan, spawn_enemy
from modes import MODES, get_mode


class TestModes(unittest.TestCase):
    def test_normal_mode_is_identity(self):
        m = MODES["normal"]
        self.assertEqual([m.difficulty_room(r) for r in (1, 5, 10)], [1, 5, 10])

    def test_short_mode_ends_at_full_difficulty(self):
        m = MODES["curto"]
        self.assertEqual(m.difficulty_room(1), 1)
        self.assertEqual(m.difficulty_room(5), 10)

    def test_unknown_mode_falls_back_to_normal(self):
        self.assertEqual(get_mode("xpto").key, "normal")


class TestEnemies(unittest.TestCase):
    def test_enemy_is_abstract(self):
        with self.assertRaises(TypeError):
            Enemy(1)

    def test_boss_is_last_room_in_each_mode(self):
        for mode in MODES.values():
            self.assertIsInstance(spawn_enemy(mode.rooms, mode), Boss)
            self.assertNotIsInstance(spawn_enemy(mode.rooms - 1, mode), Boss)

    def test_boss_hp_depends_on_mode(self):
        for mode in MODES.values():
            self.assertEqual(Boss(mode.rooms, mode).max_hp, mode.boss_hp)

    def test_difficulty_grows_with_room(self):
        self.assertLess(Bug(1).max_hp, Bug(9).max_hp)
        self.assertLess(Bug(1).damage, Bug(9).damage)

    def test_boss_hides_intent_but_keeps_history(self):
        boss, player = Boss(10), Player("T", Deck([]))
        boss.plan(1)
        self.assertIn("???", boss.describe_intent())
        boss.act(player)
        self.assertEqual(len(boss.history), 1)
        self.assertIn("Já fez", boss.describe_intent())

    def test_boss_pattern_heavy_attack_every_third_turn(self):
        boss = Boss(10)
        boss.plan(3)
        self.assertEqual(boss.intent.value, 2 * boss.damage)
        boss.plan(6)
        self.assertEqual(boss.intent.value, 2 * boss.damage)
        boss.plan(2)
        self.assertEqual(boss.intent.kind, "weaken")

    def test_race_condition_hits_twice(self):
        e = RaceCondition(1)
        e.plan(1)
        self.assertEqual((e.intent.kind, e.intent.hits), ("attack", 2))

    def test_trojan_exposes_player(self):
        t, p = Trojan(1), Player("T", Deck([]))
        t.plan(1)
        t.act(p)
        self.assertEqual(p.vulnerable, 2)

    def test_enrage_after_turn_limit(self):
        e = Bug(1)
        e.plan(1)
        base = e.intent.value
        e.plan(config.ENRAGE_TURN + 3)
        self.assertEqual(e.intent.value, base + 3)

    def test_enemy_defend_and_heal(self):
        from enemies import MemoryLeak
        m, p = MemoryLeak(5), Player("T", Deck([]))
        m.plan(1)                       # defende
        m.act(p)
        self.assertGreater(m.block, 0)
        m.take_damage(5 + m.block)
        hp = m.hp
        m.plan(3)                       # cura-se
        m.act(p)
        self.assertGreater(m.hp, hp)


if __name__ == "__main__":
    unittest.main()
