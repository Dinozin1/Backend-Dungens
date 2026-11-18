"""
fileutil.py - Escrita segura de ficheiros (R4).

Escrever diretamente no ficheiro final é arriscado: se o jogo fechar a meio da
escrita, o ficheiro fica cortado ou vazio. Aqui escrevemos primeiro num ficheiro
temporário e só depois o trocamos pelo final (os.replace é atómico): o ficheiro
final ou tem o conteúdo antigo completo ou o novo completo, nunca meio escrito.
"""
import os


def write_text_atomic(path, text):
    """Grava 'text' em 'path' de forma atómica. Lança OSError se não conseguir."""
    tmp = path.with_name(path.name + ".tmp")
    try:
        tmp.write_text(text, encoding="utf-8")
        os.replace(tmp, path)
    except OSError:
        try:
            tmp.unlink(missing_ok=True)      # não deixa lixo para trás
        except OSError:
            pass
        raise
