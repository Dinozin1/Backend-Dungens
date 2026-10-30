"""
ui.py - Interface em modo texto (consola).

Toda a comunicação com o jogador (print/input) vive aqui. A lógica do jogo
só chama estes métodos, por isso mais tarde basta escrever uma classe com
os mesmos métodos em pygame para ter a versão 2D.
"""
import config


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
    def main_menu(self):
        print("\n" + "=" * 44)
        print("        BACKEND DUNGEONS")
        print("  Limpa o sistema infetado, sala a sala!")
        print("=" * 44)
        print(" 1) Jogar\n 2) Recordes\n 3) Como jogar\n 4) Sair")
        return self._ask("> ", ["1", "2", "3", "4"])

    def show_help(self):
        print(f"""
COMO JOGAR
- Percorres {config.TOTAL_ROOMS} salas; na última está o boss.
- Cada turno: compras 1 carta e depois jogas as que quiseres.
- A ENERGIA não se perde no fim do turno: podes poupar para jogadas fortes
  (ganhas +{config.ENERGY_PER_TURN} por turno, máximo {config.MAX_ENERGY}).
- O BLOQUEIO e o PARRY desaparecem no início do teu turno.
- Compra: carta básica (ataque ou defesa) ou uma carta ESPECIAL aleatória.
- Mão máxima: {config.HAND_LIMIT} cartas. Depois de cada combate escolhes 1 carta entre 3.
- O boss esconde as ações, mas segue um padrão. Observa o histórico!""")

    def show_hall(self, entries, warning=""):
        print("\n--- RECORDES ---")
        if warning:
            print(f"(aviso: {warning})")
        if not entries:
            print("Ainda não há recordes. Sê o primeiro!")
        for i, e in enumerate(entries, 1):
            estado = "VITÓRIA" if e.won else f"sala {e.rooms}"
            print(f"{i:>2}. {e.name:<12} {e.score:>5} pontos  ({estado})")

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

    def choose_purchase(self):
        print("\nCompra do turno (escolhe 1):")
        print(' 1) Carta básica de ATAQUE   - Print("Hit")')
        print(" 2) Carta básica de DEFESA   - If/Else")
        print(" 3) Carta ESPECIAL aleatória (aposta: pode ser ótima ou inútil)")
        return {"1": "attack", "2": "defense", "3": "special"}[
            self._ask("> ", ["1", "2", "3"])]

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

    def choose_reward(self, options):
        """Escolhe 1 carta entre as opções (ou nenhuma). Devolve a carta ou None."""
        print("\nRecompensa! Escolhe uma carta para o baralho:")
        for i, carta in enumerate(options, 1):
            print(f" {i}) {carta}")
        print(" 0) Nenhuma (mantém o baralho pequeno)")
        validas = ["0"] + [str(i) for i in range(1, len(options) + 1)]
        escolha = int(self._ask("> ", validas))
        return None if escolha == 0 else options[escolha - 1]

    def message(self, text):
        print(text)
