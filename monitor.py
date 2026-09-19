import os
import re
import requests
from bs4 import BeautifulSoup

URL = "https://defesacivil.itajai.sc.gov.br/monitoramento/nivel-rios"

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

LIMITE_INICIAL = 1.65
INCREMENTO = 0.10
ARQUIVO_ESTADO = "estado.txt"


def obter_dc04():
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/140.0 Safari/537.36"
        )
    }

    resposta = requests.get(
        URL,
        headers=headers,
        timeout=30
    )

    resposta.raise_for_status()

    # DIAGNÓSTICO
    print("STATUS:", resposta.status_code)
    print("URL FINAL:", resposta.url)
    print("TAMANHO DA RESPOSTA:", len(resposta.text))
    print("INÍCIO DA RESPOSTA:")
    print(resposta.text[:5000])

    soup = BeautifulSoup(resposta.text, "html.parser")

    # Primeiro tenta encontrar diretamente algum elemento
    # que contenha "DC-04".
    encontrados = soup.find_all(
        string=re.compile(r"DC-04", re.IGNORECASE)
    )

    for encontrado in encontrados:
        elemento = encontrado.parent

        # Sobe alguns níveis procurando o bloco que contém
        # as informações da estação.
        for _ in range(6):
            if elemento is None:
                break

            texto = elemento.get_text(
                " ",
                strip=True
            )

            if (
                "DC-04" in texto
                and "Nível do Rio" in texto
                and "Data e hora da medição" in texto
            ):
                padrao = re.search(
                    r"Nível do Rio:\s*([0-9]+,[0-9]+)\s*m",
                    texto
                )

                data_hora = re.search(
                    r"Data e hora da medição:\s*"
                    r"([0-9/]+)\s+([0-9:]+)",
                    texto
                )

                if padrao and data_hora:
                    nivel = float(
                        padrao.group(1).replace(",", ".")
                    )

                    data = data_hora.group(1)
                    hora = data_hora.group(2)

                    return nivel, data, hora

            elemento = elemento.parent

    # Fallback: procura diretamente no texto completo da página.
    texto = soup.get_text(
        " ",
        strip=True
    )

    padrao = re.search(
        r"DC-04.*?"
        r"Nível do Rio:\s*([0-9]+,[0-9]+)\s*m.*?"
        r"Data e hora da medição:\s*"
        r"([0-9/]+)\s+([0-9:]+)",
        texto,
        re.IGNORECASE
    )

    if padrao:
        nivel = float(
            padrao.group(1).replace(",", ".")
        )

        data = padrao.group(2)
        hora = padrao.group(3)

        return nivel, data, hora

    raise RuntimeError(
        "Não foi possível localizar os dados do DC-04"
    )


def enviar_telegram(mensagem):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    resposta = requests.post(
        url,
        data={
            "chat_id": CHAT_ID,
            "text": mensagem
        },
        timeout=30
    )

    resposta.raise_for_status()


def carregar_estado():
    if not os.path.exists(ARQUIVO_ESTADO):
        return -1

    with open(
        ARQUIVO_ESTADO,
        "r"
    ) as arquivo:
        return int(
            arquivo.read().strip()
        )


def salvar_estado(patamar):
    with open(
        ARQUIVO_ESTADO,
        "w"
    ) as arquivo:
        arquivo.write(
            str(patamar)
        )


def calcular_patamar(nivel):
    if nivel < LIMITE_INICIAL:
        return -1

    return int(
        (nivel - LIMITE_INICIAL + 0.000001)
        / INCREMENTO
    )


try:
    nivel, data, hora = obter_dc04()

    patamar_atual = calcular_patamar(nivel)
    patamar_anterior = carregar_estado()

    if patamar_atual > patamar_anterior:

        limite_atingido = (
            LIMITE_INICIAL
            + (patamar_atual * INCREMENTO)
        )

        mensagem = (
            "🚨🚨 ALERTA DC-04 🚨🚨\n\n"
            f"🌊 Nível atual: {nivel:.2f} m\n"
            "📍 Vitalmar Pescados\n"
            f"🕐 Medição: {data} {hora}\n\n"
            f"⚠️ Limite atingido: "
            f"{limite_atingido:.2f} m"
        )

        enviar_telegram(mensagem)

        salvar_estado(
            patamar_atual
        )

    elif patamar_atual < patamar_anterior:

        salvar_estado(
            patamar_atual
        )

    print(
        f"DC-04: {nivel:.2f} m | "
        f"Medição: {data} {hora}"
    )

except Exception as erro:

    print("ERRO NO MONITORAMENTO:")
    print(str(erro))
    raise