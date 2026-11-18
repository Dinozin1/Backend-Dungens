"""
names.py - Filtro de nomes para os recordes (o jogo vai a público na exposição).

Os nomes são normalizados antes de comparar (sem acentos, maiúsculas, números
parecidos com letras e pontuação), para "P.u.t.4" ou "FÚCK" não passarem.
Palavras longas e muito específicas bloqueiam em qualquer posição; as restantes
só bloqueiam se forem o nome todo, o início ou o fim (assim "Computador" passa).
"""
import unicodedata

_LEET = str.maketrans("013457@$!", "oieastasi")

# Bloqueadas em qualquer posição do nome.
_ANYWHERE = ("nigger", "nigga", "faggot", "caralho", "fuck", "shit", "cunt",
             "paneleiro", "filhodaputa", "hitler")
# Bloqueadas se forem o nome todo, o início ou o fim.
_EDGES = ("puta", "merda", "foda", "fodase", "cabrao", "viado", "porra", "bitch",
          "nazi", "retard", "cona", "pila")


def _normalize(name):
    texto = unicodedata.normalize("NFKD", name.lower())
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = texto.translate(_LEET)
    return "".join(c for c in texto if "a" <= c <= "z")


def is_acceptable_name(name):
    """True se o nome pode aparecer nos recordes."""
    if not isinstance(name, str) or not name.strip():
        return False
    n = _normalize(name)
    if any(palavra in n for palavra in _ANYWHERE):
        return False
    return not any(n == p or n.startswith(p) or n.endswith(p) for p in _EDGES)
