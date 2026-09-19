import os
import re
import requests
from bs4 import BeautifulSoup

# ============================================================
# CONFIGURAÇÕES
# ============================================================

URL = "https://defesacivil.itajai.sc.gov.br/monitoramento/nivel-rios"

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

LIMITE_INICIAL = 1.65
INCREMENTO = 0.10

ARQUIVO_ESTADO = "estado.txt"


# ============================================================
# BUSCAR DC-04
# ============================================================

def obter_dc04():

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
    }

    resposta = requests.get(
        URL,
        headers=headers,
        timeout=30
    )

    resposta.raise_for_status()

    soup = BeautifulSoup(
        resposta.text,
        "html.parser"
    )

    # --------------------------------------------------------
    # PRIMEIRA TENTATIVA:
    # procura o texto DC-04 e sobe pelos elementos HTML
    # até encontrar o bloco que também contém "Nível do Rio"
    # --------------------------------------------------------

    encontrados = soup.find_all(
        string=re.compile(r"DC-04", re.IGNORECASE)
    )

    for item in encontrados:

        elemento = item.parent

        # Procura o bloco correto subindo alguns níveis
        for _ in range(8):

            if elemento is None:
                break

            bloco = elemento.get_text(
                " ",
                strip=True
            )

            bloco = re.sub(
                r"\s+",
                " ",
                bloco
            )

            if (
                "Nível do Rio" in bloco
                and "Data e hora da medição" in bloco
            ):

                resultado = re.search(
                    r"Nível do Rio\s*:\s*"
                    r"([0-9]+[,.][0-9]+)\s*m",
                    bloco,
                    re.IGNORECASE
                )

                data_hora = re.search(
                    r"Data e hora da medição\s*:\s*"
                    r"([0-9/]+)\s+([0-9:]+)",
                    bloco,
                    re.IGNORECASE
                )

                if resultado and data_hora:

                    nivel = float(
                        resultado.group(1)
                        .replace(",", ".")
                    )

                    data = data_hora.group(1)
                    hora = data_hora.group(2)

                    return nivel, data, hora

            elemento = elemento.parent

    # --------------------------------------------------------
    # SEGUNDA TENTATIVA:
    # procura tudo no texto da página
    # --------------------------------------------------------

    texto = soup.get_text(
        " ",
        strip=True
    )

    texto = re.sub(
        r"\s+",
        " ",
        texto
    )

    padrao = (
        r"DC-04.*?"
        r"Nível do Rio\s*:\s*"
        r"([0-9]+[,.][0-9]+)\s*m.*?"
        r"Data e hora da medição\s*:\s*"
        r"([0-9/]+)\s+([0-9:]+)"
    )

    resultado = re.search(
        padrao,
        texto,
        re.IGNORECASE
    )

    if resultado:

        nivel = float(
            resultado.group(1)
            .replace(",", ".")
        )

        data = resultado.group(2)
        hora = resultado.group(3)

        return nivel, data, hora

    # --------------------------------------------------------
    # SE CHEGAR AQUI, A PÁGINA RESPONDEU MAS NÃO CONSEGUIMOS
    # LOCALIZAR O DC-04
    # --------------------------------------------------------

    trecho = texto[:2000]

    raise RuntimeError(
        "Não foi possível localizar os dados do DC-04. "
        "Primeiros dados recebidos pelo site:\n"
        + trecho
    )


# ============================================================
# TELEGRAM
# ============================================================

def enviar_telegram(mensagem):

    url = (
        f"https://api.telegram.org/"
        f"bot{BOT_TOKEN}/sendMessage"
    )

    resposta = requests.post(
        url,
        data={
            "chat_id": CHAT_ID,
            "text": mensagem,
        },
        timeout=30
    )

    resposta.raise_for_status()


# ============================================================
# ESTADO
# ============================================================

def carregar_estado():

    if not os.path.exists(
        ARQUIVO_ESTADO
    ):
        return -1

    try:

        with open(
            ARQUIVO_ESTADO,
            "r",
            encoding="utf-8"
        ) as arquivo:

            return int(
                arquivo.read().strip()
            )

    except Exception:

        return -1


def salvar_estado(patamar):

    with open(
        ARQUIVO_ESTADO,
        "w",
        encoding="utf-8"
    ) as arquivo:

        arquivo.write(
            str(patamar)
        )


# ============================================================
# PATAMAR
# ============================================================

def calcular_patamar(nivel):

    if nivel < LIMITE_INICIAL:
        return -1

    return int(
        (
            nivel
            - LIMITE_INICIAL
            + 0.000001
        )
        / INCREMENTO
    )


# ============================================================
# EXECUÇÃO
# ============================================================

try:

    nivel, data, hora = obter_dc04()

    patamar_atual = calcular_patamar(
        nivel
    )

    patamar_anterior = carregar_estado()

    print(
        f"DC-04: {nivel:.2f} m | "
        f"Medição: {data} {hora} | "
        f"Patamar atual: {patamar_atual} | "
        f"Patamar anterior: {patamar_anterior}"
    )

    # --------------------------------------------------------
    # NOVO PATAMAR
    # --------------------------------------------------------

    if patamar_atual > patamar_anterior:

        limite_atingido = (
            LIMITE_INICIAL
            + (
                patamar_atual
                * INCREMENTO
            )
        )

        mensagem = (
            "🚨🚨 ALERTA DC-04 🚨🚨\n\n"
            f"🌊 Nível atual: {nivel:.2f} m\n"
            f"📍 Vitalmar Pescados\n"
            f"🕐 Medição: {data} {hora}\n\n"
            f"⚠️ Limite atingido: "
            f"{limite_atingido:.2f} m"
        )

        enviar_telegram(
            mensagem
        )

        salvar_estado(
            patamar_atual
        )

        print(
            f"ALERTA ENVIADO: "
            f"{limite_atingido:.2f} m"
        )

    # --------------------------------------------------------
    # NÍVEL ABAIXOU
    # --------------------------------------------------------

    elif patamar_atual < patamar_anterior:

        salvar_estado(
            patamar_atual
        )

        print(
            "Nível caiu. Estado atualizado."
        )

    # --------------------------------------------------------
    # SEM NOVO ALERTA
    # --------------------------------------------------------

    else:

        print(
            "Nenhum novo alerta necessário."
        )


except Exception as erro:

    print(
        "ERRO NO MONITORAMENTO:"
    )

    print(
        str(erro)
    )

    raise