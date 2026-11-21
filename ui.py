"""
ui.py - Contrato das interfaces (RunUI e GameUI) e a interface em modo texto.

Toda a comunicação com o jogador (print/input) vive nas interfaces. A lógica
(Game, Battle) só chama os métodos abaixo, por isso trocar o ecrã não obriga a
reescrever o jogo:

  RunUI   - o que uma run precisa (nome, combate, recompensas). Os bots do
            simulate.py implementam só isto.
  GameUI  - RunUI + os menus (menu principal, ajuda, recordes).
  TextUI  - GameUI em texto simples, sem bibliotecas externas.
  RichUI  - (ui_rich.py) herda de TextUI e só redefine a parte VISUAL.

Padrão "template method": TextUI.choose_card() mostra a mão (_show_hand) e valida a
resposta; as subclasses redefinem só o _show_*, a validação (R4) fica igual.
"""
from abc import ABC, abstractmethod

import config
from cards import BASIC_ATTACK, BASIC_DEFENSE, MUTATE_OPTION, REFACTOR_OPTION
from modes import MODES
from names import is_acceptable_name


class QuitGame(Exception):
    """Lançada quando o jogador quer sair (ou o input acaba)."""


class RunUI(ABC):
    """O que uma run precisa de uma interface (jogador humano ou bot)."""

    @abstractmethod
    def ask_name(self):
        """Devolve o nome do jogador (já validado)."""

    @abstractmethod
    def confirm(self, question):
        """Pergunta sim/não. Devolve True para sim."""

    @abstractmethod
    def message(self, text):
        """Mostra uma mensagem do jogo."""

    @abstractmethod
    def show_state(self, player, enemy, turn):
        """Mostra o estado do combate no início do turno."""

    @abstractmethod
    def choose_purchase(self, can_draw_deck):
        """Devolve 'attack', 'defense' ou 'deck' (só se can_draw_deck)."""

    @abstractmethod
    def choose_card(self, player, hand):
        """Devolve o índice da carta a jogar, ou None para terminar o turno."""

    @abstractmethod
    def choose_discard(self, hand):
        """Devolve o índice da carta a descartar."""

    @abstractmethod
    def choose_reward(self, options, can_upgrade=False, mutation=None):
        """
        Devolve uma Carta, REFACTOR_OPTION (se can_upgrade), MUTATE_OPTION (só se
        'mutation' não for None: é a mutação oferecida) ou None (nada).
        """

    @abstractmethod
    def choose_upgrade(self, pairs):
        """pairs = [(carta atual, carta melhorada)]. Devolve o índice ou None (voltar)."""

    @abstractmethod
    def choose_mutation_target(self, mutation, pairs):
        """pairs = [(carta atual, carta já mutada)]. Devolve o índice ou None (voltar)."""

    @abstractmethod
    def choose_relic(self, options):
        """Devolve a relíquia escolhida (obrigatório)."""


class GameUI(RunUI):
    """RunUI + os menus do jogo."""

    @abstractmethod
    def main_menu(self, has_save=False):
        """Devolve a chave de um modo, ou 'continue', 'hall', 'help' ou 'quit'."""

    @abstractmethod
    def show_help(self):
        """Mostra as instruções."""

    @abstractmethod
    def show_hall(self, tables, warning=""):
        """tables = lista de (título, [ScoreEntry...]), uma tabela por modo."""


class TextUI(GameUI):
    # ---------- entrada validada (R4: entrada errada não rebenta o jogo) ----------
    def _read(self, prompt):
        """Lê uma linha. As subclasses podem mudar o aspeto da pergunta."""
        try:
            return input(prompt)
        except EOFError:
            raise QuitGame

    def _ask(self, prompt, valid):
        """Pergunta até receber uma resposta que esteja na lista 'valid'."""
        while True:
            resposta = self._read(prompt).strip().lower()
            if resposta in valid:
                return resposta
            self.message(f"  Opção inválida. Escolhe uma de: {', '.join(valid)}")

    def ask_name(self):
        while True:
            nome = self._read("Como se chama o programador? ").strip()
            nome = nome[:config.PLAYER_NAME_MAX]
            if not nome:
                self.message("  O nome não pode estar vazio.")
            elif not is_acceptable_name(nome):
                self.message("  Esse nome não é permitido. Escolhe outro.")
            else:
                return nome

    def confirm(self, question):
        return self._ask(f"{question} (s/n) ", ["s", "n"]) == "s"

    def message(self, text):
        print(text)

    # ---------- menus ----------
    @staticmethod
    def _menu_options(has_save):
        opcoes = [(m.key, f"Jogar - {m.label}") for m in MODES.values()]
        if has_save:
            opcoes.append(("continue", "Continuar a run guardada"))
        return opcoes + [("hall", "Recordes"), ("help", "Como jogar"), ("quit", "Sair")]

    def _show_menu(self, opcoes):
        print("\n" + "=" * 44)
        print("        BACKEND DUNGEONS")
        print("  Limpa o sistema infetado, sala a sala!")
        print("=" * 44)
        for i, (_, texto) in enumerate(opcoes, 1):
            print(f" {i}) {texto}")

    def main_menu(self, has_save=False):
        opcoes = self._menu_options(has_save)
        self._show_menu(opcoes)
        escolha = self._ask("> ", [str(i) for i in range(1, len(opcoes) + 1)])
        return opcoes[int(escolha) - 1][0]

    @staticmethod
    def help_text():
        modos = " ou ".join(m.label for m in MODES.values())
        return f"""- Percorres várias salas (modos: {modos}); na última está o boss.
- Cada turno: compras 1 carta e depois jogas as que quiseres. Podes comprar:
  básica de ataque, básica de defesa ou uma carta do teu BARALHO (onde estão as
  cartas especiais que foste ganhando como recompensa).
- A ENERGIA não se perde no fim do turno: podes poupar para jogadas fortes
  (ganhas +{config.ENERGY_PER_TURN} por turno, máximo {config.MAX_ENERGY}).
- O BLOQUEIO e o PARRY desaparecem no início do teu turno.
- Mão máxima: {config.HAND_LIMIT} cartas.
- Depois de cada combate: 1 carta entre 3, OU REFACTOR (melhora uma carta, ex.: Segfault -> Segfault+),
  OU uma MUTAÇÃO (uma carta ganha um efeito novo, sempre com um preço; só uma por carta).
- Há cartas e relíquias de RISCO: muito poder, mas com um preço. Veneno ignora o bloqueio.
- Cuidado com os inimigos: alguns envenenam-te, roubam a energia que guardaste ou enchem o descarte de Spam.
- RELÍQUIAS: em certas salas escolhes 1 de 2; mudam as regras até ao fim da run.
- Depois do turno {config.ENRAGE_TURN} os inimigos enfurecem-se (+1 de dano por turno).
- O boss esconde as ações, mas segue um padrão. Observa o histórico!
- A run é gravada depois de cada combate: podes sair e continuar mais tarde."""

    def show_help(self):
        print("\nCOMO JOGAR\n" + self.help_text())

    def show_hall(self, tables, warning=""):
        print("\n--- RECORDES ---")
        if warning:
            print(f"(aviso: {warning})")
        for titulo, entradas in tables:
            print(f"\n{titulo}")
            if not entradas:
                print("  Ainda não há recordes.")
            for i, e in enumerate(entradas, 1):
                estado = "VITÓRIA" if e.won else f"sala {e.rooms}"
                print(f" {i:>2}. {e.name:<12} {e.score:>5} pontos  ({estado})")

    # ---------- combate ----------
    @staticmethod
    def _bar(valor, maximo, tamanho=20):
        cheio = round(tamanho * valor / maximo) if maximo else 0
        return "[" + "#" * cheio + "-" * (tamanho - cheio) + "]"

    def show_state(self, player, enemy, turn):
        print("\n" + "-" * 50)
        print(f"TURNO {turn}")
        print(f"{enemy.name:<12} {self._bar(enemy.hp, enemy.max_hp)} "
              f"{enemy.hp}/{enemy.max_hp}  bloqueio {enemy.block}  "
              f"estados: {enemy.status_text()}")
        print(f"  Intenção: {enemy.describe_intent()}")
        print(f"{player.name:<12} {self._bar(player.hp, player.max_hp)} "
              f"{player.hp}/{player.max_hp}  bloqueio {player.block}  "
              f"estados: {player.status_text()}")
        print(f"  Energia: {player.energy}/{config.MAX_ENERGY}   "
              f"Baralho: {player.deck.draw_pile_size}  "
              f"Descarte: {player.deck.discard_size}")
        if player.relics:
            print("  Relíquias: " + ", ".join(r.name for r in player.relics))

    def _show_purchase(self, can_draw_deck):
        print("\nCompra do turno (escolhe 1):")
        print(f" 1) Carta básica de ATAQUE   - {BASIC_ATTACK}")
        print(f" 2) Carta básica de DEFESA   - {BASIC_DEFENSE}")
        if can_draw_deck:
            print(" 3) Carta do teu BARALHO     (o que construíste na run)")

    def choose_purchase(self, can_draw_deck):
        self._show_purchase(can_draw_deck)
        validas = ["1", "2"] + (["3"] if can_draw_deck else [])
        return {"1": "attack", "2": "defense", "3": "deck"}[self._ask("> ", validas)]

    def _show_hand(self, player, hand):
        print(f"\nMão (energia {player.energy}):")
        for i, carta in enumerate(hand, 1):
            aviso = "" if player.can_afford(carta.cost) else "  (sem energia)"
            print(f" {i}) {carta}{aviso}")
        print(" 0) Terminar turno")

    def choose_card(self, player, hand):
        self._show_hand(player, hand)
        validas = ["0"] + [str(i) for i in range(1, len(hand) + 1)]
        escolha = int(self._ask("> ", validas))
        return None if escolha == 0 else escolha - 1

    def _show_discard(self, hand):
        print(f"\nA mão passou de {config.HAND_LIMIT} cartas! Descarta uma:")
        for i, carta in enumerate(hand, 1):
            print(f" {i}) {carta}")

    def choose_discard(self, hand):
        self._show_discard(hand)
        validas = [str(i) for i in range(1, len(hand) + 1)]
        return int(self._ask("> ", validas)) - 1

    @staticmethod
    def _reward_numbers(options, can_upgrade, mutation):
        """Números das opções especiais do menu (None se não estão disponíveis)."""
        proximo = len(options) + 1
        refactor = proximo if can_upgrade else None
        mutar = proximo + (1 if can_upgrade else 0) if mutation is not None else None
        return refactor, mutar

    def _show_reward(self, options, can_upgrade, mutation=None):
        print("\nRecompensa! Escolhe uma carta para o baralho:")
        for i, carta in enumerate(options, 1):
            print(f" {i}) {carta}")
        refactor, mutar = self._reward_numbers(options, can_upgrade, mutation)
        if refactor:
            print(f" {refactor}) REFACTOR: melhora uma carta do teu baralho")
        if mutar:
            print(f" {mutar}) MUTAÇÃO ({mutation}) numa carta do teu baralho")
        print(" 0) Nenhuma (mantém o baralho pequeno)")

    def choose_reward(self, options, can_upgrade=False, mutation=None):
        """Recompensa de fim de combate: Carta, REFACTOR_OPTION, MUTATE_OPTION ou None."""
        self._show_reward(options, can_upgrade, mutation)
        refactor, mutar = self._reward_numbers(options, can_upgrade, mutation)
        validas = ["0"] + [str(i) for i in range(1, len(options) + 1)]
        validas += [str(n) for n in (refactor, mutar) if n]
        escolha = self._ask("> ", validas)
        if escolha == "0":
            return None
        if refactor and escolha == str(refactor):
            return REFACTOR_OPTION
        if mutar and escolha == str(mutar):
            return MUTATE_OPTION
        return options[int(escolha) - 1]

    def _show_mutation_target(self, mutation, pairs):
        print(f"\nMUTAÇÃO ({mutation}) - em que carta?")
        for i, (antes, depois) in enumerate(pairs, 1):
            print(f" {i}) {antes}\n      => {depois}")
        print(" 0) Voltar atrás")

    def choose_mutation_target(self, mutation, pairs):
        self._show_mutation_target(mutation, pairs)
        validas = ["0"] + [str(i) for i in range(1, len(pairs) + 1)]
        escolha = int(self._ask("> ", validas))
        return None if escolha == 0 else escolha - 1

    def _show_upgrades(self, pairs):
        print("\nREFACTOR - que carta queres melhorar?")
        for i, (antes, depois) in enumerate(pairs, 1):
            print(f" {i}) {antes}\n      => {depois}")
        print(" 0) Voltar atrás")

    def choose_upgrade(self, pairs):
        self._show_upgrades(pairs)
        validas = ["0"] + [str(i) for i in range(1, len(pairs) + 1)]
        escolha = int(self._ask("> ", validas))
        return None if escolha == 0 else escolha - 1

    def _show_relics(self, options):
        print("\nENCONTRASTE UMA RELÍQUIA! Escolhe uma (dura até ao fim da run):")
        for i, relic in enumerate(options, 1):
            print(f" {i}) {relic}")

    def choose_relic(self, options):
        self._show_relics(options)
        validas = [str(i) for i in range(1, len(options) + 1)]
        return options[int(self._ask("> ", validas)) - 1]
