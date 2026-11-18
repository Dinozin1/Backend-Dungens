"""Testes das cartas e do deck (R2: polimorfismo; R3: coleção de objetos)."""
import unittest

from cards import CARD_FACTORIES, Card, make_card
from characters import Player
from deck import Deck
from enemies import Bug


def new_player(cards=("If/Else",) * 10):
    return Player("T", Deck([make_card(n) for n in cards]))


class TestCards(unittest.TestCase):
    def test_card_is_abstract(self):
        with self.assertRaises(TypeError):
            Card("x", 1, "y")

    def test_unknown_card_raises(self):
        with self.assertRaises(KeyError):
            make_card("Nope")

    def test_all_cards_have_valid_cost_and_play(self):
        for nome in CARD_FACTORIES:
            carta = make_card(nome)
            self.assertTrue(1 <= carta.cost <= 8, nome)
            p, e = new_player(), Bug(1)
            p.start_combat()
            self.assertIsInstance(carta.play(p, e), str)   # polimorfismo

    def test_card_names_match_catalog_keys(self):
        for nome in CARD_FACTORIES:
            self.assertEqual(make_card(nome).name, nome)

    def test_attack_hits_enemy(self):
        p, e = new_player(), Bug(1)
        hp = e.hp
        make_card('Print("Hit")').play(p, e)
        self.assertEqual(e.hp, hp - 5)

    def test_fork_bomb_hits_twice(self):
        p, e = new_player(), Bug(5)
        hp = e.hp
        make_card("Fork Bomb").play(p, e)
        self.assertEqual(e.hp, hp - 12)

    def test_debug_mode_bonus_applies_once(self):
        p, e = new_player(), Bug(5)
        hp = e.hp
        make_card("Debug Mode").play(p, e)
        make_card('Print("Hit")').play(p, e)
        self.assertEqual(e.hp, hp - 10)
        make_card('Print("Hit")').play(p, e)
        self.assertEqual(e.hp, hp - 15)

    def test_defense_heal_debuff_parry(self):
        p, e = new_player(), Bug(1)
        make_card("Try/Catch").play(p, e)
        self.assertEqual(p.block, 10)
        p.take_damage(20)
        before = p.hp
        make_card("Ctrl+Z").play(p, e)
        self.assertEqual(p.hp, before + 8)
        make_card("Stack Overflow").play(p, e)
        self.assertEqual(e.vulnerable, 2)
        make_card("Catch & Return").play(p, e)
        self.assertEqual(p.parry, 8)

    def test_draw_card_draws_from_deck(self):
        p, e = new_player(), Bug(1)
        p.start_combat()
        n = len(p.deck.hand)
        make_card("Garbage Collector").play(p, e)
        self.assertEqual(len(p.deck.hand), n + 2)


class TestDeck(unittest.TestCase):
    def setUp(self):
        self.deck = Deck([make_card("If/Else") for _ in range(6)])

    def test_draw_moves_cards_to_hand(self):
        self.deck.start_combat()
        self.deck.draw(4)
        self.assertEqual(len(self.deck.hand), 4)
        self.assertEqual(self.deck.draw_pile_size, 2)

    def test_reshuffle_discard_when_pile_empty(self):
        self.deck.start_combat()
        self.deck.draw(6)
        self.deck.discard_from_hand(0)
        self.deck.discard_from_hand(0)
        self.assertEqual(self.deck.available_to_draw, 2)
        self.assertEqual(len(self.deck.draw(1)), 1)

    def test_draw_from_empty_returns_nothing(self):
        self.deck.start_combat()
        self.deck.draw(6)
        self.assertEqual(self.deck.draw(3), [])

    def test_play_moves_card_to_discard(self):
        self.deck.start_combat()
        self.deck.draw(2)
        self.deck.discard_from_hand(0)
        self.assertEqual((len(self.deck.hand), self.deck.discard_size), (1, 1))

    def test_add_card_grows_deck(self):
        self.deck.add_card(make_card("Firewall"))
        self.assertEqual(len(self.deck), 7)


if __name__ == "__main__":
    unittest.main()
