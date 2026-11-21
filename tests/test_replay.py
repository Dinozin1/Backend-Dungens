"""Testes do anti 'save scumming': retomar uma sala a meio é igual a não ter saído."""
import json
import random
import tempfile
import unittest
from pathlib import Path

from cards import MUTATE_OPTION, REFACTOR_OPTION, make_card
from game import Game
from hall_of_fame import HallOfFame
from modes import MODES
from relics import make_relic
from replay import ReplayError, RoomRecorder
from rng import rng
from savegame import SaveGame
from simulate import NaiveBot
from ui import QuitGame


class Steady(NaiveBot):
    """Bot SEM aleatoriedade: com a mesma sala, joga sempre da mesma maneira."""
    def __init__(self):
        self.enemy = None
        self.states, self.messages = [], []

    def message(self, text): self.messages.append(text)
    def show_state(self, player, enemy, turn):
        self.enemy = enemy
        self.states.append((player.hp, enemy.hp, player.energy, turn))
    def choose_purchase(self, can_draw_deck): return "deck" if can_draw_deck else "attack"
    def choose_reward(self, options, can_upgrade=False, mutation=None):
        return MUTATE_OPTION if mutation is not None else options[0]   # usa as mutações
    def choose_mutation_target(self, mutation, pairs): return 0
    def choose_relic(self, options): return options[0]
    def choose_upgrade(self, pairs): return 0


class QuitAfter(Steady):
    """Sai depois de n perguntas ao vivo (qualquer tipo)."""
    def __init__(self, n):
        super().__init__()
        self.n, self.asked = n, 0

    def _tick(self):
        self.asked += 1
        if self.asked > self.n:
            raise QuitGame

    def choose_purchase(self, can): self._tick(); return super().choose_purchase(can)
    def choose_card(self, player, hand): self._tick(); return super().choose_card(player, hand)
    def choose_reward(self, o, can_upgrade=False, mutation=None):
        self._tick()
        return super().choose_reward(o, can_upgrade, mutation)
    def choose_mutation_target(self, mutation, pairs):
        self._tick()
        return 0
    def choose_relic(self, o): self._tick(); return o[0]


def seed_everything(n=7):
    random.seed(n)
    rng.seed(n)


def result(hall):
    e = hall.entries[0]
    return (e.score, e.rooms, e.won)


class TestResumeIsFaithful(unittest.TestCase):
    def _uninterrupted(self, mode):
        seed_everything()
        hall = HallOfFame(None)
        Game(ui=Steady(), hall=hall, save=SaveGame(None)).play_new(MODES[mode])
        return result(hall)

    def _interrupted(self, mode, n):
        seed_everything()
        hall = HallOfFame(None)
        with tempfile.TemporaryDirectory() as d:
            save = SaveGame(Path(d) / "save.json")
            try:
                Game(ui=QuitAfter(n), hall=hall, save=save).play_new(MODES[mode])
                return result(hall), False                # a run acabou sem sair
            except QuitGame:
                estado = save.load()
                self.assertIsNotNone(estado)
                Game(ui=Steady(), hall=hall, save=save).continue_run(estado)
                self.assertIsNone(save.load())           # run acabou: gravação apagada
                return result(hall), True

    def test_quitting_anywhere_changes_nothing(self):
        """Sair em qualquer ponto (combate, recompensa, relíquia) e continuar dá o mesmo."""
        quits = 0
        for mode in MODES:
            esperado = self._uninterrupted(mode)
            for n in (0, 1, 4, 9, 17, 30, 55, 80, 120):
                obtido, saiu = self._interrupted(mode, n)
                quits += saiu
                self.assertEqual(obtido, esperado, f"{mode}, saiu após {n} perguntas")
        self.assertGreaterEqual(quits, 10)               # o teste saiu mesmo a meio

    def test_same_hand_energy_and_enemy_after_resume(self):
        seed_everything()

        class QuitAtThirdCard(Steady):
            cartas = 0
            def choose_card(self, player, hand):
                QuitAtThirdCard.cartas += 1
                if QuitAtThirdCard.cartas == 3:
                    self.snapshot = ([c.name for c in hand], player.hp, player.energy,
                                     self.enemy.hp, self.enemy.intent.value)
                    raise QuitGame
                return super().choose_card(player, hand)

        class Resumed(Steady):
            snapshot = None
            def choose_card(self, player, hand):
                if self.snapshot is None:
                    self.snapshot = ([c.name for c in hand], player.hp, player.energy,
                                     self.enemy.hp, self.enemy.intent.value)
                return super().choose_card(player, hand)

        with tempfile.TemporaryDirectory() as d:
            save = SaveGame(Path(d) / "save.json")
            quitter = QuitAtThirdCard()
            with self.assertRaises(QuitGame):
                Game(ui=quitter, hall=HallOfFame(None), save=save).play_new(MODES["curto"])
            retomado = Resumed()
            Game(ui=retomado, hall=HallOfFame(None), save=save).continue_run(save.load())
            self.assertEqual(retomado.snapshot, quitter.snapshot)
            self.assertTrue(any("retomado" in m for m in retomado.messages))

    def test_replay_is_silent(self):
        """Durante o replay não se mostra nada; só se mostra o que é novo."""
        seed_everything()
        with tempfile.TemporaryDirectory() as d:
            save = SaveGame(Path(d) / "save.json")
            with self.assertRaises(QuitGame):
                Game(ui=QuitAfter(12), hall=HallOfFame(None), save=save).play_new(MODES["curto"])
            ui = Steady()
            Game(ui=ui, hall=HallOfFame(None), save=save).continue_run(save.load())
            texto = "\n".join(ui.messages)
            self.assertNotIn(">>> Sala 1/", texto)       # a sala 1 repetiu-se em silêncio
            self.assertIn(">>> Sala 2/", texto)          # e a seguinte já é mostrada


class TestRecordedFile(unittest.TestCase):
    def test_every_answer_is_saved_immediately(self):
        """Mesmo que o jogo seja fechado à força, a última resposta já está no ficheiro."""
        seed_everything()
        with tempfile.TemporaryDirectory() as d:
            caminho = Path(d) / "save.json"
            with self.assertRaises(QuitGame):
                Game(ui=QuitAfter(6), hall=HallOfFame(None),
                     save=SaveGame(caminho)).play_new(MODES["curto"])
            dados = json.loads(caminho.read_text(encoding="utf-8"))
            self.assertEqual(len(dados["log"]), 6)
            self.assertIsInstance(dados["seed"], int)
            self.assertEqual(dados["next_room"], 1)

    def test_tampered_log_restarts_the_room(self):
        with tempfile.TemporaryDirectory() as d:
            caminho = Path(d) / "save.json"
            caminho.write_text(json.dumps({
                "name": "Dino", "hp": 50, "cards": ["Print(\"Hit\")"] * 6 + ["If/Else"] * 4,
                "relics": [], "mode": "curto", "next_room": 2, "total_turns": 3,
                "seed": 5, "log": ["attack", "isto não é uma carta"]}), encoding="utf-8")
            save, hall, ui = SaveGame(caminho), HallOfFame(None), Steady()
            Game(ui=ui, hall=hall, save=save).continue_run(save.load())
            self.assertTrue(any("inconsistente" in m for m in ui.messages))
            self.assertEqual(len(hall.entries), 1)

    def test_bad_seed_or_log_files_are_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            caminho = Path(d) / "save.json"
            base = {"name": "Dino", "hp": 40, "cards": ["If/Else"], "relics": [],
                    "mode": "normal", "next_room": 3, "total_turns": 9}
            for mau in ({"seed": -1}, {"seed": "x"}, {"seed": True}, {"log": "x"},
                        {"log": [{"a": 1}]}, {"log": [True]}, {"log": [1.5]},
                        {"log": ["x" * 50]}, {"log": [0] * 6000}):
                caminho.write_text(json.dumps(dict(base, **mau)), encoding="utf-8")
                self.assertIsNone(SaveGame(caminho).load(), mau)
            caminho.write_text(json.dumps(dict(base, seed=9, log=[0, None, "attack"])),
                               encoding="utf-8")
            estado = SaveGame(caminho).load()
            self.assertEqual((estado.seed, estado.log), (9, [0, None, "attack"]))

    def test_old_saves_without_seed_still_load(self):
        with tempfile.TemporaryDirectory() as d:
            caminho = Path(d) / "save.json"
            caminho.write_text(json.dumps({
                "name": "Dino", "hp": 40, "cards": ["If/Else"], "relics": [],
                "mode": "normal", "next_room": 3, "total_turns": 9}), encoding="utf-8")
            estado = SaveGame(caminho).load()
            self.assertEqual((estado.seed, estado.log), (0, []))


class TestRoomRecorder(unittest.TestCase):
    def test_answers_are_logged_and_replayed_without_asking(self):
        perguntas = []

        class Ui(Steady):
            def choose_purchase(self, can): perguntas.append("p"); return "attack"
            def choose_card(self, player, hand): perguntas.append("c"); return 2

        gravado = []
        r = RoomRecorder(Ui(), [], gravado.append)
        self.assertEqual(r.choose_purchase(True), "attack")
        self.assertEqual(r.choose_card(None, []), 2)
        self.assertEqual(gravado[-1], ["attack", 2])
        repetido = RoomRecorder(Ui(), r.log)
        self.assertEqual((repetido.choose_purchase(True), repetido.choose_card(None, [])),
                         ("attack", 2))
        self.assertEqual(perguntas, ["p", "c"])          # o replay não perguntou nada
        self.assertFalse(repetido.replaying)

    def test_rewards_and_relics_are_stored_as_indexes(self):
        opcoes = [make_card("Firewall"), make_card("Segfault"), make_card("Sudo")]
        reliquias = [make_relic("Macro"), make_relic("Overvolt")]

        class Ui(Steady):
            def choose_reward(self, options, can_upgrade=False, mutation=None): return options[1]
            def choose_relic(self, options): return options[1]
        r = RoomRecorder(Ui(), [])
        r.choose_reward(opcoes, True)
        r.choose_relic(reliquias)
        self.assertEqual(r.log, [1, 1])
        repetido = RoomRecorder(Ui(), r.log)
        self.assertIs(repetido.choose_reward(opcoes, True), opcoes[1])
        self.assertIs(repetido.choose_relic(reliquias), reliquias[1])

    def test_refactor_and_none_roundtrip(self):
        opcoes = [make_card("Firewall")]

        class Ui(Steady):
            respostas = iter([REFACTOR_OPTION, None])
            def choose_reward(self, options, can_upgrade=False, mutation=None): return next(Ui.respostas)
        r = RoomRecorder(Ui(), [])
        r.choose_reward(opcoes, True)
        r.choose_reward(opcoes, True)
        repetido = RoomRecorder(Ui(), r.log)
        self.assertEqual(repetido.choose_reward(opcoes, True), REFACTOR_OPTION)
        self.assertIsNone(repetido.choose_reward(opcoes, True))

    def test_mutation_choices_roundtrip(self):
        opcoes = [make_card("Firewall")]
        pares = [(make_card("Segfault"), make_card("Segfault|Blindado"))] * 2

        class Ui(Steady):
            def choose_reward(self, options, can_upgrade=False, mutation=None): return MUTATE_OPTION
            def choose_mutation_target(self, mutation, pairs): return 1
        r = RoomRecorder(Ui(), [])
        r.choose_reward(opcoes, True, object())
        r.choose_mutation_target(None, pares)
        self.assertEqual(r.log, [MUTATE_OPTION, 1])
        repetido = RoomRecorder(Steady(), r.log)
        self.assertEqual(repetido.choose_reward(opcoes, True, object()), MUTATE_OPTION)
        self.assertEqual(repetido.choose_mutation_target(None, pares), 1)

    def test_nonsense_answers_raise_replay_error(self):
        opcoes = [make_card("Firewall")]
        casos = (lambda r: r.choose_reward(opcoes), lambda r: r.choose_relic([]),
                 lambda r: r.choose_card(None, []), lambda r: r.choose_discard([]),
                 lambda r: r.choose_upgrade([]), lambda r: r.choose_purchase(True),
                 lambda r: r.choose_mutation_target(None, []))
        respostas = (9, 0, "x", "x", 3, 7, 2)
        for chamar, resposta in zip(casos, respostas):
            with self.assertRaises(ReplayError):
                chamar(RoomRecorder(Steady(), [resposta]))


if __name__ == "__main__":
    unittest.main()
