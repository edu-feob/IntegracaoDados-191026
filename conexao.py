import os

import psycopg2
from dotenv import load_dotenv

# Lê o arquivo .env e coloca as variáveis dentro do ambiente do programa
load_dotenv()


def conectar():
    # Busca no .env a URL completa de conexão fornecida pelo NeonDB
    url = os.getenv("DATABASE_URL")

    # Se a variável não existir, avisa com uma mensagem clara
    if not url:
        raise RuntimeError("Variável DATABASE_URL não encontrada no arquivo .env")

    # O psycopg2 aceita a URL inteira (usuário, senha, host, banco e SSL)
    return psycopg2.connect(url)