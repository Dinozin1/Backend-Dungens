"""
ui.py - Interface em modo texto (consola), sem bibliotecas externas.

Toda a comunicação com o jogador (print/input) vive aqui. A lógica do jogo
só chama estes métodos, por isso mais tarde basta escrever uma classe com
os mesmos métodos em pygame para ter a versão 2D. A versão colorida
(ui_rich.py) herda desta classe e só redefine a parte visual.
"""
import config
from cards import REFACTOR_OPTION
from modes import MODES


class QuitGame(Exception):
    """Lançada quando o jogador quer sair (ou o input acaba)."""


class TextUI:
    # ---------- entrada validada (R4: entrada errada não rebenta o jogo) ----------
    def _ask(self, prompt, valid):
        """Pergunta até receber uma resposta que esteja na lista 'valid'."""
        while True:
            try:
                resposta = input(prompt).strip().lower()
            except EOFError:
                raise QuitGame
            if resposta in valid:
                return resposta
            print(f"  Opção inválida. Escolhe uma de: {', '.join(valid)}")

    def ask_name(self):
        while True:
            try:
                nome = input("Como se chama o programador? ").strip()
            except EOFError:
                raise QuitGame
            if nome:
                return nome[:config.PLAYER_NAME_MAX]
            print("  O nome não pode estar vazio.")

    # ---------- menus ----------
    def main_menu(self, has_save=False):
        """Devolve a chave do modo escolhido, ou 'continue', 'hall', 'help', 'quit'."""
        print("\n" + "=" * 44)
        print("        BACKEND DUNGEONS")
        print("  Limpa o sistema infetado, sala a sala!")
        print("=" * 44)
        opcoes = [(m.key, f"Jogar - {m.label}") for m in MODES.values()]
        if has_save:
            opcoes.append(("continue", "Continuar a run guardada"))
        opcoes += [("hall", "Recordes"), ("help", "Como jogar"), ("quit", "Sair")]
        for i, (_, texto) in enumerate(opcoes, 1):
            print(f" {i}) {texto}")
        escolha = self._ask("> ", [str(i) for i in range(1, len(opcoes) + 1)])
        return opcoes[int(escolha) - 1][0]

    def show_help(self):
        print(f"""
COMO JOGAR
- Percorres 10 salas (modo normal) ou 5 (modo rápido); na última está o boss.
- Cada turno: compras 1 carta e depois jogas as que quiseres. Podes comprar:
  básica de ataque, básica de defesa ou uma carta do teu BARALHO (onde estão as
  cartas especiais que foste ganhando como recompensa).
- A ENERGIA não se perde no fim do turno: podes poupar para jogadas fortes
  (ganhas +{config.ENERGY_PER_TURN} por turno, máximo {config.MAX_ENERGY}).
- O BLOQUEIO e o PARRY desaparecem no início do teu turno.
- Mão máxima: {config.HAND_LIMIT} cartas.
- Depois de cada combate: 1 carta entre 3 OU REFACTOR (melhora uma carta, ex.: Segfault -> Segfault+).
- Há cartas e relíquias de RISCO: muito poder, mas com um preço. Veneno ignora o bloqueio.
- RELÍQUIAS: em certas salas escolhes 1 de 2; mudam as regras até ao fim da run.
- Depois do turno {config.ENRAGE_TURN} os inimigos enfurecem-se (+1 de dano por turno).
- O boss esconde as ações, mas segue um padrão. Observa o histórico!
- A run é gravada depois de cada combate: podes sair e continuar mais tarde.""")

    def show_hall(self, tables, warning=""):
        """tables = lista de (título, [ScoreEntry...]), uma tabela por modo."""
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

    def choose_purchase(self, can_draw_deck):
        print("\nCompra do turno (escolhe 1):")
        print(' 1) Carta básica de ATAQUE   - Print("Hit")')
        print(" 2) Carta básica de DEFESA   - If/Else")
        validas = ["1", "2"]
        if can_draw_deck:
            print(" 3) Carta do teu BARALHO     (o que construíste na run)")
            validas.append("3")
        return {"1": "attack", "2": "defense", "3": "deck"}[self._ask("> ", validas)]

    def choose_card(self, player, hand):
        """Devolve o índice da carta a jogar, ou None para terminar o turno."""
        print(f"\nMão (energia {player.energy}):")
        for i, carta in enumerate(hand, 1):
            aviso = "" if player.can_afford(carta.cost) else "  (sem energia)"
            print(f" {i}) {carta}{aviso}")
        print(" 0) Terminar turno")
        validas = ["0"] + [str(i) for i in range(1, len(hand) + 1)]
        escolha = int(self._ask("> ", validas))
        return None if escolha == 0 else escolha - 1

    def choose_discard(self, hand):
        print(f"\nA mão passou de {config.HAND_LIMIT} cartas! Descarta uma:")
        for i, carta in enumerate(hand, 1):
            print(f" {i}) {carta}")
        validas = [str(i) for i in range(1, len(hand) + 1)]
        return int(self._ask("> ", validas)) - 1

    def choose_reward(self, options, can_upgrade=False):
        """
        Recompensa de fim de combate. Devolve uma Carta (nova no baralho),
        REFACTOR_OPTION (melhorar uma carta que já tens) ou None (nada).
        """
        print("\nRecompensa! Escolhe uma carta para o baralho:")
        for i, carta in enumerate(options, 1):
            print(f" {i}) {carta}")
        validas = ["0"] + [str(i) for i in range(1, len(options) + 1)]
        refactor = str(len(options) + 1)
        if can_upgrade:
            print(f" {refactor}) REFACTOR: melhora uma carta do teu baralho")
            validas.append(refactor)
        print(" 0) Nenhuma (mantém o baralho pequeno)")
        escolha = self._ask("> ", validas)
        if escolha == "0":
            return None
        if can_upgrade and escolha == refactor:
            return REFACTOR_OPTION
        return options[int(escolha) - 1]

    def choose_upgrade(self, pairs):
        """pairs = [(carta atual, carta melhorada)]. Devolve o índice ou None (voltar)."""
        print("\nREFACTOR - que carta queres melhorar?")
        for i, (antes, depois) in enumerate(pairs, 1):
            print(f" {i}) {antes}\n      => {depois}")
        print(" 0) Voltar atrás")
        validas = ["0"] + [str(i) for i in range(1, len(pairs) + 1)]
        escolha = int(self._ask("> ", validas))
        return None if escolha == 0 else escolha - 1

    def choose_relic(self, options):
        """Escolhe 1 relíquia (obrigatório). Devolve a relíquia."""
        print("\nENCONTRASTE UMA RELÍQUIA! Escolhe uma (dura até ao fim da run):")
        for i, relic in enumerate(options, 1):
            print(f" {i}) {relic}")
        validas = [str(i) for i in range(1, len(options) + 1)]
        return options[int(self._ask("> ", validas)) - 1]

    def message(self, text):
        print(text)
