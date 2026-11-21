"""Testes do conteúdo novo: veneno, cartas de risco, REFACTOR e relíquias novas."""
import random
import unittest

import config
from battle import Battle
from cards import (CARD_FACTORIES, REFACTOR_OPTION, REWARD_POOL, UPGRADES,
                   BASIC_ATTACK, BASIC_DEFENSE, make_card)
from characters import Player
from deck import Deck
from enemies import Bug
from game import Game
from hall_of_fame import HallOfFame
from relics import make_relic
from savegame import SaveGame
from simulate import NaiveBot
from rng import rng


def new_player(*cards, relics=()):
    p = Player("T", Deck([make_card(n) for n in (cards or ("If/Else",) * 10)]))
    for r in relics:
        p.add_relic(make_relic(r))
    return p


class TestPoison(unittest.TestCase):
    def test_poison_ignores_block_and_expires(self):
        e = Bug(1)
        e.gain_block(50)
        e.apply_status("poison", 2)
        hp = e.hp
        self.assertIn("veneno", e.end_turn())
        self.assertEqual((e.hp, e.block), (hp - config.POISON_DAMAGE, 50))
        e.end_turn()
        self.assertEqual(e.poison, 0)
        self.assertEqual(e.end_turn(), "")           # já não há veneno

    def test_zombie_process_applies_poison(self):
        e = Bug(1)
        make_card("Zombie Process").play(new_player(), e)
        self.assertEqual(e.poison, 4)

    def test_poison_can_win_the_battle(self):
        """O inimigo morre do veneno no fim do seu próprio turno."""
        class EndTurnUI(NaiveBot):
            def choose_purchase(self, can): return "attack"
            def choose_card(self, player, hand): return None
        bug = Bug(1)
        bug.take_damage(bug.hp - 2)
        bug.apply_status("poison", 3)
        self.assertTrue(Battle(new_player(), bug, EndTurnUI()).run())

    def test_rate_limiter_weakens_enemy(self):
        e = Bug(1)
        make_card("Rate Limiter").play(new_player(), e)
        self.assertEqual(e.weak, 2)


class TestRiskCards(unittest.TestCase):
    def test_buffer_overflow_ignores_block(self):
        e = Bug(5)
        e.gain_block(30)
        hp = e.hp
        make_card("Buffer Overflow").play(new_player(), e)
        self.assertEqual((e.hp, e.block), (hp - 10, 30))

    def test_infinite_loop_hurts_the_player(self):
        p, e = new_player(), Bug(5)
        make_card("Infinite Loop").play(p, e)
        self.assertEqual(p.hp, p.max_hp - 4)
        self.assertEqual(e.hp, e.max_hp - 12)

    def test_recoil_never_kills(self):
        p = new_player()
        p.take_damage(p.hp - 2)
        make_card("Infinite Loop").play(p, Bug(5))
        self.assertEqual(p.hp, 1)

    def test_sudo_gives_energy_but_exposes(self):
        p = new_player()
        make_card("Sudo").play(p, Bug(1))
        self.assertEqual((p.energy, p.vulnerable), (3, 2))


class TestRefactor(unittest.TestCase):
    def test_every_base_card_has_a_plus_version(self):
        for base, plus in UPGRADES.items():
            self.assertEqual(plus, base + "+")
            self.assertIn(plus, CARD_FACTORIES)
            self.assertNotIn(plus, UPGRADES)        # só se melhora uma vez

    def test_rewards_exclude_basics_and_plus_versions(self):
        self.assertNotIn(BASIC_ATTACK, REWARD_POOL)
        self.assertNotIn(BASIC_DEFENSE, REWARD_POOL)
        self.assertTrue(all(not n.endswith("+") for n in REWARD_POOL))

    def test_upgrade_replaces_exactly_one_card(self):
        d = Deck([make_card("Segfault"), make_card("Segfault"), make_card("Firewall")])
        nova = d.upgrade_card("Segfault")
        nomes = sorted(c.name for c in d.cards)
        self.assertEqual(nova.name, "Segfault+")
        self.assertEqual(nomes, ["Firewall", "Segfault", "Segfault+"])

    def test_cannot_upgrade_twice_or_missing(self):
        d = Deck([make_card("Segfault+")])
        self.assertEqual(d.upgradable_names(), [])
        with self.assertRaises(ValueError):
            d.upgrade_card("Segfault+")
        with self.assertRaises(ValueError):
            d.upgrade_card("Firewall")

    def test_plus_cards_are_stronger(self):
        e1, e2, p = Bug(9), Bug(9), new_player()
        make_card("Segfault").play(p, e1)
        make_card("Segfault+").play(p, e2)
        self.assertLess(e2.hp, e1.hp)

    def test_reward_menu_refactor_flow(self):
        """Escolher REFACTOR e depois a carta: o baralho fica com a versão melhorada."""
        class RefactorUI(NaiveBot):
            calls = 0
            def choose_reward(self, options, can_upgrade=False, mutation=None):
                RefactorUI.calls += 1
                return REFACTOR_OPTION
            def choose_upgrade(self, pairs):
                # 1.ª vez volta atrás (None); 2.ª escolhe o primeiro
                return None if RefactorUI.calls == 1 else 0
        random.seed(3)
        rng.seed(3)
        p = new_player("Segfault", "If/Else")
        Game(ui=RefactorUI(), hall=HallOfFame(None), save=SaveGame(None))._give_reward(p)
        self.assertEqual(RefactorUI.calls, 2)        # voltou ao menu e tentou outra vez
        self.assertIn("Segfault+", [c.name for c in p.deck.cards])


class TestNewRelics(unittest.TestCase):
    def test_linter_only_reacts_to_defense(self):
        p = new_player(relics=["Linter"])
        p.notify_card_played(make_card("If/Else"))
        self.assertEqual(p.block, 2)
        p.notify_card_played(make_card("Segfault"))
        self.assertEqual(p.block, 2)

    def test_auto_save_heals_each_turn(self):
        p = new_player(relics=["Auto-Save"])
        p.take_damage(10)
        p.start_turn(first_turn=True)
        self.assertEqual(p.hp, p.max_hp - 8)

    def test_overvolt_trades_hp_for_energy(self):
        p = new_player(relics=["Overvolt"])
        p.start_combat()
        p.start_turn(first_turn=True)
        self.assertEqual(p.hp, p.max_hp - 5)
        self.assertEqual(p.energy, config.INITIAL_ENERGY + 2)

    def test_legacy_code_trades_healing_for_damage(self):
        p, e = new_player(relics=["Código Legado"]), Bug(5)
        p.take_damage(20)
        self.assertEqual(p.heal_after_combat(), 0)
        hp = e.hp
        make_card('Print("Hit")').play(p, e)
        self.assertEqual(e.hp, hp - 8)


if __name__ == "__main__":
    unittest.main()
