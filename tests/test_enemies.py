"""Testes dos inimigos, dos modos de jogo e da escala de dificuldade."""
import unittest

import config
from characters import Player
from deck import Deck
from cards import SPAM, make_card
from enemies import (Adware, Boss, Bug, Enemy, Intent, Keylogger, MemoryLeak,
                     RaceCondition, Ransomware, Trojan, Virus, Worm, spawn_enemy)
from modes import MODES, get_mode
from rng import rng


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


class TestIntents(unittest.TestCase):
    def test_intent_is_abstract(self):
        with self.assertRaises(TypeError):
            Intent(3)

    def test_every_intent_describes_itself(self):
        for classe in Intent.__subclasses__():
            self.assertTrue(classe(3).describe())

    def test_dead_enemy_does_not_keep_attacking(self):
        """Regressão: se o parry mata o inimigo no 1.º golpe, o 2.º não acontece."""
        p, race = Player("T", Deck([])), RaceCondition(1)
        race.take_damage(race.hp - 3)
        race.plan(1)
        p.set_parry(8)
        mensagens = race.act(p)
        self.assertFalse(race.is_alive)
        self.assertEqual(len(mensagens), 1)
        self.assertEqual(p.hp, p.max_hp)


class TestNewEnemies(unittest.TestCase):
    def setUp(self):
        self.p = Player("T", Deck([make_card("If/Else") for _ in range(10)]))
        self.p.start_combat()

    def test_worm_hits_three_times_and_defends_every_fourth_turn(self):
        w = Worm(5)
        w.plan(1)
        self.assertEqual((w.intent.kind, w.intent.hits), ("attack", 3))
        self.assertEqual(len(w.act(self.p)), 3)
        w.plan(4)
        self.assertEqual(w.intent.kind, "defend")

    def test_keylogger_poison_ignores_block_and_ticks_at_end_of_turn(self):
        k = Keylogger(6)
        k.plan(1)
        self.assertEqual(k.intent.kind, "poison")
        k.act(self.p)
        self.assertEqual(self.p.poison, 3)
        self.p.gain_block(50)
        self.assertIn("veneno", self.p.end_turn())
        self.assertEqual((self.p.hp, self.p.block), (self.p.max_hp - 3, 50))
        k.plan(2)
        self.assertEqual(k.intent.kind, "attack")

    def test_adware_fills_the_discard_with_spam(self):
        a = Adware(6)
        a.plan(1)
        antes = self.p.deck.discard_size
        a.act(self.p)
        self.assertEqual(self.p.deck.discard_size, antes + 2)
        self.assertTrue(all(c.name == SPAM for c in list(self.p.deck._discard)[-2:]))
        self.p.deck.start_combat()                    # o lixo some no fim do combate
        self.assertEqual(len(self.p.deck), 10)
        self.assertEqual(self.p.deck.draw_pile_size, 10)

    def test_ransomware_drains_saved_energy_but_never_below_zero(self):
        r = Ransomware(8)
        r.plan(1)
        self.assertEqual(r.intent.kind, "drain")
        self.p.spend_energy(self.p.energy - 1)       # só sobra 1 de energia
        r.act(self.p)
        self.assertEqual(self.p.energy, 0)           # rouba 1, não 2: nunca fica negativa
        self.p.spend_energy(self.p.energy)
        r.act(self.p)
        self.assertEqual(self.p.energy, 0)
        r.plan(2)
        self.assertEqual(r.intent.kind, "attack")
        r.plan(3)
        self.assertEqual(r.intent.kind, "defend")

    def test_drain_takes_exactly_two_when_there_is_enough(self):
        r = Ransomware(8)
        r.plan(1)
        antes = self.p.energy
        r.act(self.p)
        self.assertEqual(self.p.energy, antes - 2)

    def test_every_new_intent_describes_itself(self):
        for classe in Intent.__subclasses__():
            self.assertTrue(classe(2).describe())
            self.assertTrue(classe(2).short())


class TestSpawn(unittest.TestCase):
    def test_new_enemies_only_appear_at_their_min_level(self):
        import random
        random.seed(1)
        rng.seed(1)
        cedo = {type(spawn_enemy(1)) for _ in range(60)}
        self.assertEqual(cedo, {Bug, Virus})
        tarde = {type(spawn_enemy(9)) for _ in range(400)}
        self.assertIn(MemoryLeak, tarde)
        self.assertNotIn(Boss, tarde)
        self.assertTrue({Worm, Adware, Keylogger, Ransomware} <= tarde)

    def test_min_levels_are_respected(self):
        rng.seed(2)
        nivel_2 = {type(spawn_enemy(2)) for _ in range(200)}       # sala 2 do modo normal
        self.assertTrue(nivel_2 <= {Bug, Virus})
        nivel_4 = {type(spawn_enemy(4)) for _ in range(300)}
        self.assertNotIn(Ransomware, nivel_4)
        self.assertNotIn(Keylogger, nivel_4)


if __name__ == "__main__":
    unittest.main()
