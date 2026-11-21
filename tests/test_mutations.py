"""Testes das mutações de cartas e do menu de recompensa com mutação."""
import json
import tempfile
import unittest
from pathlib import Path

from battle import Battle
from cards import (MUTATE_OPTION, DefenseCard, AttackCard, make_card, valid_card_spec)
from characters import Player
from deck import Deck
from enemies import Bug
from game import Game
from hall_of_fame import HallOfFame
from modes import MODES
from mutations import MUTATION_FACTORIES, Mutation, make_mutation
from savegame import SaveGame
from simulate import NaiveBot


def new_player(*cards):
    p = Player("T", Deck([make_card(n) for n in (cards or ("If/Else",) * 10)]))
    p.start_combat()
    return p


class Stop(Exception):
    pass


class TestEachMutation(unittest.TestCase):
    def test_catalog_is_built_from_subclasses(self):
        self.assertEqual(len(MUTATION_FACTORIES), len(Mutation.__subclasses__()))
        for nome in MUTATION_FACTORIES:
            self.assertEqual(make_mutation(nome).name, nome)
        with self.assertRaises(KeyError):
            make_mutation("Nope")

    def test_unstable_is_cheaper_but_costs_life(self):
        p, e = new_player(), Bug(9)
        carta = make_card("Segfault|Instável")
        self.assertEqual(carta.cost, 2)
        hp, ehp = p.hp, e.hp
        carta.play(p, e)
        self.assertEqual((p.hp, e.hp), (hp - 2, ehp - 12))

    def test_cost_never_drops_below_one(self):
        self.assertEqual(make_card('Print("Hit")|Instável').cost, 1)
        self.assertEqual(make_card('Print("Hit")|Efémero').cost, 1)

    def test_recursive_plays_twice_and_stops_if_enemy_dies(self):
        p, e = new_player(), Bug(9)
        carta = make_card("Segfault|Recursivo")
        self.assertEqual(carta.cost, 4)
        hp = e.hp
        texto = carta.play(p, e)
        self.assertEqual(e.hp, hp - 24)
        self.assertIn("de novo", texto)
        fraco = Bug(1)
        fraco.take_damage(fraco.hp - 5)
        carta.play(p, fraco)
        self.assertEqual(fraco.hp, 0)            # morreu à 1.ª; a 2.ª não aconteceu

    def test_vampiric_heals(self):
        p = new_player()
        p.take_damage(10)
        hp = p.hp
        make_card("If/Else|Vampírico").play(p, Bug(1))
        self.assertEqual(p.hp, hp + 2)

    def test_armored_gives_extra_block(self):
        p = new_player()
        make_card("If/Else|Blindado").play(p, Bug(1))
        self.assertEqual(p.block, 8)

    def test_infected_poisons_the_enemy(self):
        p, e = new_player(), Bug(1)
        make_card('Print("Hit")|Infectado').play(p, e)
        self.assertEqual(e.poison, 2)

    def test_precompiled_draws_a_card(self):
        p = new_player()
        n = len(p.deck.hand)
        carta = make_card("If/Else|Compilado")
        self.assertEqual(carta.cost, 2)
        carta.play(p, Bug(1))
        self.assertEqual(len(p.deck.hand), n + 1)

    def test_ephemeral_is_exiled_until_the_combat_ends(self):
        class Ui(NaiveBot):
            calls = 0
            def choose_purchase(self, can): return "attack"
            def choose_card(self, player, hand):
                Ui.calls += 1
                if Ui.calls > 1:
                    raise Stop
                return 0
        p = Player("T", Deck([make_card("Segfault|Efémero")] * 10))
        with self.assertRaises(Stop):
            Battle(p, Bug(1), Ui()).run()
        self.assertEqual(p.deck.discard_size, 0)            # não foi ao descarte
        self.assertEqual(len(p.deck.hand), 5)               # 5 + compra - a jogada
        p.deck.start_combat()                               # no combate seguinte volta
        self.assertEqual(p.deck.draw_pile_size, 10)


class TestMutatedCards(unittest.TestCase):
    def test_a_mutated_card_keeps_its_type(self):
        self.assertIsInstance(make_card("If/Else|Blindado"), DefenseCard)
        self.assertIsInstance(make_card("Segfault|Recursivo"), AttackCard)

    def test_identifiers_and_names(self):
        c = make_card("Segfault|Vampírico")
        self.assertEqual((c.name, c.spec, c.display_name),
                         ("Segfault", "Segfault|Vampírico", "Segfault (Vampírico)"))
        self.assertIn("Vampírico", c.description)
        self.assertIn("Segfault (Vampírico)", str(c))
        self.assertEqual(make_card("Segfault").spec, "Segfault")

    def test_only_one_mutation_per_card(self):
        c = make_card("Segfault|Vampírico")
        with self.assertRaises(ValueError):
            c.mutate(make_mutation("Blindado"))

    def test_unknown_names_raise(self):
        for mau in ("Segfault|Nope", "Nope|Vampírico"):
            with self.assertRaises(KeyError):
                make_card(mau)

    def test_valid_card_spec(self):
        self.assertTrue(valid_card_spec("Segfault"))
        self.assertTrue(valid_card_spec("Segfault+|Blindado"))
        for mau in ("Segfault|Nope", "Spam", "Spam|Blindado", "x", 5, None):
            self.assertFalse(valid_card_spec(mau), mau)

    def test_spam_does_nothing(self):
        p, e = new_player(), Bug(1)
        hp = e.hp
        make_card("Spam").play(p, e)
        self.assertEqual((e.hp, p.block, p.hp), (hp, 0, p.max_hp))


class TestDeckAndSave(unittest.TestCase):
    def test_mutable_names_skip_mutated_cards(self):
        d = Deck([make_card("Segfault|Vampírico"), make_card("Segfault"), make_card("If/Else")])
        self.assertEqual(d.mutable_names(), ["Segfault", "If/Else"])
        d.mutate_card("Segfault", make_mutation("Blindado"))
        self.assertEqual(d.mutable_names(), ["If/Else"])
        with self.assertRaises(ValueError):
            d.mutate_card("Segfault", make_mutation("Blindado"))

    def test_refactor_keeps_the_mutation(self):
        d = Deck([make_card("Segfault|Vampírico"), make_card("Segfault")])
        self.assertEqual(d.upgradable_names(), ["Segfault|Vampírico", "Segfault"])
        nova = d.upgrade_card("Segfault|Vampírico")
        self.assertEqual(nova.spec, "Segfault+|Vampírico")
        self.assertIn("Segfault", [c.spec for c in d.cards])      # a outra ficou igual

    def test_cannot_upgrade_twice_even_if_mutated(self):
        d = Deck([make_card("Segfault+|Vampírico")])
        self.assertEqual(d.upgradable_names(), [])
        with self.assertRaises(ValueError):
            d.upgrade_card("Segfault+|Vampírico")

    def test_save_roundtrip_with_mutated_cards(self):
        with tempfile.TemporaryDirectory() as tmp:
            save = SaveGame(Path(tmp) / "save.json")
            p = Player("Dino", Deck([make_card("Firewall|Blindado"), make_card("If/Else")]))
            self.assertTrue(save.save(p, MODES["curto"], 2, 5))
            self.assertEqual(save.load().cards, ["Firewall|Blindado", "If/Else"])

    def test_save_with_junk_or_bad_mutations_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            caminho = Path(tmp) / "save.json"
            for mau in (["Spam"], ["Segfault|Nope"], ["Nope|Vampírico"]):
                p = Player("Dino", Deck([make_card("If/Else")]))
                save = SaveGame(caminho)
                save.save(p, MODES["curto"], 2, 5)
                dados = json.loads(caminho.read_text(encoding="utf-8"))
                dados["cards"] = mau
                caminho.write_text(json.dumps(dados), encoding="utf-8")
                self.assertIsNone(save.load(), mau)


class TestRewardWithMutation(unittest.TestCase):
    def _game(self, ui):
        return Game(ui=ui, hall=HallOfFame(None), save=SaveGame(None))

    def test_mutation_flow_back_keeps_the_same_mutation(self):
        ofertas, escolhas = [], iter([MUTATE_OPTION, MUTATE_OPTION])

        class Ui(NaiveBot):
            alvos = iter([None, 1])
            def choose_reward(self, options, can_upgrade=False, mutation=None):
                ofertas.append(mutation.name)
                return next(escolhas)
            def choose_mutation_target(self, mutation, pairs):
                antes, depois = pairs[1]
                assert depois.mutation.name == mutation.name and antes.mutation is None
                return next(Ui.alvos)
        p = new_player("Segfault", "If/Else")
        self._game(Ui())._give_reward(p)
        self.assertEqual(ofertas[0], ofertas[1])             # voltar atrás não re-sorteia
        mutadas = [c.spec for c in p.deck.cards if c.mutation]
        self.assertEqual(len(mutadas), 1)
        self.assertTrue(mutadas[0].startswith("If/Else|"))

    def test_no_mutation_is_offered_when_every_card_is_mutated(self):
        vistas = []

        class Ui(NaiveBot):
            def choose_reward(self, options, can_upgrade=False, mutation=None):
                vistas.append(mutation)
                return None
        p = new_player("Segfault|Vampírico", "If/Else|Blindado")
        self._game(Ui())._give_reward(p)
        self.assertEqual(vistas, [None])


if __name__ == "__main__":
    unittest.main()
