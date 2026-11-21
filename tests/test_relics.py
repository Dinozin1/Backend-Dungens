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
        self.assertEqual(p.energy, antes + 3)

    def test_defrag_draws_only_with_a_nearly_empty_hand(self):
        p = player_with("Defrag")
        p.start_combat()
        p.start_turn(first_turn=False)
        self.assertEqual(len(p.deck.hand), config.INITIAL_HAND)          # mão cheia: nada
        for _ in range(4):
            p.deck.discard_from_hand(0)
        p.start_turn(first_turn=False)
        self.assertEqual(len(p.deck.hand), 1 + 2)

    def test_watchdog_heals_only_below_half(self):
        p = player_with("Watchdog")
        p.take_damage(10)
        p.start_turn(first_turn=True)
        self.assertEqual(p.hp, p.max_hp - 10)
        p.take_damage(25)
        hp = p.hp
        p.start_turn(first_turn=False)
        self.assertEqual(p.hp, hp + 3)

    def test_honeypot_hurts_the_attacker_even_through_block(self):
        p, e = player_with("Honeypot"), Bug(5)
        p.gain_block(50)
        hp = e.hp
        p.receive_attack(5, e)
        self.assertEqual(e.hp, hp - 2)

    def test_honeypot_does_not_trigger_on_parry(self):
        p, e = player_with("Honeypot"), Bug(5)
        p.set_parry(8)
        hp = e.hp
        p.receive_attack(5, e)
        self.assertEqual(e.hp, hp - 8)                  # só o parry, sem os 2 do Honeypot

    def test_stack_canary_saves_once_per_combat(self):
        p, e = player_with("Stack Canary"), Bug(5)
        p.start_combat()
        p.take_damage(p.hp - 3)
        p.receive_attack(50, e)
        self.assertEqual((p.hp, p.is_alive), (1, True))
        p.receive_attack(50, e)
        self.assertFalse(p.is_alive)
        p2 = player_with("Stack Canary")
        for _ in range(2):                               # volta a funcionar no combate seguinte
            p2.start_combat()
            p2.restore_hp(p2.max_hp)
            p2.take_damage(p2.hp - 1)
            p2.receive_attack(50, e)
            self.assertTrue(p2.is_alive)

    def test_safe_mode_trades_energy_for_block(self):
        p = player_with("Modo Seguro")
        p.start_combat()
        p.start_turn(first_turn=True)
        self.assertEqual((p.block, p.energy), (6, config.INITIAL_ENERGY - 1))
        p.spend_energy(p.energy)
        p.start_turn(first_turn=False)
        self.assertEqual(p.energy, config.ENERGY_PER_TURN - 1)

    def test_catalog_is_built_from_subclasses(self):
        from relics import Relic
        self.assertEqual(len(RELIC_FACTORIES), len(Relic.__subclasses__()))

    def test_legacy_code_blocks_healing_even_with_backup(self):
        p = player_with("Backup", "Código Legado")
        p.take_damage(30)
        self.assertEqual(p.heal_after_combat(), 0)

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
