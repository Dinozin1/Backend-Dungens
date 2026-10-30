"""main.py - Ponto de entrada. Corre com:  python main.py"""
from game import Game
from ui import QuitGame


def main():
    try:
        Game().menu()
    except (QuitGame, KeyboardInterrupt):
        print("\nJogo terminado. Até breve!")


if __name__ == "__main__":
    main()
