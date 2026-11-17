"""Testes de Character e Player: dano, estados, energia, parry."""
import unittest

import config
from cards import make_card
from characters import Player
from deck import Deck
from enemies import Bug, RaceCondition


def new_player():
    return Player("T", Deck([make_card("If/Else") for _ in range(10)]))


class TestDamage(unittest.TestCase):
    def test_block_absorbs_before_hp(self):
        bug = Bug(1)
        bug.gain_block(3)
        r = bug.take_damage(5)
        self.assertEqual((r.absorbed, r.lost), (3, 2))
        self.assertEqual(bug.block, 0)

    def test_vulnerable_takes_50_percent_more(self):
        bug = Bug(1)
        bug.apply_status("vulnerable", 2)
        self.assertEqual(bug.take_damage(10).total, 15)

    def test_weak_deals_25_percent_less(self):
        p = new_player()
        p.apply_status("weak", 1)
        self.assertEqual(p.outgoing_damage(8), 6)

    def test_hp_never_below_zero(self):
        bug = Bug(1)
        bug.take_damage(999)
        self.assertEqual(bug.hp, 0)
        self.assertFalse(bug.is_alive)

    def test_status_lasts_exactly_n_turns(self):
        p = new_player()
        p.apply_status("weak", 2)
        p.end_turn()
        self.assertEqual(p.weak, 1)
        p.end_turn()
        self.assertEqual(p.weak, 0)

    def test_unknown_status_rejected(self):
        with self.assertRaises(ValueError):
            new_player().apply_status("burn", 1)

    def test_heal_is_capped(self):
        p = new_player()
        p.take_damage(10)
        self.assertEqual(p.heal(50), 10)
        self.assertEqual(p.hp, p.max_hp)


class TestParry(unittest.TestCase):
    def test_parry_cancels_and_reflects(self):
        p, bug = new_player(), Bug(1)
        hp = bug.hp
        p.set_parry(8)
        r = p.receive_attack(99, bug)
        self.assertTrue(r.parried)
        self.assertEqual(p.hp, p.max_hp)
        self.assertEqual(bug.hp, hp - 8)

    def test_parry_only_cancels_one_hit(self):
        """A Race Condition bate 2 vezes: o parry só anula o primeiro golpe."""
        p, race = new_player(), RaceCondition(1)
        p.set_parry(8)
        race.plan(1)
        race.act(p)
        self.assertEqual(p.hp, p.max_hp - 3)

    def test_parry_expires_at_start_of_next_turn(self):
        p = new_player()
        p.set_parry(8)
        p.start_turn(first_turn=False)
        self.assertEqual(p.parry, 0)


class TestEnergy(unittest.TestCase):
    def test_energy_is_capped(self):
        p = new_player()
        p.gain_energy(100)
        self.assertEqual(p.energy, config.MAX_ENERGY)

    def test_cannot_overspend(self):
        p = new_player()
        with self.assertRaises(ValueError):
            p.spend_energy(1)

    def test_first_turn_gives_no_extra_energy(self):
        p = new_player()
        p.start_combat()
        p.start_turn(first_turn=True)
        self.assertEqual(p.energy, config.INITIAL_ENERGY)
        p.start_turn(first_turn=False)
        self.assertEqual(p.energy, config.INITIAL_ENERGY + config.ENERGY_PER_TURN)

    def test_block_resets_each_turn(self):
        p = new_player()
        p.gain_block(9)
        p.start_turn(first_turn=False)
        self.assertEqual(p.block, 0)

    def test_heal_after_combat_is_10_percent(self):
        p = new_player()
        p.take_damage(30)
        self.assertEqual(p.heal_after_combat(), 6)


if __name__ == "__main__":
    unittest.main()
