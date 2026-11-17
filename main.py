"""
main.py - Ponto de entrada.

  python main.py            # usa cores se o "rich" estiver instalado
  python main.py --plain    # força o modo texto simples
"""
import sys

from game import Game
from ui import QuitGame, TextUI


def choose_ui():
    """Interface colorida se houver 'rich' (pip install rich); senão texto simples."""
    if "--plain" not in sys.argv:
        try:
            from ui_rich import RichUI
            return RichUI()
        except ImportError:
            pass
    return TextUI()


def main():
    try:
        Game(ui=choose_ui()).menu()
    except (QuitGame, KeyboardInterrupt):
        print("\nJogo terminado. Até breve! (A run fica gravada, podes continuar.)")


if __name__ == "__main__":
    main()
