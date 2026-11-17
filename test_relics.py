"""Testes das relíquias (ganchos redefinidos por cada subclasse)."""
import unittest

import config
from cards import make_card
from characters import Player
from deck import Deck
from enemies import Bug
from relics import RELIC_FACTORIES, make_relic, random_relics


def player_with(*relics):
    p = Player("T", Deck([make_card("If/Else") for _ in range(10)]))
    for r in relics:
        p.add_relic(make_relic(r))
    return p


class TestRelics(unittest.TestCase):
    def test_overclock_extra_energy_each_turn(self):
        p = player_with("Overclock")
        p.start_combat()
        p.start_turn(first_turn=True)
        self.assertEqual(p.energy, config.INITIAL_ENERGY + 1)

    def test_antivirus_gives_block_each_turn(self):
        p = player_with("Antivirus")
        p.start_turn(first_turn=True)
        self.assertEqual(p.block, 3)

    def test_cache_gives_extra_card(self):
        p = player_with("Cache L1")
        p.start_combat()
        self.assertEqual(len(p.deck.hand), config.INITIAL_HAND + 1)

    def test_stack_trace_adds_damage_per_hit(self):
        p, e = player_with("Stack Trace"), Bug(5)
        hp = e.hp
        make_card("Fork Bomb").play(p, e)
        self.assertEqual(e.hp, hp - 14)

    def test_backup_heals_extra_after_combat(self):
        p = player_with("Backup")
        p.take_damage(30)
        self.assertEqual(p.heal_after_combat(), 6 + 4)

    def test_macro_grants_energy_every_five_cards(self):
        p = player_with("Macro")
        p.start_combat()
        p.start_turn(first_turn=True)
        antes = p.energy
        for _ in range(5):
            p.notify_card_played(None)
        self.assertEqual(p.energy, antes + 1)

    def test_every_relic_can_be_built(self):
        for nome in RELIC_FACTORIES:
            self.assertEqual(make_relic(nome).name, nome)

    def test_unknown_relic_raises(self):
        with self.assertRaises(KeyError):
            make_relic("Nope")

    def test_offers_exclude_owned_relics(self):
        dono = list(RELIC_FACTORIES)[:-2]
        ofertas = random_relics(dono, 2)
        self.assertEqual(len(ofertas), 2)
        self.assertTrue(all(r.name not in dono for r in ofertas))

    def test_offer_empty_when_all_owned(self):
        self.assertEqual(random_relics(list(RELIC_FACTORIES), 2), [])


if __name__ == "__main__":
    unittest.main()
