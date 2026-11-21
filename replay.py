"""
replay.py - Retomar uma sala a meio, sem batota (anti "save scumming").

Problema: se só gravássemos entre salas, sair a meio de um combate difícil e
"continuar" repunha o estado anterior e deixava tentar outra vez.

Solução: cada sala corre com uma SEMENTE (o rng do jogo é reiniciado com ela) e
tudo o que o jogador responde nessa sala é gravado, resposta a resposta. Para
retomar, a sala volta a correr com a mesma semente e as respostas gravadas são
repetidas em silêncio; quando acabam, o jogador continua no mesmo ponto, com as
mesmas cartas na mão e o mesmo inimigo. Sair já não muda nada.

O RoomRecorder é um "decorator": tem a interface RunUI, embrulha a interface
verdadeira e, ao Battle e ao Game, parece uma interface normal.
"""
from cards import MUTATE_OPTION, REFACTOR_OPTION
from ui import RunUI


class ReplayError(Exception):
    """A resposta gravada não faz sentido neste ponto (ficheiro adulterado)."""


def _is_int(valor):
    return isinstance(valor, int) and not isinstance(valor, bool)


class RoomRecorder(RunUI):
    def __init__(self, ui, log=(), on_change=None):
        self._ui = ui
        self._log = list(log)          # respostas gravadas (JSON simples)
        self._pos = 0                  # quantas já foram repetidas/dadas
        self._on_change = on_change    # chamado a cada resposta nova (grava o ficheiro)
        self._hidden_state = None      # último show_state escondido durante o replay

    @property
    def log(self):
        return list(self._log)

    @property
    def replaying(self):
        return self._pos < len(self._log)

    # ---------- o que não é uma decisão: passa direto (calado durante o replay) ----------
    def ask_name(self):
        return self._ui.ask_name()

    def confirm(self, question):
        return self._ui.confirm(question)

    def message(self, text):
        if not self.replaying:
            self._ui.message(text)

    def show_state(self, player, enemy, turn):
        if self.replaying:
            self._hidden_state = (player, enemy, turn)
        else:
            self._hidden_state = None
            self._ui.show_state(player, enemy, turn)

    # ---------- as decisões: repetidas do log ou perguntadas e gravadas ----------
    def _decide(self, ask, encode, decode):
        if self.replaying:
            raw = self._log[self._pos]
            self._pos += 1
            return decode(raw)
        resposta = ask()
        self._log.append(encode(resposta))
        self._pos += 1
        if self._on_change:
            self._on_change(self._log)
        return resposta

    def _resume_screen(self):
        """Primeira pergunta ao vivo a meio de um turno: volta a mostrar o ecrã."""
        if self._hidden_state is not None and not self.replaying:
            self._ui.message("\n(Combate retomado no ponto onde ficou.)")
            self._ui.show_state(*self._hidden_state)
            self._hidden_state = None

    def choose_purchase(self, can_draw_deck):
        def decode(raw):
            if not isinstance(raw, str):
                raise ReplayError("compra inválida")
            return raw
        return self._decide(lambda: self._ui.choose_purchase(can_draw_deck),
                            lambda r: r, decode)

    def choose_card(self, player, hand):
        def ask():
            self._resume_screen()
            return self._ui.choose_card(player, hand)

        def decode(raw):
            if raw is not None and not _is_int(raw):
                raise ReplayError("carta inválida")
            return raw
        return self._decide(ask, lambda r: r, decode)

    def choose_discard(self, hand):
        def ask():
            self._resume_screen()
            return self._ui.choose_discard(hand)

        def decode(raw):
            if not _is_int(raw):
                raise ReplayError("descarte inválido")
            return raw
        return self._decide(ask, lambda r: r, decode)

    def choose_reward(self, options, can_upgrade=False, mutation=None):
        def encode(escolha):
            if escolha is None or escolha in (REFACTOR_OPTION, MUTATE_OPTION):
                return escolha
            return options.index(escolha)

        def decode(raw):
            if raw is None or raw in (REFACTOR_OPTION, MUTATE_OPTION):
                return raw
            if not _is_int(raw) or not 0 <= raw < len(options):
                raise ReplayError("recompensa inválida")
            return options[raw]
        return self._decide(lambda: self._ui.choose_reward(options, can_upgrade, mutation),
                            encode, decode)

    def choose_upgrade(self, pairs):
        def decode(raw):
            if raw is not None and (not _is_int(raw) or not 0 <= raw < len(pairs)):
                raise ReplayError("melhoria inválida")
            return raw
        return self._decide(lambda: self._ui.choose_upgrade(pairs), lambda r: r, decode)

    def choose_mutation_target(self, mutation, pairs):
        def decode(raw):
            if raw is not None and (not _is_int(raw) or not 0 <= raw < len(pairs)):
                raise ReplayError("alvo de mutação inválido")
            return raw
        return self._decide(lambda: self._ui.choose_mutation_target(mutation, pairs),
                            lambda r: r, decode)

    def choose_relic(self, options):
        def decode(raw):
            if not _is_int(raw) or not 0 <= raw < len(options):
                raise ReplayError("relíquia inválida")
            return options[raw]
        return self._decide(lambda: self._ui.choose_relic(options),
                            options.index, decode)
