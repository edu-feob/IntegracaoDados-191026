from pathlib import Path

from ofxparse import OfxParser

from conexao import conectar  # a conexão com o banco agora vive em conexao.py

# Categorias disponíveis: o usuário digita o número para escolher
CATEGORIAS = {
    "1": "Receita de Clientes",
    "2": "Aluguel",
    "3": "Contas Fixas",           # energia, internet, assinaturas
    "4": "Folha de Pagamento",
    "5": "Material e Equipamentos",
    "6": "Veículo e Transporte",
    "7": "Outros",
}

# Formas de pagamento: COMO o dinheiro foi movimentado
FORMAS_PAGAMENTO = {
    "1": "PIX",
    "2": "Boleto",
    "3": "TED/DOC",
    "4": "Cartão",
    "5": "Dinheiro",
    "6": "Outros",
}


def criar_tabela(conn):
    # "with conn" confirma (commit) as alterações ao final do bloco
    with conn:
        # "with conn.cursor()" cria o cursor e o fecha automaticamente
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS movimentacoes (
                    id SERIAL PRIMARY KEY,
                    data_movimentacao DATE,
                    valor NUMERIC(15,2),
                    descricao VARCHAR(255),
                    categoria VARCHAR(50),
                    fitid VARCHAR(100) UNIQUE   -- UNIQUE impede duplicados
                );
            """)
            # Se a tabela já existia sem a coluna, ela é adicionada aqui
            cur.execute("""
                ALTER TABLE movimentacoes
                ADD COLUMN IF NOT EXISTS forma_pagamento VARCHAR(30);
            """)


def escolher_categoria(t):
    # Mostra a transação para o usuário saber o que está classificando
    print("\n--------------------------------------")
    print(f"Data      : {t.date.strftime('%d/%m/%Y')}")
    print(f"Valor     : R$ {t.amount:.2f}")
    print(f"Descrição : {t.memo}")
    print("Categorias:")
    for numero, nome in CATEGORIAS.items():
        print(f"  {numero} - {nome}")

    # Repete a pergunta até o usuário digitar uma opção válida
    while True:
        opcao = input("Escolha a categoria: ").strip()
        if opcao in CATEGORIAS:
            return CATEGORIAS[opcao]
        print("Opção inválida, tente novamente.")


def sugerir_forma(memo):
    # Quebra a descrição em palavras para procurar pistas (ex.: "PIX CLIENTE OMEGA")
    palavras = (memo or "").upper().split()
    if "PIX" in palavras:
        return "1"
    if "BOLETO" in palavras:
        return "2"
    if "TED" in palavras:
        return "3"
    return ""  # sem sugestão


def escolher_forma_pagamento(t):
    sugestao = sugerir_forma(t.memo)

    print("Formas de pagamento:")
    for numero, nome in FORMAS_PAGAMENTO.items():
        print(f"  {numero} - {nome}")
    if sugestao:
        print(f"Sugestão: {FORMAS_PAGAMENTO[sugestao]} (Enter para aceitar)")

    while True:
        opcao = input("Escolha a forma de pagamento: ").strip()
        if opcao == "" and sugestao:      # Enter aceita a sugestão
            return FORMAS_PAGAMENTO[sugestao]
        if opcao in FORMAS_PAGAMENTO:
            return FORMAS_PAGAMENTO[opcao]
        print("Opção inválida, tente novamente.")


def ja_existe(cur, fitid):
    # Procura no banco uma transação com o mesmo identificador
    cur.execute("SELECT 1 FROM movimentacoes WHERE fitid = %s", (fitid,))
    return cur.fetchone() is not None  # True se encontrou algum registro


def main():
    # Monta o caminho a partir da pasta onde está o main.py:
    # ProjetoOFX/assets/extrato.ofx (funciona de qualquer pasta que você execute)
    caminho_ofx = Path(__file__).parent / "assets" / "extrato.ofx"

    # Lê o arquivo OFX
    with open(caminho_ofx, "rb") as arquivo:
        ofx = OfxParser.parse(arquivo)

    transacoes = ofx.account.statement.transactions
    print(f"Transações lidas do arquivo: {len(transacoes)}")

    conn = conectar()
    try:
        criar_tabela(conn)
        inseridas = 0
        ignoradas = 0

        with conn:
            with conn.cursor() as cur:
                for t in transacoes:
                    # Se já está no banco, não pergunta nem grava de novo
                    if ja_existe(cur, t.id):
                        ignoradas += 1
                        continue

                    categoria = escolher_categoria(t)
                    forma = escolher_forma_pagamento(t)

                    # Os %s são preenchidos pelos valores da tupla, o que
                    # protege contra SQL Injection (nunca use f-string aqui)
                    cur.execute(
                        """
                        INSERT INTO movimentacoes
                            (data_movimentacao, valor, descricao, categoria,
                             forma_pagamento, fitid)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        """,
                        (t.date.date(), t.amount, t.memo, categoria, forma, t.id),
                    )
                    conn.commit()  # grava agora; se interromper, o que já foi fica salvo
                    inseridas += 1

        print(f"\nInseridas: {inseridas} | Ignoradas (duplicadas): {ignoradas}")

        # Confirma no banco: nome do banco conectado e total de linhas na tabela
        with conn.cursor() as cur:
            cur.execute("SELECT current_database(), COUNT(*) FROM movimentacoes")
            banco, total = cur.fetchone()
            print(f"Banco: {banco} | Linhas na tabela movimentacoes: {total}")
    finally:
        # Garante que a conexão é fechada mesmo se ocorrer algum erro
        conn.close()


main()